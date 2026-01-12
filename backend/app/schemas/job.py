"""Job-related Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class JobConfig(BaseModel):
    """Job configuration settings."""

    object_class_ids: list[str] = Field(description="IDs of object classes to detect")
    sam3_model_variant: str = "sam3_hiera_large"
    sam3_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    sam3_iou_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    sam3_batch_size: int = Field(default=8, ge=1, le=32)
    frame_skip: int = Field(default=1, ge=1, description="Process every Nth frame")
    enable_tracking: bool = True
    export_3d_data: bool = True
    stages_to_run: list[str] = Field(
        default=["extraction", "segmentation", "reconstruction", "tracking"],
        description="Pipeline stages to execute"
    )


class JobCreate(BaseModel):
    """Request schema for creating a new job."""

    name: str = Field(min_length=1, max_length=255)
    input_paths: list[str] = Field(min_length=1, description="Paths to SVO2 files")
    output_directory: str | None = None
    config: JobConfig


class JobResponse(BaseModel):
    """Response schema for job details."""

    id: UUID
    name: str
    status: Literal["pending", "running", "paused", "completed", "failed", "cancelled"]
    current_stage: int = 0
    current_stage_name: str | None = None
    progress: float = 0.0
    stage_progress: float = 0.0
    total_frames: int | None = None
    processed_frames: int | None = None
    input_paths: list[str]
    output_directory: str | None = None
    config: JobConfig
    stages_to_run: list[str] = Field(
        default=["extraction", "segmentation", "reconstruction", "tracking"]
    )
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    eta_seconds: int | None = None


class JobListResponse(BaseModel):
    """Response schema for job list."""

    jobs: list[JobResponse]
    total: int
    limit: int
    offset: int


class JobStatusUpdate(BaseModel):
    """Response schema for job status updates."""

    id: UUID
    status: str
    message: str | None = None


class JobStatistics(BaseModel):
    """Job processing statistics."""

    total_frames: int
    total_detections: int
    detections_by_class: dict[str, int]
    total_tracks: int
    processing_time_seconds: float


class JobResultsResponse(BaseModel):
    """Response schema for job results."""

    job_id: UUID
    status: str
    statistics: JobStatistics
    output_directory: str
    available_exports: list[str]
