"""Data-related Pydantic schemas for frame browsing and correlation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BBox2D(BaseModel):
    """2D bounding box."""
    x: float
    y: float
    width: float
    height: float


class BBox3D(BaseModel):
    """3D bounding box in camera coordinates."""
    x: float  # center x
    y: float  # center y
    z: float  # center z (depth)
    length: float
    width: float
    height: float
    rotation_y: float = 0.0


class AnnotationSummary(BaseModel):
    """Summary of an annotation/detection."""
    id: str
    class_name: str
    class_color: str = "#3b82f6"
    confidence: float
    bbox_2d: BBox2D
    bbox_3d: BBox3D | None = None
    mask_url: str | None = None
    track_id: str | None = None
    distance: float | None = None  # Distance in meters (center patch average)


class FrameMetadataSummary(BaseModel):
    """Frame metadata summary including IMU data."""
    image_width: int | None = None
    image_height: int | None = None
    # Accelerometer (m/s²)
    accel_x: float | None = None
    accel_y: float | None = None
    accel_z: float | None = None
    # Gyroscope (rad/s)
    gyro_x: float | None = None
    gyro_y: float | None = None
    gyro_z: float | None = None
    # Orientation (degrees, converted from quaternion)
    orientation_roll: float | None = None
    orientation_pitch: float | None = None
    orientation_yaw: float | None = None


class FrameSummary(BaseModel):
    """Summary of a frame for list view."""
    id: str
    frame_id: str  # e.g., "e854478a39923a10_000000"
    sequence_index: int
    svo2_frame_index: int
    svo2_file: str
    timestamp_ns: int | None = None
    has_left_image: bool = False
    has_right_image: bool = False
    has_depth: bool = False
    has_pointcloud: bool = False
    detection_count: int = 0
    thumbnail_url: str | None = None


class FrameDetail(BaseModel):
    """Detailed frame information."""
    id: str
    frame_id: str
    sequence_index: int
    svo2_frame_index: int
    svo2_file: str
    timestamp_ns: int | None = None
    # File URLs (served via API)
    image_left_url: str | None = None
    image_right_url: str | None = None
    depth_url: str | None = None
    pointcloud_url: str | None = None
    # Status
    segmentation_complete: bool = False
    reconstruction_complete: bool = False
    tracking_complete: bool = False
    # Related data
    annotations: list[AnnotationSummary] = Field(default_factory=list)
    metadata: FrameMetadataSummary | None = None


class FrameListResponse(BaseModel):
    """Response for frame list endpoint."""
    frames: list[FrameSummary]
    total: int
    limit: int
    offset: int
    job_id: str


class SVO2FileSummary(BaseModel):
    """Summary of an SVO2 source file."""
    filename: str
    path: str
    total_frames_original: int | None = None
    frames_extracted: int = 0
    frame_skip: int = 1


class DataSummary(BaseModel):
    """Summary of extracted data for a job."""
    job_id: str
    job_name: str
    status: str
    total_frames: int = 0
    frames_with_left_image: int = 0
    frames_with_right_image: int = 0
    frames_with_depth: int = 0
    frames_with_pointcloud: int = 0
    total_detections: int = 0
    detections_by_class: dict[str, int] = Field(default_factory=dict)
    total_tracks: int = 0
    svo2_files: list[SVO2FileSummary] = Field(default_factory=list)
    output_directory: str | None = None
    frame_skip: int = 1
    created_at: datetime | None = None
    completed_at: datetime | None = None


class CorrelationEntry(BaseModel):
    """Single entry in the correlation table."""
    sequence_index: int
    svo2_frame_index: int
    frame_id: str
    has_left_image: bool = False
    has_right_image: bool = False
    has_depth: bool = False
    has_pointcloud: bool = False
    has_imu: bool = False
    detection_count: int = 0


class CorrelationTableResponse(BaseModel):
    """Response for correlation table."""
    entries: list[CorrelationEntry]
    total: int
    svo2_file: str
    frame_skip: int
