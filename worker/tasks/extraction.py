"""SVO2 extraction task."""

import logging
import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from worker.celery_app import app

logger = logging.getLogger(__name__)


def get_db_engine():
    """Get synchronous database engine for progress updates."""
    db_url = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://svo2_analyzer:svo2_analyzer_dev@localhost:5432/svo2_analyzer"
    )
    return create_engine(db_url)


def update_job_progress(job_id: str, stage: int, progress: float,
                        total_frames: int = None, processed_frames: int = None,
                        stage_progress: float = None):
    """Update job progress in database.

    Only updates if job is in 'running' status to prevent stale tasks
    from corrupting job state after restart/cancel.
    """
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            # First check if job is still running - prevents stale tasks from
            # overwriting progress after a job restart or cancellation
            result = conn.execute(
                text("SELECT status FROM processing_jobs WHERE id = :job_id"),
                {"job_id": job_id}
            )
            row = result.fetchone()
            if row is None or row[0] != "running":
                logger.debug(f"Skipping progress update for job {job_id} - status is {row[0] if row else 'not found'}")
                return

            params = {
                "job_id": job_id,
                "stage": stage,
                "progress": progress,
            }

            sql_parts = [
                "UPDATE processing_jobs SET",
                "current_stage = :stage,",
                "progress = :progress,",
            ]

            # Note: stage_progress column may not exist, skip it
            # if stage_progress is not None:
            #     sql_parts.append("stage_progress = :stage_progress,")
            #     params["stage_progress"] = stage_progress

            if total_frames is not None:
                sql_parts.append("total_frames = :total_frames,")
                params["total_frames"] = total_frames

            if processed_frames is not None:
                sql_parts.append("processed_frames = :processed_frames,")
                params["processed_frames"] = processed_frames

            sql_parts.append("updated_at = now()")
            sql_parts.append("WHERE id = :job_id AND status = 'running'")

            sql = " ".join(sql_parts)
            conn.execute(text(sql), params)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update job progress: {e}")


@app.task(bind=True, name="worker.tasks.extraction.extract_svo2")
def extract_svo2(
    self,
    job_id: str,
    svo2_file: str,
    config: dict,
) -> dict[str, Any]:
    """
    Extract frames from a single SVO2 file.

    Args:
        job_id: Processing job UUID
        svo2_file: Path to SVO2 file
        config: Extraction configuration

    Returns:
        Extraction result with frame registry path
    """
    from processing.svo2.extractor import ExtractionConfig, SVO2Extractor
    from processing.svo2.reader import SVO2Reader

    logger.info(f"Extracting SVO2: {svo2_file}")

    # Create output directory
    output_base = config.get("output_dir", f"data/output/{job_id}")
    svo2_name = Path(svo2_file).stem
    output_dir = Path(output_base) / svo2_name

    # Configure extraction
    extraction_config = ExtractionConfig(
        extract_left_rgb=config.get("extract_left_rgb", True),
        extract_right_rgb=config.get("extract_right_rgb", True),
        extract_depth=config.get("extract_depth", True),
        extract_point_cloud=config.get("extract_point_cloud", True),
        extract_imu=config.get("extract_imu", True),
        frame_skip=config.get("frame_skip", 1),
        start_frame=config.get("start_frame", 0),
        end_frame=config.get("end_frame"),
        image_format=config.get("image_format", "png"),
        depth_format=config.get("depth_format", "png16"),
        point_cloud_format=config.get("point_cloud_format", "ply"),
    )

    # Track total frames for this file
    total_frames_this_file = 0

    # Get progress range from config (default to old behavior)
    progress_range = config.get("progress_range", (0, 25))
    range_start, range_end = progress_range

    # Progress callback
    def progress_callback(current: int, total: int, message: str) -> None:
        nonlocal total_frames_this_file
        total_frames_this_file = total

        # Update Celery state
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": "extraction",
                "file": svo2_file,
                "current": current,
                "total": total,
                "message": message,
            },
        )

        # Update database progress (stage 1 = extraction)
        # Calculate overall progress based on assigned range
        stage_progress = (current / total * 100) if total > 0 else 0
        range_size = range_end - range_start
        overall_progress = range_start + (stage_progress / 100 * range_size)

        update_job_progress(
            job_id=job_id,
            stage=1,
            progress=overall_progress,
            stage_progress=stage_progress,
            total_frames=total,
            processed_frames=current,
        )

    try:
        # Open SVO2 file
        with SVO2Reader(svo2_file, depth_mode=config.get("depth_mode", "ULTRA")) as reader:
            # Create extractor
            extractor = SVO2Extractor(reader, output_dir, extraction_config)

            # Run extraction
            result = extractor.extract(progress_callback=progress_callback)

        logger.info(f"Extraction complete: {result.extracted_frames} frames")

        return {
            "status": "completed",
            "svo2_file": svo2_file,
            "output_dir": str(result.output_dir),
            "frame_count": result.frame_count,
            "extracted_frames": result.extracted_frames,
            "failed_frames": result.failed_frames,
            "frame_registry": str(result.frame_registry_file),
            "calibration": str(result.calibration_file),
        }

    except Exception as e:
        logger.error(f"Extraction failed for {svo2_file}: {e}")
        return {
            "status": "failed",
            "svo2_file": svo2_file,
            "error": str(e),
        }


@app.task(name="worker.tasks.extraction.validate_svo2")
def validate_svo2(svo2_file: str) -> dict[str, Any]:
    """
    Validate an SVO2 file can be opened.

    Args:
        svo2_file: Path to SVO2 file

    Returns:
        Validation result with file metadata
    """
    from processing.svo2.reader import SVO2Reader

    try:
        with SVO2Reader(svo2_file) as reader:
            metadata = reader.get_metadata()

        return {
            "valid": True,
            "file": svo2_file,
            "metadata": metadata,
        }

    except Exception as e:
        return {
            "valid": False,
            "file": svo2_file,
            "error": str(e),
        }
