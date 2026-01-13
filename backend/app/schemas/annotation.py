"""Annotation-related Pydantic schemas for external annotation imports."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnnotationImportRequest(BaseModel):
    """Request to import annotations from external tool."""

    source_path: str = Field(min_length=1)
    source_tool: Literal["cvat", "labelimg", "labelme", "coco"] = "cvat"
    source_format: Literal["xml", "json", "coco", "yolo"] = "xml"
    match_by: Literal["filename", "frame_index"] = "filename"


class AnnotationImportResponse(BaseModel):
    """Response from annotation import."""

    import_id: UUID
    dataset_id: UUID
    status: str
    message: str
    total_images: int = 0
    total_annotations: int = 0


class AnnotationImportSummary(BaseModel):
    """Summary of an annotation import."""

    id: UUID
    dataset_id: UUID
    source_tool: str
    source_format: str
    source_filename: str
    status: str
    total_images: int
    matched_frames: int
    unmatched_images: int
    total_annotations: int
    imported_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime


class AnnotationImportDetail(AnnotationImportSummary):
    """Detailed annotation import information."""

    source_path: str
    import_metadata: dict | None = None
    updated_at: datetime


class AnnotationImportListResponse(BaseModel):
    """Response for listing annotation imports."""

    imports: list[AnnotationImportSummary]
    total: int
    limit: int
    offset: int


class ExternalAnnotationSummary(BaseModel):
    """Summary of an external annotation."""

    id: UUID
    frame_id: UUID | None = None
    source_image_name: str
    label: str
    annotation_type: str
    bbox: tuple[float, float, float, float] | None = None  # x, y, width, height
    is_matched: bool


class ExternalAnnotationDetail(BaseModel):
    """Detailed external annotation information."""

    id: UUID
    import_id: UUID
    frame_id: UUID | None = None
    source_image_name: str
    label: str
    annotation_type: str
    bbox_x: float | None = None
    bbox_y: float | None = None
    bbox_width: float | None = None
    bbox_height: float | None = None
    points: list | None = None
    attributes: dict | None = None
    occurrence_id: int | None = None
    z_order: int
    is_matched: bool
    match_confidence: float | None = None
    created_at: datetime
    updated_at: datetime


class ExternalAnnotationListResponse(BaseModel):
    """Response for listing external annotations."""

    annotations: list[ExternalAnnotationSummary]
    total: int
    matched: int
    unmatched: int
    limit: int
    offset: int


class FrameAnnotationsResponse(BaseModel):
    """Annotations for a specific frame."""

    frame_id: UUID
    annotations: list[ExternalAnnotationDetail]
    total: int


class AnnotationMatchStats(BaseModel):
    """Statistics about annotation matching."""

    import_id: UUID
    total_annotations: int
    matched_annotations: int
    unmatched_annotations: int
    match_rate: float  # 0.0 to 1.0
    labels: dict[str, int]  # label -> count


class TrainingExportRequest(BaseModel):
    """Request to export training data."""

    output_directory: str | None = None
    format: Literal["tfrecord", "coco", "both"] = "both"
    split_ratio: tuple[float, float, float] = Field(
        default=(0.7, 0.2, 0.1),
        description="Train/val/test split ratios"
    )
    include_unmatched: bool = False
    labels_filter: list[str] | None = None  # Only export specific labels
    shuffle_seed: int | None = 42


class TrainingExportResponse(BaseModel):
    """Response from training export."""

    dataset_id: UUID
    status: str
    output_directory: str
    format: str
    total_images: int
    total_annotations: int
    train_count: int
    val_count: int
    test_count: int
    message: str


class TrainingExportProgress(BaseModel):
    """Progress update for training export."""

    dataset_id: UUID
    status: str
    progress: float  # 0.0 to 1.0
    current_step: str
    images_processed: int
    total_images: int
