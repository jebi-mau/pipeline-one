"""Processing job models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.export import Export
    from backend.app.models.frame import Frame
    from backend.app.models.track import Track


class JobConfig(Base, UUIDMixin, TimestampMixin):
    """Job configuration settings."""

    __tablename__ = "job_configs"

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # SAM 3 settings
    sam3_model_variant: Mapped[str] = mapped_column(
        String(50), default="sam3_hiera_large"
    )
    sam3_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    sam3_iou_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    sam3_batch_size: Mapped[int] = mapped_column(Integer, default=8)

    # Processing settings
    frame_skip: Mapped[int] = mapped_column(Integer, default=1)
    enable_tracking: Mapped[bool] = mapped_column(default=True)
    export_3d_data: Mapped[bool] = mapped_column(default=True)

    # Object classes (JSON array of class IDs)
    object_class_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    # Relationship
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="config")


class ProcessingJob(Base, UUIDMixin, TimestampMixin):
    """Processing job model."""

    __tablename__ = "processing_jobs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    current_stage: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    # Input configuration
    input_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    output_directory: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configuration
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_configs.id"), nullable=False
    )
    config: Mapped["JobConfig"] = relationship(back_populates="jobs")

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Statistics (populated after completion)
    total_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_detections: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    frames: Mapped[list["Frame"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    tracks: Mapped[list["Track"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    exports: Mapped[list["Export"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def current_stage_name(self) -> str | None:
        """Get human-readable stage name."""
        stage_names = {
            0: None,
            1: "extraction",
            2: "segmentation",
            3: "reconstruction",
            4: "tracking",
        }
        return stage_names.get(self.current_stage)
