"""Pydantic schemas for curated datasets."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FilterConfig(BaseModel):
    """Filter configuration for a curated dataset."""

    excluded_classes: list[str] = Field(default_factory=list)
    excluded_annotation_ids: list[str] = Field(default_factory=list)
    diversity_applied: bool = False
    diversity_similarity_threshold: float | None = None
    diversity_motion_threshold: float | None = None
    excluded_frame_indices: list[int] = Field(default_factory=list)


class ExclusionReasons(BaseModel):
    """Breakdown of why items were excluded."""

    class_filter: list[str] = Field(default_factory=list)
    diversity: list[str] = Field(default_factory=list)
    manual: list[str] = Field(default_factory=list)


class CuratedDatasetCreate(BaseModel):
    """Schema for creating a new curated dataset."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_job_id: UUID
    filter_config: FilterConfig

    # Statistics (computed from source job)
    original_frame_count: int = Field(ge=0)
    original_annotation_count: int = Field(ge=0)
    filtered_frame_count: int = Field(ge=0)
    filtered_annotation_count: int = Field(ge=0)

    # Detailed exclusion tracking
    excluded_frame_ids: list[str] = Field(default_factory=list)
    excluded_annotation_ids: list[str] = Field(default_factory=list)
    exclusion_reasons: ExclusionReasons = Field(default_factory=ExclusionReasons)


class CuratedDatasetUpdate(BaseModel):
    """Schema for updating a curated dataset (limited to metadata)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class CuratedDatasetResponse(BaseModel):
    """Response schema for a curated dataset."""

    id: UUID
    name: str
    description: str | None
    version: int

    # Source lineage
    source_job_id: UUID
    source_job_name: str | None = None
    source_dataset_id: UUID | None
    source_dataset_name: str | None = None

    # Filter configuration
    filter_config: dict[str, Any]

    # Statistics
    original_frame_count: int
    original_annotation_count: int
    filtered_frame_count: int
    filtered_annotation_count: int
    frames_removed: int
    annotations_removed: int
    reduction_percentage: float

    # Exclusion details
    excluded_frame_ids: list[str]
    excluded_annotation_ids: list[str]
    exclusion_reasons: dict[str, Any]

    # Metadata
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    # Related exports count
    training_datasets_count: int = 0

    class Config:
        from_attributes = True


class CuratedDatasetListResponse(BaseModel):
    """Response schema for listing curated datasets."""

    id: UUID
    name: str
    description: str | None
    version: int
    source_job_id: UUID
    source_job_name: str | None = None
    source_dataset_id: UUID | None = None
    source_dataset_name: str | None = None
    filter_config: dict[str, Any] = Field(default_factory=dict)
    original_frame_count: int = 0
    original_annotation_count: int = 0
    filtered_frame_count: int
    filtered_annotation_count: int
    training_datasets_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CuratedDatasetListPaginated(BaseModel):
    """Paginated response for curated datasets."""

    curated_datasets: list[CuratedDatasetListResponse]
    total: int
    limit: int
    offset: int
