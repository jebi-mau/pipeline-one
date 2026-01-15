"""Cleanup and disk management API endpoints."""

import logging
import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_db
from backend.app.models.job import ProcessingJob
from backend.app.schemas.cleanup import (
    BackfillResponse,
    CleanupResultResponse,
    DiskUsageResponse,
    OrphanedDirectoriesResponse,
    OrphanedDirectory,
    StorageSummaryResponse,
)
from backend.app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_directory_size(path: Path) -> int:
    """Calculate total size of a directory."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


@router.get("/disk-usage", response_model=DiskUsageResponse)
async def get_disk_usage():
    """Get current disk usage for the output directory."""
    settings = get_settings()
    output_dir = Path(settings.output_directory)

    # Get disk usage
    usage = shutil.disk_usage(output_dir)

    total_gb = usage.total / (1024 ** 3)
    used_gb = usage.used / (1024 ** 3)
    free_gb = usage.free / (1024 ** 3)
    usage_percent = (usage.used / usage.total) * 100

    # Generate warning if space is low
    warning = None
    if free_gb < 10:
        warning = f"Critical: Only {free_gb:.1f} GB free. New jobs will be blocked."
    elif free_gb < 50:
        warning = f"Warning: Only {free_gb:.1f} GB free. Consider cleaning up old jobs."

    return DiskUsageResponse(
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
        total_gb=round(total_gb, 2),
        used_gb=round(used_gb, 2),
        free_gb=round(free_gb, 2),
        usage_percent=round(usage_percent, 2),
        warning=warning,
    )


@router.get("/orphans", response_model=OrphanedDirectoriesResponse)
async def list_orphaned_directories(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    List orphaned directories (exist on disk but not in database).

    These are typically from jobs that were deleted without cleaning up
    the filesystem.
    """
    settings = get_settings()
    output_dir = Path(settings.output_directory)

    # Get all job IDs from database
    result = await db.execute(select(ProcessingJob.id))
    db_job_ids = {str(row[0]) for row in result.all()}

    # Find orphaned directories
    orphans = []
    if output_dir.exists():
        for item in output_dir.iterdir():
            if item.is_dir():
                try:
                    # Validate it looks like a UUID
                    UUID(item.name)
                    # Check if it exists in database
                    if item.name not in db_job_ids:
                        size = get_directory_size(item)
                        orphans.append(OrphanedDirectory(
                            name=item.name,
                            path=str(item),
                            size_bytes=size,
                            size_human=format_size(size),
                        ))
                except ValueError:
                    # Not a UUID, skip
                    continue

    # Sort by size descending
    orphans.sort(key=lambda x: x.size_bytes, reverse=True)

    total_size = sum(o.size_bytes for o in orphans)

    return OrphanedDirectoriesResponse(
        orphaned_count=len(orphans),
        total_size_bytes=total_size,
        total_size_human=format_size(total_size),
        orphans=orphans,
    )


@router.delete("/orphans", response_model=CleanupResultResponse)
async def delete_orphaned_directories(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Delete all orphaned directories.

    This permanently removes directories that exist on disk but have no
    corresponding job in the database.
    """
    settings = get_settings()
    output_dir = Path(settings.output_directory)

    # Get all job IDs from database
    result = await db.execute(select(ProcessingJob.id))
    db_job_ids = {str(row[0]) for row in result.all()}

    deleted_count = 0
    deleted_size = 0
    failed_count = 0
    errors = []

    if output_dir.exists():
        for item in output_dir.iterdir():
            if item.is_dir():
                try:
                    # Validate it looks like a UUID
                    UUID(item.name)
                    # Check if it's orphaned
                    if item.name not in db_job_ids:
                        size = get_directory_size(item)
                        try:
                            shutil.rmtree(item)
                            deleted_count += 1
                            deleted_size += size
                            logger.info(f"Deleted orphaned directory: {item}")
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"Failed to delete {item.name}: {str(e)}")
                            logger.error(f"Failed to delete orphaned directory {item}: {e}")
                except ValueError:
                    # Not a UUID, skip
                    continue

    return CleanupResultResponse(
        deleted_count=deleted_count,
        deleted_size_bytes=deleted_size,
        deleted_size_human=format_size(deleted_size),
        failed_count=failed_count,
        errors=errors,
    )


@router.get("/storage-summary", response_model=StorageSummaryResponse)
async def get_storage_summary(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Get comprehensive storage breakdown by entity type.

    Returns disk usage, per-entity storage totals, and warnings.
    """
    storage_service = StorageService(db)
    summary = await storage_service.get_storage_summary()
    return StorageSummaryResponse(**summary)


@router.post("/backfill-storage", response_model=BackfillResponse)
async def backfill_storage_sizes(
    db: Annotated[AsyncSession, Depends(get_db)],
    dry_run: bool = True,
):
    """
    Backfill storage_size_bytes for existing jobs and datasets.

    Args:
        dry_run: If True, only calculate sizes without updating database
    """
    storage_service = StorageService(db)

    # Backfill jobs
    job_result = await storage_service.backfill_job_sizes(dry_run=dry_run)

    # Backfill datasets
    dataset_result = await storage_service.backfill_dataset_sizes(dry_run=dry_run)

    return BackfillResponse(
        jobs_found=job_result["jobs_found"],
        jobs_updated=job_result["jobs_updated"],
        datasets_found=dataset_result["datasets_found"],
        datasets_updated=dataset_result["datasets_updated"],
        total_size_bytes=job_result["total_size_bytes"] + dataset_result["total_size_bytes"],
        total_size_formatted=format_size(
            job_result["total_size_bytes"] + dataset_result["total_size_bytes"]
        ),
        dry_run=dry_run,
        errors=job_result["errors"] + dataset_result["errors"],
    )
