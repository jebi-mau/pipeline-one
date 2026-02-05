"""Job management service."""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.constants import DEFAULT_PIPELINE_STAGES
from backend.app.models.job import JobConfig, ProcessingJob
from backend.app.schemas.job import (
    JobConfig as JobConfigSchema,
)
from backend.app.schemas.job import (
    JobCreate,
    JobResponse,
    JobResultsResponse,
    JobStatistics,
    JobStatusUpdate,
    StageETA,
)
from worker.tasks.orchestrator import run_pipeline

logger = logging.getLogger(__name__)

# Disk space thresholds (in bytes)
DISK_SPACE_ERROR_THRESHOLD = 10 * 1024 * 1024 * 1024  # 10 GB - block job creation
DISK_SPACE_WARNING_THRESHOLD = 50 * 1024 * 1024 * 1024  # 50 GB - warn but allow


class DiskSpaceError(Exception):
    """Raised when there is insufficient disk space to create a job."""

    def __init__(self, available_gb: float, required_gb: float = 10.0):
        self.available_gb = available_gb
        self.required_gb = required_gb
        super().__init__(
            f"Insufficient disk space: {available_gb:.1f} GB available, "
            f"need at least {required_gb:.1f} GB"
        )


def check_disk_space(path: Path) -> tuple[int, int, int]:
    """
    Check disk space at the given path.

    Returns:
        Tuple of (total_bytes, used_bytes, free_bytes)
    """
    usage = shutil.disk_usage(path)
    return usage.total, usage.used, usage.free


def get_disk_space_warning(path: Path) -> str | None:
    """
    Check if disk space is low and return a warning message if so.

    Returns:
        Warning message if space is low, None otherwise.

    Raises:
        DiskSpaceError: If disk space is critically low (< 10 GB)
    """
    _, _, free = check_disk_space(path)
    free_gb = free / (1024 ** 3)

    if free < DISK_SPACE_ERROR_THRESHOLD:
        raise DiskSpaceError(free_gb)

    if free < DISK_SPACE_WARNING_THRESHOLD:
        return f"Low disk space warning: only {free_gb:.1f} GB available"

    return None


