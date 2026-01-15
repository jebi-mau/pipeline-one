"""Service for managing curated datasets."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.app.models.curated_dataset import CuratedDataset
from backend.app.models.job import ProcessingJob
from backend.app.models.training_dataset import TrainingDataset
from backend.app.schemas.curated_dataset import (
    CuratedDatasetCreate,
    CuratedDatasetListPaginated,
    CuratedDatasetListResponse,
    CuratedDatasetResponse,
    CuratedDatasetUpdate,
)

logger = logging.getLogger(__name__)


class CuratedDatasetService:
    """Service for curated dataset operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: CuratedDatasetCreate) -> CuratedDatasetResponse:
        """Create a new curated dataset."""
        # Get the source job to populate dataset ID
        job = await self.db.get(ProcessingJob, data.source_job_id)
        if not job:
            raise ValueError(f"Source job {data.source_job_id} not found")

        # Check for existing curations of this job and increment version
        version_query = select(func.max(CuratedDataset.version)).where(
            CuratedDataset.source_job_id == data.source_job_id
        )
        result = await self.db.execute(version_query)
        max_version = result.scalar() or 0
        new_version = max_version + 1

        # Create the curated dataset
        curated = CuratedDataset(
            name=data.name,
            description=data.description,
            version=new_version,
            source_job_id=data.source_job_id,
            source_dataset_id=job.dataset_id if hasattr(job, 'dataset_id') else None,
            filter_config=data.filter_config.model_dump(),
            original_frame_count=data.original_frame_count,
            original_annotation_count=data.original_annotation_count,
            filtered_frame_count=data.filtered_frame_count,
            filtered_annotation_count=data.filtered_annotation_count,
            excluded_frame_ids=data.excluded_frame_ids,
            excluded_annotation_ids=data.excluded_annotation_ids,
            exclusion_reasons=data.exclusion_reasons.model_dump(),
        )

        self.db.add(curated)
        await self.db.commit()
        await self.db.refresh(curated)

        logger.info(f"Created curated dataset: {curated.name} (v{curated.version})")

        return await self._to_response(curated)

    async def get(self, curated_id: UUID) -> CuratedDatasetResponse | None:
        """Get a curated dataset by ID."""
        query = (
            select(CuratedDataset)
            .options(
                joinedload(CuratedDataset.source_job),
                joinedload(CuratedDataset.source_dataset),
            )
            .where(CuratedDataset.id == curated_id)
        )
        result = await self.db.execute(query)
        curated = result.unique().scalar_one_or_none()

        if not curated:
            return None

        return await self._to_response(curated)

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        job_id: UUID | None = None,
    ) -> CuratedDatasetListPaginated:
        """List curated datasets with pagination."""
        # Base query
        query = select(CuratedDataset).options(
            joinedload(CuratedDataset.source_job),
            joinedload(CuratedDataset.source_dataset),
        )

        # Filter by job if specified
        if job_id:
            query = query.where(CuratedDataset.source_job_id == job_id)

        # Get total count
        count_query = select(func.count()).select_from(CuratedDataset)
        if job_id:
            count_query = count_query.where(CuratedDataset.source_job_id == job_id)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(CuratedDataset.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        curated_datasets = result.unique().scalars().all()

        # Build response items
        items = []
        for curated in curated_datasets:
            # Count related training datasets
            training_count_query = select(func.count()).select_from(TrainingDataset).where(
                TrainingDataset.source_curated_dataset_id == curated.id
            )
            training_count_result = await self.db.execute(training_count_query)
            training_count = training_count_result.scalar() or 0

            items.append(CuratedDatasetListResponse(
                id=curated.id,
                name=curated.name,
                description=curated.description,
                version=curated.version,
                source_job_id=curated.source_job_id,
                source_job_name=curated.source_job.name if curated.source_job else None,
                source_dataset_id=curated.source_dataset_id,
                source_dataset_name=curated.source_dataset.name if curated.source_dataset else None,
                filter_config=curated.filter_config,
                original_frame_count=curated.original_frame_count,
                original_annotation_count=curated.original_annotation_count,
                filtered_frame_count=curated.filtered_frame_count,
                filtered_annotation_count=curated.filtered_annotation_count,
                training_datasets_count=training_count,
                created_at=curated.created_at,
            ))

        return CuratedDatasetListPaginated(
            curated_datasets=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update(
        self, curated_id: UUID, data: CuratedDatasetUpdate
    ) -> CuratedDatasetResponse | None:
        """Update curated dataset metadata (name, description only)."""
        curated = await self.db.get(CuratedDataset, curated_id)
        if not curated:
            return None

        if data.name is not None:
            curated.name = data.name
        if data.description is not None:
            curated.description = data.description

        await self.db.commit()
        await self.db.refresh(curated)

        return await self._to_response(curated)

    async def delete(self, curated_id: UUID) -> bool:
        """Delete a curated dataset."""
        curated = await self.db.get(CuratedDataset, curated_id)
        if not curated:
            return False

        await self.db.delete(curated)
        await self.db.commit()

        logger.info(f"Deleted curated dataset: {curated.name}")
        return True

    async def _to_response(self, curated: CuratedDataset) -> CuratedDatasetResponse:
        """Convert model to response schema."""
        # Load relationships if needed
        if not curated.source_job:
            await self.db.refresh(curated, ["source_job", "source_dataset"])

        # Count related training datasets
        training_count_query = select(func.count()).select_from(TrainingDataset).where(
            TrainingDataset.source_curated_dataset_id == curated.id
        )
        training_count_result = await self.db.execute(training_count_query)
        training_count = training_count_result.scalar() or 0

        return CuratedDatasetResponse(
            id=curated.id,
            name=curated.name,
            description=curated.description,
            version=curated.version,
            source_job_id=curated.source_job_id,
            source_job_name=curated.source_job.name if curated.source_job else None,
            source_dataset_id=curated.source_dataset_id,
            source_dataset_name=curated.source_dataset.name if curated.source_dataset else None,
            filter_config=curated.filter_config,
            original_frame_count=curated.original_frame_count,
            original_annotation_count=curated.original_annotation_count,
            filtered_frame_count=curated.filtered_frame_count,
            filtered_annotation_count=curated.filtered_annotation_count,
            frames_removed=curated.frames_removed,
            annotations_removed=curated.annotations_removed,
            reduction_percentage=curated.reduction_percentage,
            excluded_frame_ids=curated.excluded_frame_ids,
            excluded_annotation_ids=curated.excluded_annotation_ids,
            exclusion_reasons=curated.exclusion_reasons,
            created_by=curated.created_by,
            created_at=curated.created_at,
            updated_at=curated.updated_at,
            training_datasets_count=training_count,
        )
