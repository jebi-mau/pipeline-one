"""Shared database utilities for worker tasks.

Provides a singleton connection pool for synchronous database operations
in Celery tasks.
"""

import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Thread-safe singleton for database engine
_engine: Engine | None = None
_engine_lock = threading.Lock()


def get_db_engine() -> Engine:
    """
    Get the singleton database engine with connection pooling.

    Uses QueuePool with sensible defaults for worker tasks:
    - pool_size=5: Base number of connections
    - max_overflow=10: Allow up to 15 total connections under load
    - pool_timeout=30: Wait up to 30s for available connection
    - pool_recycle=1800: Recycle connections every 30 minutes

    Returns:
        SQLAlchemy Engine with connection pooling
    """
    global _engine

    if _engine is None:
        with _engine_lock:
            # Double-check after acquiring lock
            if _engine is None:
                db_url = os.getenv(
                    "SYNC_DATABASE_URL",
                    "postgresql://svo2_analyzer:svo2_analyzer_dev@localhost:5432/svo2_analyzer"
                )
                _engine = create_engine(
                    db_url,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                    pool_pre_ping=True,  # Verify connections before use
                )
                logger.info("Created database connection pool")

    return _engine


@contextmanager
def get_db_connection() -> Generator:
    """
    Context manager for database connections.

    Yields a connection from the pool and ensures proper cleanup.

    Usage:
        with get_db_connection() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
    """
    engine = get_db_engine()
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def get_job_timing_info(job_id: str) -> dict | None:
    """
    Get current timing info for a job.

    Returns:
        Dict with current_stage, stage_started_at, or None if not found
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT current_stage, stage_started_at, started_at
                    FROM processing_jobs
                    WHERE id = :job_id
                """),
                {"job_id": job_id}
            )
            row = result.fetchone()
            if row:
                return {
                    "current_stage": row[0],
                    "stage_started_at": row[1],
                    "started_at": row[2],
                }
            return None
    except Exception as e:
        logger.error(f"Failed to get job timing info: {e}")
        return None


def update_job_progress(
    job_id: str,
    stage: int,
    progress: float,
    total_frames: int | None = None,
    processed_frames: int | None = None,
    stage_progress: float | None = None,
    current_stage_name: str | None = None,
) -> bool:
    """
    Update job progress in database atomically.

    Only updates if job is in 'running' status to prevent stale tasks
    from corrupting job state after restart/cancel.

    Also tracks stage timing for ETA calculations:
    - Updates stage_started_at when stage changes
    - Calculates frames_per_second from elapsed time

    Args:
        job_id: Processing job UUID
        stage: Current stage number (1-4)
        progress: Overall progress percentage (0-100)
        total_frames: Total frames to process
        processed_frames: Frames processed so far
        stage_progress: Current stage progress percentage
        current_stage_name: Name of current stage

    Returns:
        True if update was applied, False if job was not running
    """
    try:
        now = datetime.now(timezone.utc)

        # Get current job timing info to detect stage changes
        timing_info = get_job_timing_info(job_id)
        current_stage_in_db = timing_info["current_stage"] if timing_info else 0
        stage_started_at = timing_info["stage_started_at"] if timing_info else None

        with get_db_connection() as conn:
            # Build update SQL dynamically based on provided parameters
            params = {
                "job_id": job_id,
                "stage": stage,
                "progress": progress,
                "updated_at": now,
            }

            set_clauses = [
                "current_stage = :stage",
                "progress = :progress",
                "updated_at = :updated_at",
            ]

            # Detect stage change - update stage_started_at
            if stage != current_stage_in_db:
                set_clauses.append("stage_started_at = :stage_started_at")
                params["stage_started_at"] = now
                stage_started_at = now  # Use new time for rate calculation
                logger.info(f"Job {job_id}: Stage changed from {current_stage_in_db} to {stage}")

            # Calculate frames_per_second if we have timing and frame data
            if stage_started_at and processed_frames and processed_frames > 0:
                elapsed_seconds = (now - stage_started_at).total_seconds()
                if elapsed_seconds > 0:
                    frames_per_second = processed_frames / elapsed_seconds
                    set_clauses.append("frames_per_second = :frames_per_second")
                    params["frames_per_second"] = round(frames_per_second, 2)

            if total_frames is not None:
                set_clauses.append("total_frames = :total_frames")
                params["total_frames"] = total_frames

            if processed_frames is not None:
                set_clauses.append("processed_frames = :processed_frames")
                params["processed_frames"] = processed_frames

            sql = f"""
                UPDATE processing_jobs
                SET {', '.join(set_clauses)}
                WHERE id = :job_id AND status = 'running'
            """

            result = conn.execute(text(sql), params)
            conn.commit()

            # Check if any row was updated
            updated = result.rowcount > 0
            if not updated:
                logger.debug(f"Skipping progress update for job {job_id} - not running")

            return updated

    except Exception as e:
        logger.error(f"Failed to update job progress: {e}")
        return False


