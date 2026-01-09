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


@app.task(bind=True, name="worker.tasks.orchestrator.run_pipeline")
def run_pipeline(
    self,
    job_id: str,
    svo2_files: list[str],
    object_classes: list[dict],
    config: dict,
) -> dict[str, Any]:
    """
    Run the full processing pipeline.

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

    Returns:
        Pipeline result summary
    """
    logger.info(f"Starting pipeline for job {job_id}")

    # Update task state
    self.update_state(
        state="PROGRESS",
        meta={
            "stage": "extraction",
            "progress": 0,
            "message": "Starting extraction",
        },
    )

    # Build extraction chain for each SVO2 file
    extraction_tasks = group([
        extract_svo2.s(job_id, svo2_file, config.get("extraction", {}))
        for svo2_file in svo2_files
    ])

    # Chain: extraction -> segmentation -> reconstruction -> tracking
    # Use chord with callback to avoid blocking
    pipeline = chain(
        extraction_tasks,
        run_segmentation.s(job_id, object_classes, config.get("sam3", {})),
        run_reconstruction.s(job_id, config.get("reconstruction", {})),
        run_tracking.s(job_id, config.get("tracking", {})),
        pipeline_completed.s(job_id),
    )

    # Execute pipeline asynchronously (fire and forget)
    pipeline.apply_async()

    logger.info(f"Pipeline dispatched for job {job_id}")
    return {
        "status": "dispatched",
        "job_id": job_id,
        "message": "Pipeline tasks have been queued",
    }


@app.task(name="worker.tasks.orchestrator.pipeline_completed")
def pipeline_completed(tracking_result: dict | None, job_id: str) -> dict[str, Any]:
    """
    Callback task executed when pipeline completes.

    Args:
        tracking_result: Result from tracking stage
        job_id: Processing job UUID

    Returns:
        Final pipeline result
    """
    from datetime import datetime

    from sqlalchemy import create_engine, text

    logger.info(f"Pipeline completed for job {job_id}")

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
                        current_stage = 4,
                        progress = 100.0,
                        total_detections = :total_detections,
                        updated_at = now()
                    WHERE id = :job_id
                    """
                ),
                {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "total_detections": tracking_result.get("total_tracks", 0) if tracking_result else 0,
                    "job_id": job_id,
                },
            )
            conn.commit()
        logger.info(f"Updated job {job_id} status to completed")
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")

    if tracking_result is None:
        return {
            "status": "completed",
            "job_id": job_id,
            "message": "Pipeline completed (no tracking result)",
        }

    return {
        "status": "completed",
        "job_id": job_id,
        "result": tracking_result,
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
