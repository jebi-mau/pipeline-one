"""Object class model."""

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.annotation import Annotation
    from backend.app.models.track import Track


class ObjectClass(Base, UUIDMixin, TimestampMixin):
    """Detection object class definition."""

    __tablename__ = "object_classes"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)  # Hex color
    kitti_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_preset: Mapped[bool] = mapped_column(default=False)

    # Relationships
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="object_class")
    tracks: Mapped[list["Track"]] = relationship(back_populates="object_class")
