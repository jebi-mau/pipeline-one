"""Pipeline orchestrator task for coordinating processing stages."""

import logging
from typing import Any
from uuid import UUID

from celery import chain, chord, group

from worker.celery_app import app
from worker.tasks.extraction import extract_svo2
from worker.tasks.segmentation import run_segmentation
from worker.tasks.reconstruction import run_reconstruction
from worker.tasks.tracking import run_tracking

logger = logging.getLogger(__name__)

# Stage weights for progress calculation (must sum to 1.0)
STAGE_WEIGHTS = {
    "extraction": 0.25,
    "segmentation": 0.50,
    "reconstruction": 0.15,
    "tracking": 0.10,
}

# Stage number mapping
STAGE_NUMBERS = {
    "extraction": 1,
    "segmentation": 2,
    "reconstruction": 3,
    "tracking": 4,
}

# All stages in order
ALL_STAGES = ["extraction", "segmentation", "reconstruction", "tracking"]


def calculate_progress_ranges(stages_to_run: list[str]) -> dict[str, tuple[float, float]]:
    """
    Calculate progress ranges normalized to selected stages.

    For example, if only extraction and segmentation are selected:
    - extraction: (0, 33.33)  # 0.25 / 0.75 * 100
    - segmentation: (33.33, 100)  # 0.50 / 0.75 * 100

    Args:
        stages_to_run: List of stage names to execute

    Returns:
        Dict mapping stage name to (start, end) progress tuple
    """
    # Get weights for selected stages only
    selected_weights = {s: STAGE_WEIGHTS[s] for s in stages_to_run if s in STAGE_WEIGHTS}
    total_weight = sum(selected_weights.values())

    if total_weight == 0:
        return {}

    ranges = {}
    accumulated = 0.0

    # Process stages in order
    for stage in ALL_STAGES:
        if stage in selected_weights:
            normalized = selected_weights[stage] / total_weight * 100
            ranges[stage] = (accumulated, accumulated + normalized)
            accumulated += normalized

    return ranges


def validate_stage_dependencies(stages_to_run: list[str]) -> list[str]:
    """
    Validate and add required dependencies for selected stages.

    Stage dependencies:
    - segmentation requires extraction
    - reconstruction requires segmentation
    - tracking requires reconstruction

    Args:
        stages_to_run: List of requested stages

    Returns:
        Validated list with all required dependencies
    """
    validated = set(stages_to_run)

    # Check dependencies
    if "tracking" in validated:
        validated.add("reconstruction")
    if "reconstruction" in validated:
        validated.add("segmentation")
    if "segmentation" in validated:
        validated.add("extraction")

    # Return in proper order
    return [s for s in ALL_STAGES if s in validated]


