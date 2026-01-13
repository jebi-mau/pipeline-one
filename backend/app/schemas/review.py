"""Review and training dataset Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Annotation Statistics
# =============================================================================


class AnnotationClassStats(BaseModel):
    """Statistics for a single annotation class."""

    class_name: str
    class_color: str
    total_count: int
    frame_count: int  # Number of frames containing this class
    avg_confidence: float
    annotation_ids: list[str]  # For individual filtering


class AnnotationStatsResponse(BaseModel):
    """Aggregated annotation statistics for filtering UI."""

    job_id: str
    total_annotations: int
    total_frames: int
    classes: list[AnnotationClassStats]


# =============================================================================
# Frame Diversity Analysis
# =============================================================================


class DiversityAnalysisRequest(BaseModel):
    """Request to analyze frame diversity."""

    similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Frames with similarity > threshold are considered duplicates",
    )
    motion_threshold: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Frames with motion < threshold are considered low-motion",
    )
    sample_camera: Literal["left", "right"] = "left"


class FrameCluster(BaseModel):
    """A cluster of similar frames."""

    representative_index: int  # The selected frame (first in cluster)
    member_indices: list[int]  # All frames in cluster
    avg_similarity: float


class DiversityAnalysisResponse(BaseModel):
    """Results of frame diversity analysis."""

    job_id: str
    status: Literal["pending", "analyzing", "complete", "failed"]
    error_message: str | None = None

    # Results (when complete)
    selected_frame_indices: list[int] = Field(default_factory=list)
    excluded_frame_indices: list[int] = Field(default_factory=list)
    clusters: list[FrameCluster] = Field(default_factory=list)

    # Statistics
    original_frame_count: int = 0
    selected_frame_count: int = 0
    reduction_percent: float = 0.0
    duplicate_pairs_found: int = 0
    low_motion_frames: int = 0

    # Per-frame data for visualization (only when requested)
    perceptual_hashes: dict[int, str] = Field(default_factory=dict)
    motion_scores: dict[int, float] = Field(default_factory=dict)


# =============================================================================
# Filter Configuration
# =============================================================================


class FilterConfiguration(BaseModel):
    """User's filter selections for training dataset export."""

    excluded_classes: list[str] = Field(default_factory=list)
    excluded_annotation_ids: list[str] = Field(default_factory=list)
    excluded_frame_indices: list[int] = Field(default_factory=list)
    diversity_applied: bool = False
    similarity_threshold: float | None = None
    motion_threshold: float | None = None


# =============================================================================
# Training Dataset
# =============================================================================


class TrainingDatasetRequest(BaseModel):
    """Request to create a training dataset."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    format: Literal["kitti", "coco", "both"] = "both"

    # Filtering configuration
    filter_config: FilterConfiguration = Field(default_factory=FilterConfiguration)

    # Split configuration
    train_ratio: float = Field(default=0.7, ge=0.0, le=1.0)
    val_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    test_ratio: float = Field(default=0.1, ge=0.0, le=1.0)
    shuffle_seed: int | None = 42

    # Export options
    include_masks: bool = True
    include_depth: bool = True
    include_3d_boxes: bool = False


class TrainingDatasetResponse(BaseModel):
    """Response from training dataset creation."""

    id: UUID
    job_id: UUID
    name: str
    status: Literal["pending", "processing", "complete", "failed"]
    progress: float = 0.0

    # Statistics
    total_frames: int = 0
    total_annotations: int = 0
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0

    created_at: datetime


class TrainingDatasetDetail(TrainingDatasetResponse):
    """Detailed training dataset information with lineage."""

    description: str | None = None
    format: str
    filter_config: FilterConfiguration

    # Lineage
    source_job_id: UUID
    source_job_name: str | None = None
    source_dataset_id: UUID | None = None
    source_dataset_name: str | None = None

    # Output
    output_directory: str | None = None
    kitti_path: str | None = None
    coco_path: str | None = None
    file_size_bytes: int | None = None

    # Timing
    completed_at: datetime | None = None
    error_message: str | None = None


class TrainingDatasetListResponse(BaseModel):
    """Response schema for training dataset list."""

    datasets: list[TrainingDatasetResponse]
    total: int


# =============================================================================
# Frame Batch for Playback
# =============================================================================


class FrameBatchRequest(BaseModel):
    """Request for batch of frames for video playback."""

    start_index: int = Field(ge=0)
    count: int = Field(default=24, ge=1, le=100)


class FrameThumbnail(BaseModel):
    """Minimal frame data for playback."""

    frame_id: str
    sequence_index: int
    svo2_frame_index: int
    thumbnail_url: str
    annotation_count: int


class FrameBatchResponse(BaseModel):
    """Response with batch of frames for video playback."""

    job_id: str
    frames: list[FrameThumbnail]
    total_frames: int
    start_index: int
    has_more: bool
