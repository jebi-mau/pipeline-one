"""Training dataset model for filtered exports with lineage tracking."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.dataset import Dataset
    from backend.app.models.job import ProcessingJob


class TrainingDataset(Base, UUIDMixin, TimestampMixin):
    """A filtered training dataset exported from job results."""

    __tablename__ = "training_datasets"

    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source lineage
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_job: Mapped["ProcessingJob | None"] = relationship()

    source_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_dataset: Mapped["Dataset | None"] = relationship()

    # Filter configuration (stored for reproducibility)
    filter_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Contains: excluded_classes, excluded_annotations, diversity settings, etc.

    # Export format
    format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="both"
    )  # kitti, coco, both

    # Split configuration
    train_ratio: Mapped[float] = mapped_column(Float, default=0.7)
    val_ratio: Mapped[float] = mapped_column(Float, default=0.2)
    test_ratio: Mapped[float] = mapped_column(Float, default=0.1)
    shuffle_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Statistics
    total_frames: Mapped[int] = mapped_column(Integer, default=0)
    total_annotations: Mapped[int] = mapped_column(Integer, default=0)
    train_count: Mapped[int] = mapped_column(Integer, default=0)
    val_count: Mapped[int] = mapped_column(Integer, default=0)
    test_count: Mapped[int] = mapped_column(Integer, default=0)

    # Output paths
    output_directory: Mapped[str | None] = mapped_column(Text, nullable=True)
    kitti_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    coco_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    # pending, processing, complete, failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Frame-level provenance
    frames: Mapped[list["TrainingDatasetFrame"]] = relationship(
        back_populates="training_dataset", cascade="all, delete-orphan"
    )


class TrainingDatasetFrame(Base, UUIDMixin):
    """Individual frame included in a training dataset for detailed lineage."""

    __tablename__ = "training_dataset_frames"

    training_dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    training_dataset: Mapped["TrainingDataset"] = relationship(back_populates="frames")

    # Source frame reference
    source_frame_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Position in output dataset
    split: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # train, val, test
    output_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Annotations included (after filtering)
    annotation_count: Mapped[int] = mapped_column(Integer, default=0)
    included_annotation_ids: Mapped[list] = mapped_column(JSONB, default=list)


class FrameDiversityCache(Base, UUIDMixin, TimestampMixin):
    """Cached frame diversity analysis for a job."""

    __tablename__ = "frame_diversity_cache"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )

    # Analysis parameters
    camera: Mapped[str] = mapped_column(String(10), default="left")

    # Per-frame data (computed once, reused)
    perceptual_hashes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # { "frame_id": "hash_string", ... }

    motion_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # { "frame_id": 0.05, ... }

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, analyzing, complete, failed
    analyzed_frames: Mapped[int] = mapped_column(Integer, default=0)
    total_frames: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
