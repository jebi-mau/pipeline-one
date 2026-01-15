"""Dataset and dataset file models for data ingestion."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.job import ProcessingJob


class Dataset(Base, UUIDMixin, TimestampMixin):
    """Dataset representing a collection of SVO2 files with rich metadata."""

    __tablename__ = "datasets"

    # Core metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Data context
    customer: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    site: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    equipment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collection_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Object types included in this dataset
    object_types: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    # Source folder path (original location of SVO2 files)
    source_folder: Mapped[str] = mapped_column(Text, nullable=False)

    # Output directory for processed files
    output_directory: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), default="created", nullable=False, index=True
    )
    # created, scanning, scanned, preparing, ready, processing, completed, failed

    # Statistics
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    prepared_files: Mapped[int] = mapped_column(Integer, default=0)

    # Output storage tracking (populated after dataset preparation)
    output_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    files: Mapped[list["DatasetFile"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="dataset"
    )


class DatasetFile(Base, UUIDMixin, TimestampMixin):
    """Individual SVO2 file within a dataset."""

    __tablename__ = "dataset_files"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset: Mapped["Dataset"] = relationship(back_populates="files")

    # Original file information
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    relative_path: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Path relative to source_folder

    # New file location after preparation
    renamed_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    renamed_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Camera identification (extracted from SVO2 metadata)
    camera_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    camera_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    camera_serial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # File attributes
    file_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )  # SHA256 hash for deduplication
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Recording info (from SVO2 metadata)
    recording_start_ns: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    recording_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolution_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Video container metadata (from SVO2 header)
    video_codec: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "H264", "H265/HEVC", etc.
    pixel_format: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "BGRA", "NV12", etc.
    compression_mode: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "LOSSLESS", "LOSSY"
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), default="discovered", nullable=False, index=True
    )
    # discovered, copying, copied, extracting, extracted, failed

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    copied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extended metadata (JSON for flexibility)
    # Note: Using 'extra_metadata' as attribute name since 'metadata' is reserved in SQLAlchemy
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
