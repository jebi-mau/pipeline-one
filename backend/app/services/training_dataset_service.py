"""Training dataset export service with lineage tracking."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models import ProcessingJob
from backend.app.models.training_dataset import (
    TrainingDataset,
    TrainingDatasetFrame,
)
from backend.app.schemas.review import (
    FilterConfiguration,
    TrainingDatasetDetail,
    TrainingDatasetListResponse,
    TrainingDatasetRequest,
    TrainingDatasetResponse,
)

logger = logging.getLogger(__name__)


class TrainingDatasetService:
    """Service for training dataset export with lineage tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_training_dataset(
        self, job_id: UUID, request: TrainingDatasetRequest
    ) -> TrainingDataset:
        """Create a training dataset record and prepare for export."""
        # Get source job
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Validate split ratios
        total_ratio = request.train_ratio + request.val_ratio + request.test_ratio
        if abs(total_ratio - 1.0) > 0.001:
            raise ValueError(
                f"Split ratios must sum to 1.0, got {total_ratio}"
            )

        # Create training dataset record
        training_dataset = TrainingDataset(
            name=request.name,
            description=request.description,
            source_job_id=job_id,
            source_dataset_id=job.dataset_id,
            filter_config=request.filter_config.model_dump(),
            format=request.format,
            train_ratio=request.train_ratio,
            val_ratio=request.val_ratio,
            test_ratio=request.test_ratio,
            shuffle_seed=request.shuffle_seed,
            status="pending",
        )

        self.db.add(training_dataset)
        await self.db.commit()
        await self.db.refresh(training_dataset)

        return training_dataset

    async def get_training_dataset(
        self, dataset_id: UUID
    ) -> TrainingDatasetDetail | None:
        """Get training dataset with full details."""
        result = await self.db.execute(
            select(TrainingDataset)
            .where(TrainingDataset.id == dataset_id)
            .options(
                selectinload(TrainingDataset.source_job),
                selectinload(TrainingDataset.source_dataset),
            )
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            return None

        return TrainingDatasetDetail(
            id=dataset.id,
            job_id=dataset.source_job_id,
            name=dataset.name,
            description=dataset.description,
            format=dataset.format,
            filter_config=FilterConfiguration(**dataset.filter_config),
            status=dataset.status,
            progress=dataset.progress,
            total_frames=dataset.total_frames,
            total_annotations=dataset.total_annotations,
            train_count=dataset.train_count,
            val_count=dataset.val_count,
            test_count=dataset.test_count,
            source_job_id=dataset.source_job_id,
            source_job_name=dataset.source_job.name if dataset.source_job else None,
            source_dataset_id=dataset.source_dataset_id,
            source_dataset_name=(
                dataset.source_dataset.name if dataset.source_dataset else None
            ),
            output_directory=dataset.output_directory,
            kitti_path=dataset.kitti_path,
            coco_path=dataset.coco_path,
            file_size_bytes=dataset.file_size_bytes,
            created_at=dataset.created_at,
            completed_at=dataset.completed_at,
            error_message=dataset.error_message,
        )

    async def get_training_dataset_response(
        self, dataset_id: UUID
    ) -> TrainingDatasetResponse | None:
        """Get training dataset summary response."""
        result = await self.db.execute(
            select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            return None

        return TrainingDatasetResponse(
            id=dataset.id,
            job_id=dataset.source_job_id,
            name=dataset.name,
            status=dataset.status,
            progress=dataset.progress,
            total_frames=dataset.total_frames,
            total_annotations=dataset.total_annotations,
            train_count=dataset.train_count,
            val_count=dataset.val_count,
            test_count=dataset.test_count,
            created_at=dataset.created_at,
        )

    async def list_training_datasets(
        self, job_id: UUID | None = None
    ) -> TrainingDatasetListResponse:
        """List training datasets, optionally filtered by source job."""
        query = select(TrainingDataset).order_by(TrainingDataset.created_at.desc())

        if job_id:
            query = query.where(TrainingDataset.source_job_id == job_id)

        result = await self.db.execute(query)
        datasets = result.scalars().all()

        responses = [
            TrainingDatasetResponse(
                id=d.id,
                job_id=d.source_job_id,
                name=d.name,
                status=d.status,
                progress=d.progress,
                total_frames=d.total_frames,
                total_annotations=d.total_annotations,
                train_count=d.train_count,
                val_count=d.val_count,
                test_count=d.test_count,
                created_at=d.created_at,
            )
            for d in datasets
        ]

        return TrainingDatasetListResponse(
            datasets=responses,
            total=len(responses),
        )

    async def update_progress(
        self,
        dataset_id: UUID,
        progress: float,
        status: str | None = None,
        **kwargs,
    ) -> None:
        """Update training dataset progress and optionally other fields."""
        result = await self.db.execute(
            select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            return

        dataset.progress = progress
        if status:
            dataset.status = status
        for key, value in kwargs.items():
            if hasattr(dataset, key):
                setattr(dataset, key, value)

        await self.db.commit()

    async def mark_complete(
        self,
        dataset_id: UUID,
        total_frames: int,
        total_annotations: int,
        train_count: int,
        val_count: int,
        test_count: int,
        output_directory: str,
        kitti_path: str | None,
        coco_path: str | None,
        file_size_bytes: int,
    ) -> None:
        """Mark training dataset as complete with final statistics."""
        result = await self.db.execute(
            select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            return

        dataset.status = "complete"
        dataset.progress = 100.0
        dataset.total_frames = total_frames
        dataset.total_annotations = total_annotations
        dataset.train_count = train_count
        dataset.val_count = val_count
        dataset.test_count = test_count
        dataset.output_directory = output_directory
        dataset.kitti_path = kitti_path
        dataset.coco_path = coco_path
        dataset.file_size_bytes = file_size_bytes
        dataset.completed_at = datetime.now(timezone.utc)

        await self.db.commit()

    async def mark_failed(self, dataset_id: UUID, error_message: str) -> None:
        """Mark training dataset as failed."""
        result = await self.db.execute(
            select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            return

        dataset.status = "failed"
        dataset.error_message = error_message

        await self.db.commit()

    async def add_frame_mapping(
        self,
        training_dataset_id: UUID,
        source_frame_id: str,
        source_job_id: UUID,
        split: str,
        output_index: int,
        annotation_count: int,
        included_annotation_ids: list[str],
    ) -> None:
        """Add a frame mapping to the training dataset for lineage tracking."""
        frame = TrainingDatasetFrame(
            training_dataset_id=training_dataset_id,
            source_frame_id=source_frame_id,
            source_job_id=source_job_id,
            split=split,
            output_index=output_index,
            annotation_count=annotation_count,
            included_annotation_ids=included_annotation_ids,
        )
        self.db.add(frame)
        # Don't commit here - caller will batch and commit
