"""Job management service."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.job import JobConfig, ProcessingJob
from worker.tasks.orchestrator import run_pipeline
from backend.app.schemas.job import (
    JobConfig as JobConfigSchema,
    JobCreate,
    JobResponse,
    JobResultsResponse,
    JobStatistics,
    JobStatusUpdate,
)

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing processing jobs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(self, job_data: JobCreate) -> JobResponse:
        """Create a new processing job."""
        # Create job config
        config = JobConfig(
            name=job_data.name,
            sam3_model_variant=job_data.config.sam3_model_variant,
            sam3_confidence_threshold=job_data.config.sam3_confidence_threshold,
            sam3_iou_threshold=job_data.config.sam3_iou_threshold,
            sam3_batch_size=job_data.config.sam3_batch_size,
            frame_skip=job_data.config.frame_skip,
            enable_tracking=job_data.config.enable_tracking,
            export_3d_data=job_data.config.export_3d_data,
            object_class_ids=job_data.config.object_class_ids,
        )
        self.db.add(config)
        await self.db.flush()

        # Create job
        job = ProcessingJob(
            name=job_data.name,
            input_paths=job_data.input_paths,
            output_directory=job_data.output_directory,
            config_id=config.id,
        )
        self.db.add(job)
        await self.db.flush()

        logger.info(f"Created job {job.id}: {job.name}")
        return self._to_response(job, config)

    async def get_job(self, job_id: UUID) -> JobResponse | None:
        """Get job by ID."""
        result = await self.db.execute(
            select(ProcessingJob, JobConfig)
            .join(JobConfig)
            .where(ProcessingJob.id == job_id)
        )
        row = result.first()
        if row is None:
            return None
        return self._to_response(row[0], row[1])

    async def list_jobs(
        self, status: str | None = None, limit: int = 20, offset: int = 0
    ) -> tuple[list[JobResponse], int]:
        """List jobs with optional filtering."""
        query = select(ProcessingJob, JobConfig).join(JobConfig)
        count_query = select(ProcessingJob)

        if status:
            query = query.where(ProcessingJob.status == status)
            count_query = count_query.where(ProcessingJob.status == status)

        # Get total count
        count_result = await self.db.execute(count_query)
        total = len(count_result.all())

        # Get paginated results
        query = query.order_by(ProcessingJob.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)

        jobs = [self._to_response(row[0], row[1]) for row in result.all()]
        return jobs, total

    async def start_job(self, job_id: UUID) -> JobStatusUpdate | None:
        """Start a pending job."""
        result = await self.db.execute(
            select(ProcessingJob, JobConfig)
            .join(JobConfig)
            .where(ProcessingJob.id == job_id)
        )
        row = result.first()
        if row is None:
            return None

        job, config = row[0], row[1]

        if job.status != "pending":
            return JobStatusUpdate(
                id=job_id,
                status=job.status,
                message=f"Cannot start job in {job.status} status",
            )

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.current_stage = 1  # extraction stage

        await self.db.commit()

        # Build object classes from config
        object_classes = [
            {"class_id": cls, "class_name": cls.replace("_", " ").title(), "text": cls}
            for cls in config.object_class_ids
        ]

        # Build pipeline config
        pipeline_config = {
            "extraction": {"frame_skip": config.frame_skip},
            "sam3": {
                "model_variant": config.sam3_model_variant,
                "confidence_threshold": config.sam3_confidence_threshold,
                "iou_threshold": config.sam3_iou_threshold,
                "batch_size": config.sam3_batch_size,
            },
            "reconstruction": {"enabled": config.export_3d_data},
            "tracking": {"enabled": config.enable_tracking},
            "output_directory": job.output_directory,
        }

        # Trigger Celery pipeline task
        run_pipeline.delay(
            str(job_id),
            job.input_paths,
            object_classes,
            pipeline_config,
        )

        logger.info(f"Started job {job_id} - dispatched to Celery")
        return JobStatusUpdate(id=job_id, status="running", message="Job started")

    async def pause_job(self, job_id: UUID) -> JobStatusUpdate | None:
        """Pause a running job."""
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None

        if job.status != "running":
            return JobStatusUpdate(
                id=job_id,
                status=job.status,
                message=f"Cannot pause job in {job.status} status",
            )

        job.status = "paused"

        logger.info(f"Paused job {job_id}")
        return JobStatusUpdate(id=job_id, status="paused", message="Job paused")

    async def resume_job(self, job_id: UUID) -> JobStatusUpdate | None:
        """Resume a paused job."""
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None

        if job.status != "paused":
            return JobStatusUpdate(
                id=job_id,
                status=job.status,
                message=f"Cannot resume job in {job.status} status",
            )

        job.status = "running"

        logger.info(f"Resumed job {job_id}")
        return JobStatusUpdate(id=job_id, status="running", message="Job resumed")

    async def cancel_job(self, job_id: UUID) -> JobStatusUpdate | None:
        """Cancel a running or paused job."""
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None

        if job.status not in ("running", "paused", "pending"):
            return JobStatusUpdate(
                id=job_id,
                status=job.status,
                message=f"Cannot cancel job in {job.status} status",
            )

        job.status = "cancelled"
        job.completed_at = datetime.utcnow()

        logger.info(f"Cancelled job {job_id}")
        return JobStatusUpdate(id=job_id, status="cancelled", message="Job cancelled")

    async def get_job_results(self, job_id: UUID) -> JobResultsResponse | None:
        """Get results for a completed job."""
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None or job.status != "completed":
            return None

        return JobResultsResponse(
            job_id=job.id,
            status=job.status,
            statistics=JobStatistics(
                total_frames=job.total_frames or 0,
                total_detections=job.total_detections or 0,
                detections_by_class={},  # TODO: Compute from annotations
                total_tracks=0,  # TODO: Count tracks
                processing_time_seconds=(
                    (job.completed_at - job.started_at).total_seconds()
                    if job.completed_at and job.started_at
                    else 0
                ),
            ),
            output_directory=job.output_directory or "",
            available_exports=["kitti", "coco", "json"],
        )

    async def delete_job(self, job_id: UUID) -> bool:
        """Delete a job and its associated data."""
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return False

        await self.db.delete(job)
        logger.info(f"Deleted job {job_id}")
        return True

    def _to_response(self, job: ProcessingJob, config: JobConfig) -> JobResponse:
        """Convert job model to response schema."""
        return JobResponse(
            id=job.id,
            name=job.name,
            status=job.status,
            current_stage=job.current_stage,
            current_stage_name=job.current_stage_name,
            progress=job.progress,
            stage_progress=0.0,
            total_frames=job.total_frames,
            processed_frames=job.processed_frames,
            input_paths=job.input_paths,
            output_directory=job.output_directory,
            config=JobConfigSchema(
                object_class_ids=config.object_class_ids,
                sam3_model_variant=config.sam3_model_variant,
                sam3_confidence_threshold=config.sam3_confidence_threshold,
                sam3_iou_threshold=config.sam3_iou_threshold,
                sam3_batch_size=config.sam3_batch_size,
                frame_skip=config.frame_skip,
                enable_tracking=config.enable_tracking,
                export_3d_data=config.export_3d_data,
            ),
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