def update_job_status(
    job_id: str,
    status: str,
    error_message: str | None = None,
    error_stage: str | None = None,
    total_detections: int | None = None,
) -> bool:
    """
    Update job status in database.

    Args:
        job_id: Processing job UUID
        status: New status (completed, failed, cancelled)
        error_message: Error message if failed
        error_stage: Stage where error occurred
        total_detections: Total detections count

    Returns:
        True if update was applied
    """
    try:
        with get_db_connection() as conn:
            params = {
                "job_id": job_id,
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }

            set_clauses = [
                "status = :status",
                "updated_at = :updated_at",
            ]

            if status in ("completed", "failed", "cancelled"):
                set_clauses.append("completed_at = :completed_at")
                params["completed_at"] = datetime.now(timezone.utc)

            if status == "completed":
                set_clauses.append("progress = 100.0")

            if error_message is not None:
                set_clauses.append("error_message = :error_message")
                params["error_message"] = error_message

            if error_stage is not None:
                set_clauses.append("error_stage = :error_stage")
                params["error_stage"] = error_stage

            if total_detections is not None:
                set_clauses.append("total_detections = :total_detections")
                params["total_detections"] = total_detections

            sql = f"""
                UPDATE processing_jobs
                SET {', '.join(set_clauses)}
                WHERE id = :job_id
            """

            result = conn.execute(text(sql), params)
            conn.commit()

            return result.rowcount > 0

    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
        return False


