"""File-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class DirectoryInfo(BaseModel):
    """Directory information."""

    name: str
    path: str
    item_count: int = 0


class FileInfo(BaseModel):
    """Basic file information."""

    name: str
    path: str
    size_bytes: int
    modified_at: float
    metadata: dict | None = None


class DirectoryContents(BaseModel):
    """Directory contents response."""

    path: str
    directories: list[DirectoryInfo] = Field(default_factory=list)
    files: list[FileInfo] = Field(default_factory=list)


class FileMetadata(BaseModel):
    """Detailed SVO2 file metadata."""

    path: str
    name: str
    size_bytes: int
    duration_ms: int = 0
    frame_count: int = 0
    fps: float = 30.0
    resolution: list[int] = Field(default_factory=lambda: [1920, 1080])
    depth_mode: str = "NEURAL"
    has_imu: bool = True
    serial_number: str = ""
    firmware_version: str = ""
    created_at: float = 0
