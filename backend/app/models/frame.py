"""Frame and frame metadata models."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.annotation import Annotation
    from backend.app.models.dataset import DatasetFile
    from backend.app.models.job import ProcessingJob


class Frame(Base, UUIDMixin, TimestampMixin):
    """Extracted frame from SVO2 file."""

    __tablename__ = "frames"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job: Mapped["ProcessingJob"] = relationship(back_populates="frames")

    # Optional link to dataset file (for new workflow with traceability)
    dataset_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dataset_file: Mapped["DatasetFile | None"] = relationship()

    # Source tracking
    svo2_file_path: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    svo2_frame_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Enhanced lineage tracking (preserves original SVO2 context)
    original_svo2_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Original filename (e.g., "1704067200.svo2")
    original_unix_timestamp: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  # Unix timestamp parsed from filename

    # Timestamps
    timestamp_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    timestamp_relative_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # Output paths (relative to job output directory)
    image_left_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_right_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    point_cloud_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    numpy_path: Mapped[str | None] = mapped_column(Text, nullable=True)  # NumPy RGB array

    # Processing status
    extraction_status: Mapped[str] = mapped_column(String(20), default="pending")
    segmentation_status: Mapped[str] = mapped_column(String(20), default="pending")
    reconstruction_status: Mapped[str] = mapped_column(String(20), default="pending")

    # Sequence info
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    frame_metadata: Mapped["FrameMetadata | None"] = relationship(
        back_populates="frame",
        uselist=False,
        cascade="all, delete-orphan",
    )
    annotations: Mapped[list["Annotation"]] = relationship(
        back_populates="frame", cascade="all, delete-orphan"
    )


class FrameMetadata(Base):
    """Extended frame metadata including IMU data."""

    __tablename__ = "frame_metadata"

    frame_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("frames.id", ondelete="CASCADE"),
        primary_key=True,
    )
    frame: Mapped["Frame"] = relationship(back_populates="frame_metadata")

    # IMU - Accelerometer (m/s²)
    accel_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    accel_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    accel_z: Mapped[float | None] = mapped_column(Float, nullable=True)

    # IMU - Gyroscope (rad/s)
    gyro_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    gyro_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    gyro_z: Mapped[float | None] = mapped_column(Float, nullable=True)

    # IMU - Magnetometer (µT)
    mag_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    mag_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    mag_z: Mapped[float | None] = mapped_column(Float, nullable=True)

    # IMU - Orientation (quaternion)
    orientation_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    orientation_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    orientation_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    orientation_z: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Barometer
    pressure_hpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Temperature sensors
    imu_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    barometer_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Camera info
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Extended metadata (JSON for flexibility)
    extended_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
