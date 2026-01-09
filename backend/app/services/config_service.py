"""Configuration management service."""

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.object_class import ObjectClass
from backend.app.models.preset import Preset
from backend.app.schemas.config import (
    ModelInfo,
    ModelVariant,
    ObjectClassCreate,
    ObjectClassResponse,
    PresetConfig,
    PresetCreate,
    PresetResponse,
    SystemConfig,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class ConfigService:
    """Service for configuration management."""

    def __init__(self, db: AsyncSession | None):
        self.db = db

    async def list_object_classes(
        self, include_custom: bool = True
    ) -> list[ObjectClassResponse]:
        """List all object classes."""
        if self.db is None:
            return []

        query = select(ObjectClass)
        if not include_custom:
            query = query.where(ObjectClass.is_preset == True)  # noqa: E712

        result = await self.db.execute(query.order_by(ObjectClass.name))
        return [
            ObjectClassResponse(
                id=obj.id,
                name=obj.name,
                prompt=obj.prompt,
                color=obj.color,
                kitti_type=obj.kitti_type,
                is_preset=obj.is_preset,
                created_at=obj.created_at,
            )
            for obj in result.scalars().all()
        ]

    async def create_object_class(
        self, data: ObjectClassCreate
    ) -> ObjectClassResponse:
        """Create a custom object class."""
        if self.db is None:
            raise ValueError("Database session required")

        obj = ObjectClass(
            name=data.name,
            prompt=data.prompt,
            color=data.color,
            kitti_type=data.kitti_type,
            is_preset=False,
        )
        self.db.add(obj)
        await self.db.flush()

        logger.info(f"Created object class: {obj.name}")
        return ObjectClassResponse(
            id=obj.id,
            name=obj.name,
            prompt=obj.prompt,
            color=obj.color,
            kitti_type=obj.kitti_type,
            is_preset=obj.is_preset,
            created_at=obj.created_at,
        )

    async def get_object_class(self, class_id: UUID) -> ObjectClassResponse | None:
        """Get object class by ID."""
        if self.db is None:
            return None

        result = await self.db.execute(
            select(ObjectClass).where(ObjectClass.id == class_id)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            return None

        return ObjectClassResponse(
            id=obj.id,
            name=obj.name,
            prompt=obj.prompt,
            color=obj.color,
            kitti_type=obj.kitti_type,
            is_preset=obj.is_preset,
            created_at=obj.created_at,
        )

    async def delete_object_class(self, class_id: UUID) -> bool:
        """Delete a custom object class."""
        if self.db is None:
            return False

        result = await self.db.execute(
            select(ObjectClass).where(
                ObjectClass.id == class_id,
                ObjectClass.is_preset == False,  # noqa: E712
            )
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            return False

        await self.db.delete(obj)
        logger.info(f"Deleted object class: {obj.name}")
        return True

    async def list_presets(self) -> list[PresetResponse]:
        """List all saved presets."""
        if self.db is None:
            return []

        result = await self.db.execute(select(Preset).order_by(Preset.name))
        return [
            PresetResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                config=PresetConfig(**p.config),
                created_at=p.created_at,
            )
            for p in result.scalars().all()
        ]

    async def create_preset(self, data: PresetCreate) -> PresetResponse:
        """Create a new preset."""
        if self.db is None:
            raise ValueError("Database session required")

        preset = Preset(
            name=data.name,
            description=data.description,
            config=data.config.model_dump(),
        )
        self.db.add(preset)
        await self.db.flush()

        logger.info(f"Created preset: {preset.name}")
        return PresetResponse(
            id=preset.id,
            name=preset.name,
            description=preset.description,
            config=data.config,
            created_at=preset.created_at,
        )

    async def get_preset(self, preset_id: UUID) -> PresetResponse | None:
        """Get preset by ID."""
        if self.db is None:
            return None

        result = await self.db.execute(
            select(Preset).where(Preset.id == preset_id)
        )
        preset = result.scalar_one_or_none()
        if preset is None:
            return None

        return PresetResponse(
            id=preset.id,
            name=preset.name,
            description=preset.description,
            config=PresetConfig(**preset.config),
            created_at=preset.created_at,
        )

    async def delete_preset(self, preset_id: UUID) -> bool:
        """Delete a preset."""
        if self.db is None:
            return False

        result = await self.db.execute(
            select(Preset).where(Preset.id == preset_id)
        )
        preset = result.scalar_one_or_none()
        if preset is None:
            return False

        await self.db.delete(preset)
        logger.info(f"Deleted preset: {preset.name}")
        return True

    async def get_model_info(self) -> ModelInfo:
        """Get SAM 3 model information."""
        # TODO: Implement actual GPU detection
        return ModelInfo(
            available_models=[
                ModelVariant(
                    name="sam3_hiera_tiny",
                    size_mb=400,
                    vram_required_gb=4.0,
                    recommended_for="Quick testing",
                ),
                ModelVariant(
                    name="sam3_hiera_small",
                    size_mb=900,
                    vram_required_gb=8.0,
                    recommended_for="Balanced performance",
                ),
                ModelVariant(
                    name="sam3_hiera_base",
                    size_mb=1800,
                    vram_required_gb=12.0,
                    recommended_for="Production (default)",
                ),
                ModelVariant(
                    name="sam3_hiera_large",
                    size_mb=2400,
                    vram_required_gb=16.0,
                    recommended_for="Maximum accuracy",
                ),
            ],
            default_model=settings.sam3_model_variant,
            loaded_model=None,
            gpu_available=True,  # TODO: Detect
            gpu_name="NVIDIA GeForce RTX 5090",  # TODO: Detect
            gpu_vram_gb=32.0,  # TODO: Detect
        )

    async def get_system_config(self) -> SystemConfig:
        """Get system configuration."""
        zed_installed = Path(settings.zed_sdk_path).exists()

        return SystemConfig(
            app_name=settings.app_name,
            app_version="1.0.0",
            environment=settings.app_env,
            data_root=str(settings.data_root),
            svo2_directory=str(settings.svo2_directory),
            output_directory=str(settings.output_directory),
            models_directory=str(settings.models_directory),
            zed_sdk_installed=zed_installed,
            sam3_model_loaded=False,  # TODO: Check
            gpu_available=True,  # TODO: Detect
        )
