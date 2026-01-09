"""Track model for object tracking."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.annotation import Annotation
    from backend.app.models.job import ProcessingJob
    from backend.app.models.object_class import ObjectClass


class Track(Base, UUIDMixin, TimestampMixin):
    """Persistent object track across frames."""

    __tablename__ = "tracks"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job: Mapped["ProcessingJob"] = relationship(back_populates="tracks")

    object_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("object_classes.id"),
        nullable=False,
    )
    object_class: Mapped["ObjectClass"] = relationship(back_populates="tracks")

    # Track lifecycle
    first_frame_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("frames.id"),
        nullable=False,
    )
    last_frame_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("frames.id"),
        nullable=False,
    )
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Track quality metrics
    avg_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")

    # Relationships
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="track")