def is_job_running(job_id: str) -> bool:
    """
    Check if a job is still in running status.

    Useful for tasks to check if they should continue processing
    or abort early due to cancellation.

    Args:
        job_id: Processing job UUID

    Returns:
        True if job status is 'running'
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(
                text("SELECT status FROM processing_jobs WHERE id = :job_id"),
                {"job_id": job_id}
            )
            row = result.fetchone()
            return row is not None and row[0] == "running"
    except Exception as e:
        logger.error(f"Failed to check job status: {e}")
        return False


def record_stage_completion(
    job_id: str,
    stage: str,
    duration_seconds: float,
    total_frames: int | None = None,
) -> bool:
    """
    Record stage completion with duration for benchmarking.

    Updates the per-stage duration fields on the processing_jobs table
    for use in future ETA estimation.

    Args:
        job_id: Processing job UUID
        stage: Stage name (extraction, segmentation, reconstruction, tracking)
        duration_seconds: Time taken to complete stage in seconds
        total_frames: Total frames processed (for FPS calculation)

    Returns:
        True if update was applied
    """
    try:
        with get_db_connection() as conn:
            # Map stage name to column name
            column_map = {
                "extraction": "extraction_duration_seconds",
                "segmentation": "segmentation_duration_seconds",
                "reconstruction": "reconstruction_duration_seconds",
                "tracking": "tracking_duration_seconds",
            }

            duration_column = column_map.get(stage)
            if not duration_column:
                logger.warning(f"Unknown stage for duration tracking: {stage}")
                return False

            params = {
                "job_id": job_id,
                "duration": duration_seconds,
                "updated_at": datetime.now(timezone.utc),
            }

            set_clauses = [
                f"{duration_column} = :duration",
                "updated_at = :updated_at",
            ]

            # Calculate and store FPS for extraction and segmentation
            if total_frames and duration_seconds > 0:
                fps = total_frames / duration_seconds
                if stage == "extraction":
                    set_clauses.append("extraction_fps = :fps")
                    params["fps"] = round(fps, 2)
                elif stage == "segmentation":
                    set_clauses.append("segmentation_fps = :fps")
                    params["fps"] = round(fps, 2)

            sql = f"""
                UPDATE processing_jobs
                SET {', '.join(set_clauses)}
                WHERE id = :job_id
            """

            result = conn.execute(text(sql), params)
            conn.commit()

            if result.rowcount > 0:
                logger.info(
                    f"Recorded {stage} duration for job {job_id}: "
                    f"{duration_seconds:.1f}s"
                    + (f", {fps:.2f} fps" if total_frames and duration_seconds > 0 else "")
                )
                return True

            return False

    except Exception as e:
        logger.error(f"Failed to record stage completion: {e}")
        return False


def update_performance_benchmark(
    model_variant: str,
    extraction_fps: float | None = None,
    segmentation_fps: float | None = None,
) -> bool:
    """
    Update performance benchmarks using exponential moving average.

    Called when a job completes to update the benchmark table with
    actual performance data for future ETA estimation.

    Args:
        model_variant: SAM3 model variant name
        extraction_fps: Extraction FPS from completed job
        segmentation_fps: Segmentation FPS from completed job

    Returns:
        True if update was applied
    """
    try:
        alpha = 0.3  # EMA weight for new data (30% new, 70% old)

        with get_db_connection() as conn:
            # Check if benchmark exists
            result = conn.execute(
                text("""
                    SELECT id, avg_extraction_fps, avg_segmentation_fps, sample_count
                    FROM job_performance_benchmarks
                    WHERE sam3_model_variant = :model_variant
                """),
                {"model_variant": model_variant}
            )
            row = result.fetchone()

            if row:
                # Update existing benchmark
                benchmark_id, old_ext_fps, old_seg_fps, sample_count = row

                new_ext_fps = extraction_fps
                if old_ext_fps and extraction_fps:
                    new_ext_fps = alpha * extraction_fps + (1 - alpha) * old_ext_fps
                elif not extraction_fps:
                    new_ext_fps = old_ext_fps

                new_seg_fps = segmentation_fps
                if old_seg_fps and segmentation_fps:
                    new_seg_fps = alpha * segmentation_fps + (1 - alpha) * old_seg_fps
                elif not segmentation_fps:
                    new_seg_fps = old_seg_fps

                conn.execute(
                    text("""
                        UPDATE job_performance_benchmarks
                        SET avg_extraction_fps = :ext_fps,
                            avg_segmentation_fps = :seg_fps,
                            sample_count = :sample_count,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "id": benchmark_id,
                        "ext_fps": new_ext_fps,
                        "seg_fps": new_seg_fps,
                        "sample_count": sample_count + 1,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
            else:
                # Create new benchmark
                import uuid
                conn.execute(
                    text("""
                        INSERT INTO job_performance_benchmarks
                        (id, sam3_model_variant, avg_extraction_fps, avg_segmentation_fps,
                         sample_count, created_at, updated_at)
                        VALUES (:id, :model_variant, :ext_fps, :seg_fps, 1, :now, :now)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "model_variant": model_variant,
                        "ext_fps": extraction_fps,
                        "seg_fps": segmentation_fps,
                        "now": datetime.now(timezone.utc),
                    }
                )

            conn.commit()
            logger.info(
                f"Updated benchmark for {model_variant}: "
                f"extraction={extraction_fps:.2f if extraction_fps else 'N/A'} fps, "
                f"segmentation={segmentation_fps:.2f if segmentation_fps else 'N/A'} fps"
            )
            return True

    except Exception as e:
        logger.error(f"Failed to update performance benchmark: {e}")
        return False


def get_job_performance_data(job_id: str) -> dict | None:
    """
    Get performance data from a completed job for benchmarking.

    Returns:
        Dict with model_variant, extraction_fps, segmentation_fps, or None
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT
                        jc.sam3_model_variant,
                        pj.extraction_fps,
                        pj.segmentation_fps,
                        pj.extraction_duration_seconds,
                        pj.segmentation_duration_seconds,
                        pj.total_frames
                    FROM processing_jobs pj
                    JOIN job_configs jc ON pj.config_id = jc.id
                    WHERE pj.id = :job_id
                """),
                {"job_id": job_id}
            )
            row = result.fetchone()
            if row:
                model_variant, ext_fps, seg_fps, ext_dur, seg_dur, total_frames = row

                # Calculate FPS if not stored but duration is available
                if not ext_fps and ext_dur and total_frames and ext_dur > 0:
                    ext_fps = total_frames / ext_dur
                if not seg_fps and seg_dur and total_frames and seg_dur > 0:
                    seg_fps = total_frames / seg_dur

                return {
                    "model_variant": model_variant,
                    "extraction_fps": ext_fps,
                    "segmentation_fps": seg_fps,
                }
            return None
    except Exception as e:
        logger.error(f"Failed to get job performance data: {e}")
        return None


def get_job_output_directory(job_id: str) -> str | None:
    """
    Get the output directory for a job.

    Args:
        job_id: Processing job UUID

    Returns:
        Output directory path or None if not found
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(
                text("SELECT output_directory FROM processing_jobs WHERE id = :job_id"),
                {"job_id": job_id}
            )
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Failed to get job output directory: {e}")
        return None


def update_job_storage_size(job_id: str, storage_size_bytes: int) -> bool:
    """
    Update the storage size for a completed job.

    Args:
        job_id: Processing job UUID
        storage_size_bytes: Total size of output directory in bytes

    Returns:
        True if update was applied
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(
                text("""
                    UPDATE processing_jobs
                    SET storage_size_bytes = :storage_size_bytes,
                        updated_at = :updated_at
                    WHERE id = :job_id
                """),
                {
                    "job_id": job_id,
                    "storage_size_bytes": storage_size_bytes,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            conn.commit()

            if result.rowcount > 0:
                # Format size for logging
                size_mb = storage_size_bytes / (1024 * 1024)
                size_gb = storage_size_bytes / (1024 * 1024 * 1024)
                if size_gb >= 1:
                    logger.info(f"Updated storage size for job {job_id}: {size_gb:.2f} GB")
                else:
                    logger.info(f"Updated storage size for job {job_id}: {size_mb:.2f} MB")
                return True

            return False

    except Exception as e:
        logger.error(f"Failed to update job storage size: {e}")
        return False


def cleanup_engine() -> None:
    """
    Dispose of the database engine and connection pool.

    Call this during worker shutdown to ensure clean cleanup.
    """
    global _engine

    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None
            logger.info("Database connection pool disposed")
