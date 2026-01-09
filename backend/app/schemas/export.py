"""Export-related Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ExportOptions(BaseModel):
    """Export options for different formats."""

    # KITTI options
    include_depth: bool = True
    include_velodyne: bool = True
    include_oxts: bool = True

    # COCO options
    include_segmentation: bool = True

    # JSON options
    include_point_clouds: bool = False
    compress: bool = True


class ExportRequest(BaseModel):
    """Request schema for creating an export."""

    format: Literal["kitti", "coco", "json", "csv"]
    options: ExportOptions = Field(default_factory=ExportOptions)


class ExportResponse(BaseModel):
    """Response schema for export creation."""

    id: UUID
    job_id: UUID
    format: str
    status: Literal["pending", "generating", "completed", "failed"]
    created_at: datetime


class ExportStatus(BaseModel):
    """Response schema for export status."""

    id: UUID
    job_id: UUID
    format: str
    status: Literal["pending", "generating", "completed", "failed"]
    progress: float = 0.0
    file_size: int | None = None
    output_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
