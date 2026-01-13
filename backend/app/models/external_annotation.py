"""External annotation models for imported annotations from CVAT and other tools."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.dataset import Dataset
    from backend.app.models.frame import Frame


class AnnotationImport(Base, UUIDMixin, TimestampMixin):
    """Record of an annotation import operation."""

    __tablename__ = "annotation_imports"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset: Mapped["Dataset"] = relationship()

    # Source information
    source_tool: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "cvat", "labelimg", "labelme", etc.
    source_format: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "xml", "json", "coco", "yolo"
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Import status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    # pending, processing, completed, failed

    # Statistics
    total_images: Mapped[int] = mapped_column(Integer, default=0)
    matched_frames: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_images: Mapped[int] = mapped_column(Integer, default=0)
    total_annotations: Mapped[int] = mapped_column(Integer, default=0)

    # Processing timestamps
    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw import data for debugging/reprocessing
    import_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    annotations: Mapped[list["ExternalAnnotation"]] = relationship(
        back_populates="import_record", cascade="all, delete-orphan"
    )


class ExternalAnnotation(Base, UUIDMixin, TimestampMixin):
    """Individual annotation from external tool (CVAT, etc.)."""

    __tablename__ = "external_annotations"

    # Link to import record
    import_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("annotation_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_record: Mapped["AnnotationImport"] = relationship(back_populates="annotations")

    # Link to matched frame (nullable if unmatched)
    frame_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("frames.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    frame: Mapped["Frame | None"] = relationship()

    # Direct link to source dataset for lineage traceability
    source_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_dataset: Mapped["Dataset | None"] = relationship()

    # Original image filename from annotation file (for matching)
    source_image_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    # Enhanced matching metadata
    match_strategy: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "filename", "frame_index", "timestamp"
    source_frame_index: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Frame index parsed from annotation filename

    # Annotation data
    label: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    annotation_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "bbox", "polygon", "polyline", "points"

    # Bounding box (if type is bbox)
    bbox_x: Mapped[float | None] = mapped_column(nullable=True)
    bbox_y: Mapped[float | None] = mapped_column(nullable=True)
    bbox_width: Mapped[float | None] = mapped_column(nullable=True)
    bbox_height: Mapped[float | None] = mapped_column(nullable=True)

    # Polygon/polyline points (JSON array of [x, y] pairs)
    points: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Additional attributes from annotation tool
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Occurrence ID for tracking same object across frames
    occurrence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Z-order for overlapping annotations
    z_order: Mapped[int] = mapped_column(Integer, default=0)

    # Whether this annotation has been matched and validated
    is_matched: Mapped[bool] = mapped_column(default=False)
    match_confidence: Mapped[float | None] = mapped_column(nullable=True)

    @property
    def bbox(self) -> tuple[float, float, float, float] | None:
        """Get bounding box as (x, y, width, height)."""
        if self.bbox_x is None:
            return None
        return (self.bbox_x, self.bbox_y, self.bbox_width, self.bbox_height)

    @property
    def bbox_xyxy(self) -> tuple[float, float, float, float] | None:
        """Get bounding box as (x1, y1, x2, y2)."""
        if self.bbox_x is None:
            return None
        return (
            self.bbox_x,
            self.bbox_y,
            self.bbox_x + self.bbox_width,
            self.bbox_y + self.bbox_height,
        )