class JobService:
    """Service for managing processing jobs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(self, job_data: JobCreate) -> JobResponse:
        """Create a new processing job."""
        from uuid import UUID as UUIDType

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
            enable_diversity_filter=job_data.config.enable_diversity_filter,
            diversity_similarity_threshold=job_data.config.diversity_similarity_threshold,
            diversity_motion_threshold=job_data.config.diversity_motion_threshold,
        )
        self.db.add(config)
        await self.db.flush()

        # Get stages to run from config (default to all stages)
        stages_to_run = job_data.config.stages_to_run or [
            *DEFAULT_PIPELINE_STAGES
        ]

        # Parse dataset_id if provided
        dataset_id = None
        if job_data.dataset_id:
            dataset_id = UUIDType(job_data.dataset_id)

        # Get input paths - either from direct input or from dataset files
        input_paths = job_data.input_paths
        if not input_paths and dataset_id:
            # Get paths from dataset files
            from backend.app.models.dataset import DatasetFile

            result = await self.db.execute(
                select(DatasetFile)
                .where(DatasetFile.dataset_id == dataset_id)
                .where(DatasetFile.status == "copied")
            )
            dataset_files = result.scalars().all()
            input_paths = [
                f.renamed_path or f.original_path for f in dataset_files
            ]

        # Create job
        job = ProcessingJob(
            name=job_data.name,
            input_paths=input_paths,
            output_directory=job_data.output_directory,
            config_id=config.id,
            stages_to_run=stages_to_run,
            dataset_id=dataset_id,
        )
        self.db.add(job)
        await self.db.flush()

        logger.info(f"Created job {job.id}: {job.name} with stages {stages_to_run}")
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
        count_query = select(func.count(ProcessingJob.id))

        if status:
            query = query.where(ProcessingJob.status == status)
            count_query = count_query.where(ProcessingJob.status == status)

        # Get total count using scalar count (efficient)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

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
        job.started_at = datetime.now(timezone.utc)
        job.current_stage = 1  # extraction stage

        await self.db.commit()

        # Build object classes from config
        object_classes = [
            {"class_id": cls, "class_name": cls.replace("_", " ").title(), "text": cls}
            for cls in config.object_class_ids
        ]

        # Build pipeline config
        pipeline_config = {
            "extraction": {
                "frame_skip": config.frame_skip,
                # Lineage context for enhanced naming (when dataset is linked)
                "dataset_id": str(job.dataset_id) if job.dataset_id else None,
                "use_enhanced_naming": job.dataset_id is not None,
                # Diversity filter settings
                "enable_diversity_filter": config.enable_diversity_filter,
                "diversity_similarity_threshold": config.diversity_similarity_threshold,
                "diversity_motion_threshold": config.diversity_motion_threshold,
            },
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

        # Get stages to run from job
        stages_to_run = job.stages_to_run or [
            *DEFAULT_PIPELINE_STAGES
        ]

        # Build dataset_file_mapping for lineage tracking if job is linked to dataset
        dataset_file_mapping = None
        if job.dataset_id:
            from backend.app.models.dataset import DatasetFile

            result = await self.db.execute(
                select(DatasetFile)
                .where(DatasetFile.dataset_id == job.dataset_id)
                .where(DatasetFile.status == "copied")
            )
            dataset_files = result.scalars().all()
            dataset_file_mapping = {
                (f.renamed_path or f.original_path): str(f.id)
                for f in dataset_files
            }
            logger.info(f"Built dataset_file_mapping with {len(dataset_file_mapping)} files")

        # Trigger Celery pipeline task
        run_pipeline.delay(
            str(job_id),
            job.input_paths,
            object_classes,
            pipeline_config,
            stages_to_run,
            dataset_file_mapping,
        )

        logger.info(f"Started job {job_id} with stages {stages_to_run} - dispatched to Celery")
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
        await self.db.commit()

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
        await self.db.commit()

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
        job.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

        logger.info(f"Cancelled job {job_id}")
        return JobStatusUpdate(id=job_id, status="cancelled", message="Job cancelled")

    async def restart_job(self, job_id: UUID) -> JobStatusUpdate | None:
        """Restart a failed or cancelled job."""
        result = await self.db.execute(
            select(ProcessingJob, JobConfig)
            .join(JobConfig)
            .where(ProcessingJob.id == job_id)
        )
        row = result.first()
        if row is None:
            return None

        job, config = row[0], row[1]

        if job.status not in ("failed", "cancelled"):
            return JobStatusUpdate(
                id=job_id,
                status=job.status,
                message=f"Cannot restart job in {job.status} status",
            )

        # Reset job state
        job.status = "running"
        job.current_stage = 1
        job.progress = 0.0
        job.processed_frames = 0
        job.error_message = None
        job.error_stage = None
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = None

        await self.db.commit()

        # Build object classes from config
        object_classes = [
            {"class_id": cls, "class_name": cls.replace("_", " ").title(), "text": cls}
            for cls in config.object_class_ids
        ]

        # Build pipeline config
        pipeline_config = {
            "extraction": {
                "frame_skip": config.frame_skip,
                # Lineage context for enhanced naming (when dataset is linked)
                "dataset_id": str(job.dataset_id) if job.dataset_id else None,
                "use_enhanced_naming": job.dataset_id is not None,
                # Diversity filter settings
                "enable_diversity_filter": config.enable_diversity_filter,
                "diversity_similarity_threshold": config.diversity_similarity_threshold,
                "diversity_motion_threshold": config.diversity_motion_threshold,
            },
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

        # Get stages to run from job
        stages_to_run = job.stages_to_run or [
            *DEFAULT_PIPELINE_STAGES
        ]

        # Build dataset_file_mapping for lineage tracking if job is linked to dataset
        dataset_file_mapping = None
        if job.dataset_id:
            from backend.app.models.dataset import DatasetFile

            result = await self.db.execute(
                select(DatasetFile)
                .where(DatasetFile.dataset_id == job.dataset_id)
                .where(DatasetFile.status == "copied")
            )
            dataset_files = result.scalars().all()
            dataset_file_mapping = {
                (f.renamed_path or f.original_path): str(f.id)
                for f in dataset_files
            }

        # Trigger Celery pipeline task
        run_pipeline.delay(
            str(job_id),
            job.input_paths,
            object_classes,
            pipeline_config,
            stages_to_run,
            dataset_file_mapping,
        )

        logger.info(f"Restarted job {job_id} with stages {stages_to_run}")
        return JobStatusUpdate(id=job_id, status="running", message="Job restarted")

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
        """Delete a job and its associated data, including output files."""
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return False

        # Delete output directory if it exists
        settings = get_settings()
        output_dir = Path(settings.output_directory) / str(job_id)
        if output_dir.exists():
            try:
                shutil.rmtree(output_dir)
                logger.info(f"Deleted output directory for job {job_id}: {output_dir}")
            except Exception as e:
                logger.error(f"Failed to delete output directory for job {job_id}: {e}")
                # Continue with database deletion even if filesystem cleanup fails

        await self.db.delete(job)
        await self.db.commit()
        logger.info(f"Deleted job {job_id}")
        return True

    def _calculate_eta(
        self, job: ProcessingJob
    ) -> tuple[int | None, list[StageETA], float | None]:
        """
        Calculate ETA and per-stage breakdown using linear extrapolation.

        Returns:
            (total_eta_seconds, stage_etas, frames_per_second)
        """
        # Stage weights from orchestrator.py
        STAGE_WEIGHTS = {
            "extraction": 0.25,
            "segmentation": 0.50,
            "reconstruction": 0.15,
            "tracking": 0.10,
        }
        STAGE_NUMBERS = {
            "extraction": 1,
            "segmentation": 2,
            "reconstruction": 3,
            "tracking": 4,
        }
        # Default FPS benchmarks by stage and model variant
        # These are used for early estimates before real-time data is available
        DEFAULT_FPS = {
            "extraction": 30.0,  # Relatively constant for all models
            "segmentation": {
                "sam3_hiera_tiny": 2.5,
                "sam3_hiera_small": 1.5,
                "sam3_hiera_large": 0.5,
                "default": 1.0,
            },
            "reconstruction": 50.0,  # Fast GPU-based depth processing
            "tracking": 100.0,  # Very fast association step
        }

        stages_to_run = job.stages_to_run or DEFAULT_PIPELINE_STAGES
        stage_etas: list[StageETA] = []
        total_eta_seconds: int | None = None
        frames_per_second = getattr(job, 'frames_per_second', None)

        # Get model variant for segmentation FPS lookup
        model_variant = "default"
        if hasattr(job, 'config') and job.config:
            model_variant = job.config.sam3_model_variant or "default"

        def get_default_fps(stage_name: str) -> float:
            """Get default FPS for a stage."""
            fps = DEFAULT_FPS.get(stage_name, 1.0)
            if isinstance(fps, dict):
                return fps.get(model_variant, fps.get("default", 1.0))
            return fps

        now = datetime.now(timezone.utc)

        # For completed jobs, show elapsed times
        if job.status == "completed":
            _total_elapsed = (
                int((job.completed_at - job.started_at).total_seconds())
                if job.completed_at and job.started_at
                else None
            )
            for stage_name in stages_to_run:
                stage_etas.append(StageETA(
                    stage=stage_name,
                    stage_number=STAGE_NUMBERS.get(stage_name, 0),
                    status="completed",
                    eta_seconds=None,
                    elapsed_seconds=None,  # Individual stage timing not tracked
                ))
            return None, stage_etas, frames_per_second

        # For non-running jobs, no ETA
        if job.status != "running":
            for stage_name in stages_to_run:
                stage_etas.append(StageETA(
                    stage=stage_name,
                    stage_number=STAGE_NUMBERS.get(stage_name, 0),
                    status="pending",
                    eta_seconds=None,
                    elapsed_seconds=None,
                ))
            return None, stage_etas, frames_per_second

        # Running job - calculate ETA
        current_stage_name = job.current_stage_name
        stage_started_at = getattr(job, 'stage_started_at', None)

        # Use started_at as fallback for stage 1 if stage_started_at not set
        if stage_started_at is None and job.started_at and job.current_stage == 1:
            stage_started_at = job.started_at

        # Calculate current stage elapsed time
        current_elapsed_seconds = (
            int((now - stage_started_at).total_seconds())
            if stage_started_at
            else None
        )

        # Calculate actual FPS from elapsed time and processed frames
        actual_fps = None
        if current_elapsed_seconds and current_elapsed_seconds > 0 and job.processed_frames:
            actual_fps = job.processed_frames / current_elapsed_seconds
            # Update frames_per_second for response
            frames_per_second = round(actual_fps, 2)

        # Calculate rate and ETA if we have data
        current_stage_eta = None
        use_default_estimate = False

        if actual_fps and actual_fps > 0 and job.total_frames and job.processed_frames is not None:
            # Use real-time FPS for accurate estimate
            remaining_frames = job.total_frames - job.processed_frames
            current_stage_eta = int(remaining_frames / actual_fps)
        elif (
            frames_per_second
            and frames_per_second > 0
            and job.total_frames
            and job.processed_frames is not None
        ):
            # Use stored FPS if actual calculation not possible
            remaining_frames = job.total_frames - job.processed_frames
            current_stage_eta = int(remaining_frames / frames_per_second)
        elif job.total_frames and job.total_frames > 0:
            # Fallback to default benchmarks for early estimate
            use_default_estimate = True
            default_fps = get_default_fps(current_stage_name or "extraction")
            processed = job.processed_frames or 0
            remaining_frames = job.total_frames - processed
            current_stage_eta = int(remaining_frames / default_fps)

        # Determine which stage index we're on
        current_stage_idx = (
            stages_to_run.index(current_stage_name)
            if current_stage_name in stages_to_run
            else 0
        )

        # Calculate remaining stages ETA based on weights or default benchmarks
        remaining_stages_eta = 0
        total_frames = job.total_frames or job.processed_frames or 0

        if current_elapsed_seconds and current_elapsed_seconds > 0 and job.processed_frames:
            # Use actual rate for estimation
            time_per_frame = current_elapsed_seconds / job.processed_frames

            # Estimate remaining stages using weight ratios
            for i, stage_name in enumerate(stages_to_run):
                if i > current_stage_idx:
                    weight_ratio = (
                        STAGE_WEIGHTS.get(stage_name, 0.25)
                        / STAGE_WEIGHTS.get(current_stage_name, 0.25)
                    )
                    stage_eta = int(time_per_frame * total_frames * weight_ratio)
                    remaining_stages_eta += stage_eta
        elif use_default_estimate and total_frames > 0:
            # Use default benchmarks for remaining stages
            for i, stage_name in enumerate(stages_to_run):
                if i > current_stage_idx:
                    default_fps = get_default_fps(stage_name)
                    stage_eta = int(total_frames / default_fps)
                    remaining_stages_eta += stage_eta

        # Build stage ETAs
        for i, stage_name in enumerate(stages_to_run):
            stage_num = STAGE_NUMBERS.get(stage_name, i + 1)

            if i < current_stage_idx:
                # Completed stage
                stage_etas.append(StageETA(
                    stage=stage_name,
                    stage_number=stage_num,
                    status="completed",
                    eta_seconds=None,
                    elapsed_seconds=None,
                ))
            elif i == current_stage_idx:
                # Current stage
                stage_etas.append(StageETA(
                    stage=stage_name,
                    stage_number=stage_num,
                    status="running",
                    eta_seconds=current_stage_eta,
                    elapsed_seconds=current_elapsed_seconds,
                ))
            else:
                # Future stage - estimate based on weight ratio or default benchmarks
                stage_eta = None
                if current_elapsed_seconds and current_elapsed_seconds > 0 and job.processed_frames:
                    time_per_frame = current_elapsed_seconds / job.processed_frames
                    weight_ratio = (
                        STAGE_WEIGHTS.get(stage_name, 0.25)
                        / STAGE_WEIGHTS.get(current_stage_name, 0.25)
                    )
                    stage_eta = int(time_per_frame * total_frames * weight_ratio)
                elif use_default_estimate and total_frames > 0:
                    # Use default FPS for this stage
                    default_fps = get_default_fps(stage_name)
                    stage_eta = int(total_frames / default_fps)

                stage_etas.append(StageETA(
                    stage=stage_name,
                    stage_number=stage_num,
                    status="pending",
                    eta_seconds=stage_eta,
                    elapsed_seconds=None,
                ))

        # Total ETA = current stage remaining + remaining stages
        if current_stage_eta is not None:
            total_eta_seconds = current_stage_eta + remaining_stages_eta
        elif remaining_stages_eta > 0:
            total_eta_seconds = remaining_stages_eta

        return total_eta_seconds, stage_etas, frames_per_second

    def _to_response(self, job: ProcessingJob, config: JobConfig) -> JobResponse:
        """Convert job model to response schema."""
        # Get stages_to_run with default fallback
        stages_to_run = job.stages_to_run or [
            *DEFAULT_PIPELINE_STAGES
        ]

        # Calculate ETA and stage breakdowns
        eta_seconds, stage_etas, frames_per_second = self._calculate_eta(job)

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
            total_detections=job.total_detections,
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
                stages_to_run=stages_to_run,
                enable_diversity_filter=config.enable_diversity_filter,
                diversity_similarity_threshold=config.diversity_similarity_threshold,
                diversity_motion_threshold=config.diversity_motion_threshold,
            ),
            stages_to_run=stages_to_run,
            dataset_id=job.dataset_id,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            eta_seconds=eta_seconds,
            stage_etas=stage_etas,
            frames_per_second=frames_per_second,
        )
