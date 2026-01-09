"""Annotation model for detection results."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.frame import Frame
    from backend.app.models.object_class import ObjectClass
    from backend.app.models.track import Track


class Annotation(Base, UUIDMixin, TimestampMixin):
    """2D and 3D detection annotation."""

    __tablename__ = "annotations"

    frame_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("frames.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    frame: Mapped["Frame"] = relationship(back_populates="annotations")

    object_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("object_classes.id"),
        nullable=False,
    )
    object_class: Mapped["ObjectClass"] = relationship(back_populates="annotations")

    track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracks.id"),
        nullable=True,
        index=True,
    )
    track: Mapped["Track | None"] = relationship(back_populates="annotations")

    # 2D Bounding Box (image coordinates)
    bbox_2d_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_2d_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_2d_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_2d_height: Mapped[float] = mapped_column(Float, nullable=False)

    # 3D Bounding Box (camera coordinates, KITTI format)
    bbox_3d_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_3d_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_3d_z: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_3d_length: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_3d_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_3d_height: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_3d_rotation_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Confidence & quality
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    mask_area: Mapped[int | None] = mapped_column(Integer, nullable=True)
    point_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truncation: Mapped[float] = mapped_column(Float, default=0.0)
    occlusion: Mapped[int] = mapped_column(Integer, default=0)

    # Alpha angle (observation angle)
    alpha: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Mask data (stored as path to compressed mask file)
    mask_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def bbox_2d(self) -> tuple[float, float, float, float]:
        """Get 2D bounding box as (x, y, width, height)."""
        return (self.bbox_2d_x, self.bbox_2d_y, self.bbox_2d_width, self.bbox_2d_height)

    @property
    def bbox_2d_xyxy(self) -> tuple[float, float, float, float]:
        """Get 2D bounding box as (x1, y1, x2, y2)."""
        return (
            self.bbox_2d_x,
            self.bbox_2d_y,
            self.bbox_2d_x + self.bbox_2d_width,
            self.bbox_2d_y + self.bbox_2d_height,
        )

    @property
    def has_3d(self) -> bool:
        """Check if 3D data is available."""
        return self.bbox_3d_x is not None and self.bbox_3d_z is not None
