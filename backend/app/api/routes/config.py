"""Configuration management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.config import (
    ModelInfo,
    ObjectClassCreate,
    ObjectClassResponse,
    PresetCreate,
    PresetResponse,
    SystemConfig,
)
from backend.app.services.config_service import ConfigService

router = APIRouter()


@router.get("/object-classes", response_model=list[ObjectClassResponse])
async def list_object_classes(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_custom: bool = True,
) -> list[ObjectClassResponse]:
    """
    List all available object classes.

    Returns both preset (built-in) and custom user-defined classes.
    """
    service = ConfigService(db)
    return await service.list_object_classes(include_custom=include_custom)


@router.post("/object-classes", response_model=ObjectClassResponse, status_code=201)
async def create_object_class(
    object_class: ObjectClassCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ObjectClassResponse:
    """
    Create a custom object class.
    """
    service = ConfigService(db)
    return await service.create_object_class(object_class)


@router.get("/object-classes/{class_id}", response_model=ObjectClassResponse)
async def get_object_class(
    class_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ObjectClassResponse:
    """
    Get object class by ID.
    """
    service = ConfigService(db)
    obj_class = await service.get_object_class(class_id)
    if obj_class is None:
        raise HTTPException(status_code=404, detail="Object class not found")
    return obj_class


@router.delete("/object-classes/{class_id}", status_code=204)
async def delete_object_class(
    class_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a custom object class.

    Preset classes cannot be deleted.
    """
    service = ConfigService(db)
    success = await service.delete_object_class(class_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Object class not found or is a preset class",
        )


@router.get("/presets", response_model=list[PresetResponse])
async def list_presets(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PresetResponse]:
    """
    List all saved configuration presets.
    """
    service = ConfigService(db)
    return await service.list_presets()


@router.post("/presets", response_model=PresetResponse, status_code=201)
async def create_preset(
    preset: PresetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresetResponse:
    """
    Save a new configuration preset.
    """
    service = ConfigService(db)
    return await service.create_preset(preset)


@router.get("/presets/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresetResponse:
    """
    Get preset by ID.
    """
    service = ConfigService(db)
    preset = await service.get_preset(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.delete("/presets/{preset_id}", status_code=204)
async def delete_preset(
    preset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a saved preset.
    """
    service = ConfigService(db)
    success = await service.delete_preset(preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")


@router.get("/model-info", response_model=ModelInfo)
async def get_model_info() -> ModelInfo:
    """
    Get information about available SAM 3 models.
    """
    service = ConfigService(None)
    return await service.get_model_info()


@router.get("/system", response_model=SystemConfig)
async def get_system_config() -> SystemConfig:
    """
    Get system configuration and paths.
    """
    service = ConfigService(None)
    return await service.get_system_config()
