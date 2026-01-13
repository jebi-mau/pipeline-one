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
