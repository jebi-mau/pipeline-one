"""Schemas for cleanup and disk management endpoints."""

from pydantic import BaseModel


class DiskUsageResponse(BaseModel):
    """Response for disk usage endpoint."""

    total_bytes: int
    used_bytes: int
    free_bytes: int
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    warning: str | None = None


class OrphanedDirectory(BaseModel):
    """Information about an orphaned directory."""

    name: str
    path: str
    size_bytes: int
    size_human: str


class OrphanedDirectoriesResponse(BaseModel):
    """Response for listing orphaned directories."""

    orphaned_count: int
    total_size_bytes: int
    total_size_human: str
    orphans: list[OrphanedDirectory]


class CleanupResultResponse(BaseModel):
    """Response for cleanup operation."""

    deleted_count: int
    deleted_size_bytes: int
    deleted_size_human: str
    failed_count: int
    errors: list[str]


class StorageSummaryResponse(BaseModel):
    """Response for comprehensive storage summary."""

    # Disk usage
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    disk_total_formatted: str
    disk_used_formatted: str
    disk_free_formatted: str
    disk_usage_percent: float

    # Per-entity storage
    total_jobs_storage_bytes: int
    total_jobs_storage_formatted: str
    total_datasets_storage_bytes: int
    total_datasets_storage_formatted: str
    total_training_datasets_bytes: int
    total_training_datasets_formatted: str

    # Warnings
    warning: str | None = None
    warning_level: str = "normal"  # "normal", "warning", "critical"


class BackfillResponse(BaseModel):
    """Response for storage backfill operation."""

    jobs_found: int
    jobs_updated: int
    datasets_found: int = 0
    datasets_updated: int = 0
    total_size_bytes: int
    total_size_formatted: str
    dry_run: bool
    errors: list[str]