@app.task(bind=True, name="worker.tasks.orchestrator.run_pipeline")
def run_pipeline(
    self,
    job_id: str,
    svo2_files: list[str],
    object_classes: list[dict],
    config: dict,
    stages_to_run: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run the processing pipeline with selective stage execution.

    Pipeline stages:
    1. Extraction - Extract frames from SVO2 files
    2. Segmentation - Run SAM 3 inference
    3. Reconstruction - Estimate 3D bounding boxes
    4. Tracking - Track objects across frames

    Args:
        job_id: Processing job UUID
        svo2_files: List of SVO2 file paths
        object_classes: Object class definitions
        config: Processing configuration
        stages_to_run: List of stages to execute (default: all)

    Returns:
        Pipeline result summary
    """
    # Default to all stages if not specified
    if stages_to_run is None:
        stages_to_run = ALL_STAGES.copy()

    # Validate and add required dependencies
    stages_to_run = validate_stage_dependencies(stages_to_run)

    # Calculate progress ranges for selected stages
    progress_ranges = calculate_progress_ranges(stages_to_run)

    logger.info(f"Starting pipeline for job {job_id}")
    logger.info(f"Stages to run: {stages_to_run}")
    logger.info(f"Progress ranges: {progress_ranges}")

    # Update task state
    first_stage = stages_to_run[0] if stages_to_run else "extraction"
    self.update_state(
        state="PROGRESS",
        meta={
            "stage": first_stage,
            "progress": 0,
            "message": f"Starting {first_stage}",
        },
    )

    # Build extraction config with progress ranges
    extraction_config = config.get("extraction", {})
    extraction_config["progress_range"] = progress_ranges.get("extraction", (0, 25))

    # Build the pipeline chain dynamically based on selected stages
    pipeline_tasks = []

    if "extraction" in stages_to_run:
        # Build extraction group for each SVO2 file
        extraction_tasks = group([
            extract_svo2.s(job_id, svo2_file, extraction_config)
            for svo2_file in svo2_files
        ])
        pipeline_tasks.append(extraction_tasks)

    if "segmentation" in stages_to_run:
        sam3_config = config.get("sam3", {})
        sam3_config["progress_range"] = progress_ranges.get("segmentation", (25, 75))
        pipeline_tasks.append(
            run_segmentation.s(job_id, object_classes, sam3_config)
        )

    if "reconstruction" in stages_to_run:
        recon_config = config.get("reconstruction", {})
        recon_config["progress_range"] = progress_ranges.get("reconstruction", (75, 90))
        pipeline_tasks.append(
            run_reconstruction.s(job_id, recon_config)
        )

    if "tracking" in stages_to_run:
        tracking_config = config.get("tracking", {})
        tracking_config["progress_range"] = progress_ranges.get("tracking", (90, 100))
        pipeline_tasks.append(
            run_tracking.s(job_id, tracking_config)
        )

    # Add completion callback with stages info
    final_stage = stages_to_run[-1] if stages_to_run else "extraction"
    pipeline_tasks.append(
        pipeline_completed.s(job_id, stages_to_run, STAGE_NUMBERS.get(final_stage, 1))
    )

    # Build and execute the chain
    if pipeline_tasks:
        pipeline = chain(*pipeline_tasks)
        pipeline.apply_async()

    logger.info(f"Pipeline dispatched for job {job_id}")
    return {
        "status": "dispatched",
        "job_id": job_id,
        "stages": stages_to_run,
        "progress_ranges": {k: list(v) for k, v in progress_ranges.items()},
        "message": "Pipeline tasks have been queued",
    }


@app.task(name="worker.tasks.orchestrator.pipeline_completed")
def pipeline_completed(
    prev_result: dict | None,
    job_id: str,
    stages_run: list[str] | None = None,
    final_stage_num: int = 4,
) -> dict[str, Any]:
    """
    Callback task executed when pipeline completes.

    Args:
        prev_result: Result from previous stage
        job_id: Processing job UUID
        stages_run: List of stages that were executed
        final_stage_num: Stage number of the final stage

    Returns:
        Final pipeline result
    """
    from datetime import datetime

    from sqlalchemy import create_engine, text

    logger.info(f"Pipeline completed for job {job_id}")
    logger.info(f"Stages run: {stages_run}, final stage: {final_stage_num}")

    # Update job status in database
    try:
        import os

        db_url = os.getenv(
            "SYNC_DATABASE_URL",
            "postgresql://svo2_analyzer:svo2_analyzer_dev@localhost:5432/svo2_analyzer"
        )
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    UPDATE processing_jobs
                    SET status = :status,
                        completed_at = :completed_at,
                        current_stage = :final_stage,
                        progress = 100.0,
                        total_detections = :total_detections,
                        updated_at = now()
                    WHERE id = :job_id
                    """
                ),
                {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    # Set current_stage past the final stage so UI shows it as completed
                    "final_stage": final_stage_num + 1,
                    "total_detections": prev_result.get("total_tracks", 0) if prev_result else 0,
                    "job_id": job_id,
                },
            )
            conn.commit()
        logger.info(f"Updated job {job_id} status to completed")
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")

    if prev_result is None:
        return {
            "status": "completed",
            "job_id": job_id,
            "stages_run": stages_run or [],
            "message": "Pipeline completed",
        }

    return {
        "status": "completed",
        "job_id": job_id,
        "stages_run": stages_run or [],
        "result": prev_result,
    }


@app.task(bind=True, name="worker.tasks.orchestrator.run_stage")
def run_stage(
    self,
    job_id: str,
    stage: str,
    config: dict,
    object_classes: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Run a single pipeline stage (dispatches async, does not wait).

    Args:
        job_id: Processing job UUID
        stage: Stage name (extraction, segmentation, reconstruction, tracking)
        config: Stage configuration
        object_classes: Object classes (required for segmentation)

    Returns:
        Dispatch confirmation
    """
    logger.info(f"Running stage '{stage}' for job {job_id}")

    if stage == "extraction":
        # Get SVO2 files from job config
        svo2_files = config.get("svo2_files", [])
        tasks = group([
            extract_svo2.s(job_id, f, config)
            for f in svo2_files
        ])
        tasks.apply_async()
        return {"status": "dispatched", "stage": stage}

    elif stage == "segmentation":
        if object_classes is None:
            raise ValueError("object_classes required for segmentation")
        run_segmentation.delay(
            None,  # Previous result
            job_id,
            object_classes,
            config,
        )
        return {"status": "dispatched", "stage": stage}

    elif stage == "reconstruction":
        run_reconstruction.delay(
            None,
            job_id,
            config,
        )
        return {"status": "dispatched", "stage": stage}

    elif stage == "tracking":
        run_tracking.delay(
            None,
            job_id,
            config,
        )
        return {"status": "dispatched", "stage": stage}

    else:
        raise ValueError(f"Unknown stage: {stage}")


@app.task(name="worker.tasks.orchestrator.get_pipeline_status")
def get_pipeline_status(job_id: str) -> dict[str, Any]:
    """
    Get current pipeline status for a job.

    Args:
        job_id: Processing job UUID

    Returns:
        Status dict with stage progress
    """
    # This would query the database for actual status
    # Placeholder implementation
    return {
        "job_id": job_id,
        "status": "unknown",
        "stages": {
            "extraction": {"status": "pending", "progress": 0},
            "segmentation": {"status": "pending", "progress": 0},
            "reconstruction": {"status": "pending", "progress": 0},
            "tracking": {"status": "pending", "progress": 0},
        },
    }


@app.task(name="worker.tasks.orchestrator.cancel_pipeline")
def cancel_pipeline(job_id: str) -> dict[str, Any]:
    """
    Cancel a running pipeline.

    Args:
        job_id: Processing job UUID

    Returns:
        Cancellation result
    """
    logger.info(f"Cancelling pipeline for job {job_id}")

    # Revoke all tasks for this job
    # This is a simplified implementation
    app.control.revoke(job_id, terminate=True)

    return {
        "job_id": job_id,
        "status": "cancelled",
    }
