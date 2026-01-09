"""Configuration-related Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ObjectClassCreate(BaseModel):
    """Request schema for creating an object class."""

    name: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1, max_length=500, description="SAM 3 text prompt")
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    kitti_type: str | None = Field(default=None, description="KITTI type mapping")


class ObjectClassResponse(BaseModel):
    """Response schema for object class."""

    id: UUID
    name: str
    prompt: str
    color: str
    kitti_type: str | None
    is_preset: bool
    created_at: datetime


class PresetConfig(BaseModel):
    """Preset configuration settings."""

    object_class_ids: list[str]
    sam3_model_variant: str = "sam3_hiera_large"
    sam3_confidence_threshold: float = 0.5
    sam3_iou_threshold: float = 0.7
    sam3_batch_size: int = 8
    frame_skip: int = 1
    enable_tracking: bool = True


class PresetCreate(BaseModel):
    """Request schema for creating a preset."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    config: PresetConfig


class PresetResponse(BaseModel):
    """Response schema for preset."""

    id: UUID
    name: str
    description: str | None
    config: PresetConfig
    created_at: datetime


class ModelVariant(BaseModel):
    """SAM 3 model variant information."""

    name: str
    size_mb: int
    vram_required_gb: float
    recommended_for: str


class ModelInfo(BaseModel):
    """SAM 3 model information."""

    available_models: list[ModelVariant]
    default_model: str
    loaded_model: str | None = None
    gpu_available: bool
    gpu_name: str | None = None
    gpu_vram_gb: float | None = None


class SystemConfig(BaseModel):
    """System configuration information."""

    app_name: str
    app_version: str
    environment: str
    data_root: str
    svo2_directory: str
    output_directory: str
    models_directory: str
    zed_sdk_installed: bool
    sam3_model_loaded: bool
    gpu_available: bool
