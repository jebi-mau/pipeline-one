"""Curated dataset model - snapshot of review filtering for reproducible exports."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.dataset import Dataset
    from backend.app.models.job import ProcessingJob
    from backend.app.models.training_dataset import TrainingDataset


class CuratedDataset(Base, UUIDMixin, TimestampMixin):
    """A curated dataset representing a snapshot of review filtering.

    This is the output of Step 3 (Review) in the pipeline workflow.
    It captures the filter configuration and can be used to create
    multiple training dataset exports with consistent filtering.
    """

    __tablename__ = "curated_datasets"

    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Source lineage - the job and dataset this curation is based on
    source_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_job: Mapped["ProcessingJob"] = relationship(
        foreign_keys=[source_job_id],
        lazy="joined",
    )

    source_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_dataset: Mapped["Dataset | None"] = relationship(
        foreign_keys=[source_dataset_id],
        lazy="joined",
    )

    # Filter configuration snapshot (immutable after creation)
    # This captures the exact state of filters when the curation was saved
    filter_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #   "excluded_classes": ["background", "unknown"],
    #   "excluded_annotation_ids": ["uuid1", "uuid2", ...],
    #   "diversity_applied": true,
    #   "diversity_similarity_threshold": 0.85,
    #   "diversity_motion_threshold": 0.02,
    #   "excluded_frame_indices": [1, 5, 12, ...],
    # }

    # Statistics - original counts (before filtering)
    original_frame_count: Mapped[int] = mapped_column(Integer, default=0)
    original_annotation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Statistics - after filtering
    filtered_frame_count: Mapped[int] = mapped_column(Integer, default=0)
    filtered_annotation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Detailed exclusion tracking (for audit and UI display)
    excluded_frame_ids: Mapped[list] = mapped_column(JSONB, default=list)
    excluded_annotation_ids: Mapped[list] = mapped_column(JSONB, default=list)

    # Exclusion reasons breakdown
    # { "class_filter": ["ann_id1", ...], "diversity": ["frame_id1", ...], "manual": [...] }
    exclusion_reasons: Mapped[dict] = mapped_column(JSONB, default=dict)

    # User tracking (for future multi-user support)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Related training dataset exports
    training_datasets: Mapped[list["TrainingDataset"]] = relationship(
        "TrainingDataset",
        back_populates="source_curated_dataset",
        foreign_keys="TrainingDataset.source_curated_dataset_id",
    )

    def __repr__(self) -> str:
        return f"<CuratedDataset(id={self.id}, name='{self.name}', v{self.version})>"

    @property
    def frames_removed(self) -> int:
        """Number of frames removed by filtering."""
        return self.original_frame_count - self.filtered_frame_count

    @property
    def annotations_removed(self) -> int:
        """Number of annotations removed by filtering."""
        return self.original_annotation_count - self.filtered_annotation_count

    @property
    def reduction_percentage(self) -> float:
        """Percentage of frames removed."""
        if self.original_frame_count == 0:
            return 0.0
        return (self.frames_removed / self.original_frame_count) * 100
