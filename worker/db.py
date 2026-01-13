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
