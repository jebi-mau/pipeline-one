"""Camera calibration model."""

from sqlalchemy import Float, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Calibration(Base, UUIDMixin, TimestampMixin):
    """Camera calibration data per SVO2 file."""

    __tablename__ = "calibrations"

    svo2_file_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    # Camera intrinsics (left camera)
    fx: Mapped[float] = mapped_column(Float, nullable=False)
    fy: Mapped[float] = mapped_column(Float, nullable=False)
    cx: Mapped[float] = mapped_column(Float, nullable=False)
    cy: Mapped[float] = mapped_column(Float, nullable=False)

    # Stereo baseline
    baseline: Mapped[float] = mapped_column(Float, nullable=False)

    # Distortion coefficients (JSON array)
    distortion_coeffs: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)

    # Full calibration matrices (JSON)
    calibration_matrix: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rectification_matrix: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    projection_matrix_left: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    projection_matrix_right: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Resolution
    image_width: Mapped[int] = mapped_column(Integer, nullable=False)
    image_height: Mapped[int] = mapped_column(Integer, nullable=False)
