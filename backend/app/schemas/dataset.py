"""Dataset-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    """Request schema for creating a new dataset."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    customer: str | None = Field(default=None, max_length=255)
    site: str | None = Field(default=None, max_length=255)
    equipment: str | None = Field(default=None, max_length=255)
    collection_date: datetime | None = None
    object_types: list[str] = Field(default_factory=list)
    source_folder: str = Field(min_length=1)
    output_directory: str | None = None


class DatasetUpdate(BaseModel):
    """Request schema for updating a dataset."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    customer: str | None = Field(default=None, max_length=255)
    site: str | None = Field(default=None, max_length=255)
    equipment: str | None = Field(default=None, max_length=255)
    collection_date: datetime | None = None
    object_types: list[str] | None = None
    source_folder: str | None = Field(default=None, min_length=1)
    output_directory: str | None = None
    status: str | None = Field(default=None, max_length=20)


class DatasetFileSummary(BaseModel):
    """Summary of a dataset file."""

    id: UUID
    original_filename: str
    relative_path: str
    camera_id: str | None = None
    camera_model: str | None = None
    file_size: int
    frame_count: int | None = None
    resolution: str | None = None  # e.g., "1920x1080"
    fps: float | None = None
    status: str
    error_message: str | None = None


class DatasetFileDetail(BaseModel):
    """Detailed information about a dataset file."""

    id: UUID
    dataset_id: UUID
    original_path: str
    original_filename: str
    relative_path: str
    renamed_path: str | None = None
    renamed_filename: str | None = None
    camera_id: str | None = None
    camera_model: str | None = None
    camera_serial: str | None = None
    firmware_version: str | None = None
    file_hash: str | None = None
    file_size: int
    frame_count: int | None = None
    recording_start_ns: int | None = None
    recording_duration_ms: float | None = None
    resolution_width: int | None = None
    resolution_height: int | None = None
    fps: float | None = None
    status: str
    discovered_at: datetime
    copied_at: datetime | None = None
    error_message: str | None = None
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class JobSummary(BaseModel):
    """Summary of a job for dataset display."""

    id: UUID
    name: str
    status: str
    progress: float | None = None
    current_stage_name: str | None = None
    total_frames: int | None = None
    processed_frames: int | None = None
    object_classes: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


class JobStats(BaseModel):
    """Job statistics for a dataset."""

    total: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    jobs: list[JobSummary] = Field(default_factory=list)


class DatasetResponse(BaseModel):
    """Response schema for dataset details."""

    id: UUID
    name: str
    description: str | None = None
    customer: str | None = None
    site: str | None = None
    equipment: str | None = None
    collection_date: datetime | None = None
    object_types: list[str]
    source_folder: str
    output_directory: str | None = None
    status: str
    total_files: int
    total_size_bytes: int
    prepared_files: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    job_stats: JobStats = Field(default_factory=JobStats)


class DatasetDetailResponse(DatasetResponse):
    """Detailed response including files."""

    files: list[DatasetFileSummary] = Field(default_factory=list)
    job_count: int = 0


class DatasetListResponse(BaseModel):
    """Response schema for dataset list."""

    datasets: list[DatasetResponse]
    total: int
    limit: int
    offset: int


class DatasetScanRequest(BaseModel):
    """Request to scan a folder for SVO2 files."""

    recursive: bool = True
    extract_metadata: bool = True  # Whether to open files and extract camera metadata


class DatasetScanResponse(BaseModel):
    """Response from scanning a folder."""

    dataset_id: UUID
    files_found: int
    files_added: int
    duplicates_skipped: int
    total_size_bytes: int
    errors: list[str] = Field(default_factory=list)


class DatasetPrepareRequest(BaseModel):
    """Request to prepare (copy and rename) dataset files."""

    output_directory: str | None = None  # Override dataset output_directory


class DatasetPrepareResponse(BaseModel):
    """Response from preparing dataset files."""

    dataset_id: UUID
    status: str
    files_to_prepare: int
    message: str


class DatasetStatusUpdate(BaseModel):
    """Status update for dataset operations."""

    id: UUID
    status: str
    message: str | None = None
    progress: float | None = None  # 0.0 to 1.0


class CameraInfo(BaseModel):
    """Camera information extracted from SVO2 files."""

    camera_id: str
    camera_model: str | None = None
    camera_serial: str | None = None
    file_count: int
    total_frames: int | None = None


class DatasetCamerasResponse(BaseModel):
    """Response listing cameras in a dataset."""

    dataset_id: UUID
    cameras: list[CameraInfo]
