"""Preset model for saved configurations."""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Preset(Base, UUIDMixin, TimestampMixin):
    """Saved configuration preset."""

    __tablename__ = "presets"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configuration (JSON object)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
