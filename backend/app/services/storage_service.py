"""Storage management service for tracking and estimating disk usage."""

import logging
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.dataset import Dataset
from backend.app.models.job import ProcessingJob
from backend.app.models.training_dataset import TrainingDataset

logger = logging.getLogger(__name__)

# Storage estimation constants (bytes per frame)
STORAGE_PER_FRAME_POINT_CLOUD = 10 * 1024 * 1024  # ~10 MB
STORAGE_PER_FRAME_LEFT_IMAGE = 3 * 1024 * 1024  # ~3 MB (PNG)
STORAGE_PER_FRAME_RIGHT_IMAGE = 3 * 1024 * 1024  # ~3 MB (PNG)
STORAGE_PER_FRAME_DEPTH = 2.5 * 1024 * 1024  # ~2.5 MB
STORAGE_PER_FRAME_MASKS = 5 * 1024 * 1024  # ~5 MB (all detections)
STORAGE_PER_FRAME_METADATA = 0.5 * 1024 * 1024  # ~0.5 MB (JSON, etc.)

# Storage thresholds
DISK_SPACE_CRITICAL_THRESHOLD = 20 * 1024 * 1024 * 1024  # 20 GB
DISK_SPACE_WARNING_THRESHOLD = 100 * 1024 * 1024 * 1024  # 100 GB


def format_bytes(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_directory_size(path: Path) -> int:
    """Calculate total size of a directory recursively."""
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


class StorageService:
    """Service for storage management and estimation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # ==================== Size Calculation ====================

    async def get_job_storage_size(self, job_id: UUID) -> int:
        """Calculate the storage size of a job's output directory."""
        result = await self.db.execute(
            select(ProcessingJob.output_directory).where(ProcessingJob.id == job_id)
        )
        row = result.scalar_one_or_none()

        if not row:
            return 0

        output_dir = Path(row)
        return get_directory_size(output_dir)

    async def update_job_storage_size(self, job_id: UUID) -> int:
        """Calculate and store the storage size for a job."""
        size = await self.get_job_storage_size(job_id)

        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if job:
            job.storage_size_bytes = size
            await self.db.commit()
            logger.info(f"Updated storage size for job {job_id}: {format_bytes(size)}")

        return size

    async def get_dataset_output_size(self, dataset_id: UUID) -> int:
        """Calculate the output storage size of a dataset."""
        result = await self.db.execute(
            select(Dataset.output_directory).where(Dataset.id == dataset_id)
        )
        row = result.scalar_one_or_none()

        if not row:
            return 0

        output_dir = Path(row)
        return get_directory_size(output_dir)

    async def update_dataset_output_size(self, dataset_id: UUID) -> int:
        """Calculate and store the output storage size for a dataset."""
        size = await self.get_dataset_output_size(dataset_id)

        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()

        if dataset:
            dataset.output_size_bytes = size
            await self.db.commit()
            logger.info(f"Updated output size for dataset {dataset_id}: {format_bytes(size)}")

        return size

    # ==================== Storage Estimation ====================

    @staticmethod
    def estimate_job_storage(
        total_frames: int,
        stages: list[str] | None = None,
        extract_point_clouds: bool = True,
        extract_right_image: bool = True,
        extract_masks: bool = True,
        image_format: str = "png",
        frame_skip: int = 1,
    ) -> int:
        """
        Estimate the storage required for a job based on configuration.

        Args:
            total_frames: Total number of frames in input files
            stages: Pipeline stages to run
            extract_point_clouds: Whether point clouds will be extracted
            extract_right_image: Whether right camera images will be extracted
            extract_masks: Whether segmentation masks will be saved
            image_format: Image format ("png" or "jpg")
            frame_skip: Frame skip setting (process every Nth frame)

        Returns:
            Estimated storage in bytes
        """
        if stages is None:
            stages = ["extraction", "segmentation", "reconstruction", "tracking"]

        # Calculate actual frames to process
        processed_frames = total_frames // frame_skip if frame_skip > 0 else total_frames

        # Base storage (always needed)
        storage = 0

        # Extraction stage outputs
        if "extraction" in stages:
            # Left image (always extracted)
            image_multiplier = 0.6 if image_format == "jpg" else 1.0
            storage += processed_frames * STORAGE_PER_FRAME_LEFT_IMAGE * image_multiplier

            # Right image (optional)
            if extract_right_image:
                storage += processed_frames * STORAGE_PER_FRAME_RIGHT_IMAGE * image_multiplier

            # Depth maps (always with extraction)
            storage += processed_frames * STORAGE_PER_FRAME_DEPTH

            # Point clouds (optional, largest contributor)
            if extract_point_clouds:
                storage += processed_frames * STORAGE_PER_FRAME_POINT_CLOUD

            # Metadata
            storage += processed_frames * STORAGE_PER_FRAME_METADATA

        # Segmentation stage outputs
        if "segmentation" in stages:
            if extract_masks:
                storage += processed_frames * STORAGE_PER_FRAME_MASKS

        # Reconstruction and tracking add minimal storage (label files, JSON)
        if "reconstruction" in stages or "tracking" in stages:
            storage += processed_frames * 0.1 * 1024 * 1024  # ~0.1 MB per frame

        return int(storage)

    async def check_storage_for_job(
        self,
        total_frames: int,
        stages: list[str] | None = None,
        extract_point_clouds: bool = True,
        extract_right_image: bool = True,
        extract_masks: bool = True,
        image_format: str = "png",
        frame_skip: int = 1,
    ) -> dict:
        """
        Check if there's sufficient storage for a job and return estimation details.

        Returns:
            Dict with estimation details and warnings
        """
        estimated_bytes = self.estimate_job_storage(
            total_frames=total_frames,
            stages=stages,
            extract_point_clouds=extract_point_clouds,
            extract_right_image=extract_right_image,
            extract_masks=extract_masks,
            image_format=image_format,
            frame_skip=frame_skip,
        )

        # Get available disk space
        output_dir = Path(self.settings.output_directory)
        usage = shutil.disk_usage(output_dir)
        available_bytes = usage.free

        # Determine if there's sufficient space
        sufficient_space = available_bytes > estimated_bytes

        # Generate warning/error
        warning = None
        if available_bytes < DISK_SPACE_CRITICAL_THRESHOLD:
            warning = f"Critical: Only {format_bytes(available_bytes)} free. Job creation blocked."
            sufficient_space = False
        elif available_bytes < estimated_bytes + DISK_SPACE_WARNING_THRESHOLD:
            warning = f"Warning: Estimated job size ({format_bytes(estimated_bytes)}) may exceed available space."
        elif available_bytes < DISK_SPACE_WARNING_THRESHOLD:
            warning = f"Low disk space: {format_bytes(available_bytes)} available."

        return {
            "estimated_bytes": estimated_bytes,
            "estimated_formatted": format_bytes(estimated_bytes),
            "available_bytes": available_bytes,
            "available_formatted": format_bytes(available_bytes),
            "sufficient_space": sufficient_space,
            "warning": warning,
            "details": {
                "frames_to_process": total_frames // (frame_skip or 1),
                "stages": stages or ["extraction", "segmentation", "reconstruction", "tracking"],
                "extract_point_clouds": extract_point_clouds,
                "extract_right_image": extract_right_image,
                "extract_masks": extract_masks,
            }
        }

    # ==================== Storage Summary ====================

    async def get_storage_summary(self) -> dict:
        """Get comprehensive storage breakdown by entity type."""
        output_dir = Path(self.settings.output_directory)

        # Get disk usage
        usage = shutil.disk_usage(output_dir)

        # Get total jobs storage from database
        result = await self.db.execute(
            select(func.coalesce(func.sum(ProcessingJob.storage_size_bytes), 0))
        )
        total_jobs_storage = result.scalar() or 0

        # Get total datasets output storage
        result = await self.db.execute(
            select(func.coalesce(func.sum(Dataset.output_size_bytes), 0))
        )
        total_datasets_storage = result.scalar() or 0

        # Get total training datasets storage
        result = await self.db.execute(
            select(func.coalesce(func.sum(TrainingDataset.file_size_bytes), 0))
        )
        total_training_datasets_storage = result.scalar() or 0

        # Calculate other storage (not tracked in entities)
        _tracked_storage = total_jobs_storage + total_datasets_storage + total_training_datasets_storage

        # Determine warning level
        free_gb = usage.free / (1024 ** 3)
        warning = None
        warning_level = "normal"
        if free_gb < 20:
            warning = f"Critical: Only {free_gb:.1f} GB free"
            warning_level = "critical"
        elif free_gb < 100:
            warning = f"Low disk space: {free_gb:.1f} GB free"
            warning_level = "warning"

        return {
            "disk_total_bytes": usage.total,
            "disk_used_bytes": usage.used,
            "disk_free_bytes": usage.free,
            "disk_total_formatted": format_bytes(usage.total),
            "disk_used_formatted": format_bytes(usage.used),
            "disk_free_formatted": format_bytes(usage.free),
            "disk_usage_percent": round((usage.used / usage.total) * 100, 1),
            "total_jobs_storage_bytes": total_jobs_storage,
            "total_jobs_storage_formatted": format_bytes(total_jobs_storage),
            "total_datasets_storage_bytes": total_datasets_storage,
            "total_datasets_storage_formatted": format_bytes(total_datasets_storage),
            "total_training_datasets_bytes": total_training_datasets_storage,
            "total_training_datasets_formatted": format_bytes(total_training_datasets_storage),
            "warning": warning,
            "warning_level": warning_level,
        }

    # ==================== Backfill ====================

    async def backfill_job_sizes(self, dry_run: bool = True) -> dict:
        """
        Backfill storage_size_bytes for all jobs with output directories.

        Args:
            dry_run: If True, only calculate sizes without updating database

        Returns:
            Summary of backfill operation
        """
        result = await self.db.execute(
            select(ProcessingJob).where(
                ProcessingJob.output_directory.isnot(None),
                ProcessingJob.storage_size_bytes.is_(None)
            )
        )
        jobs = result.scalars().all()

        updated = 0
        total_size = 0
        errors = []

        for job in jobs:
            try:
                output_dir = Path(job.output_directory)
                if output_dir.exists():
                    size = get_directory_size(output_dir)
                    total_size += size

                    if not dry_run:
                        job.storage_size_bytes = size
                        updated += 1

                    logger.info(f"Job {job.id}: {format_bytes(size)}")
            except Exception as e:
                errors.append(f"Job {job.id}: {str(e)}")
                logger.error(f"Error calculating size for job {job.id}: {e}")

        if not dry_run:
            await self.db.commit()

        return {
            "jobs_found": len(jobs),
            "jobs_updated": updated if not dry_run else 0,
            "total_size_bytes": total_size,
            "total_size_formatted": format_bytes(total_size),
            "dry_run": dry_run,
            "errors": errors,
        }

    async def backfill_dataset_sizes(self, dry_run: bool = True) -> dict:
        """
        Backfill output_size_bytes for all datasets with output directories.

        Args:
            dry_run: If True, only calculate sizes without updating database

        Returns:
            Summary of backfill operation
        """
        result = await self.db.execute(
            select(Dataset).where(
                Dataset.output_directory.isnot(None),
                Dataset.output_size_bytes.is_(None)
            )
        )
        datasets = result.scalars().all()

        updated = 0
        total_size = 0
        errors = []

        for dataset in datasets:
            try:
                output_dir = Path(dataset.output_directory)
                if output_dir.exists():
                    size = get_directory_size(output_dir)
                    total_size += size

                    if not dry_run:
                        dataset.output_size_bytes = size
                        updated += 1

                    logger.info(f"Dataset {dataset.id}: {format_bytes(size)}")
            except Exception as e:
                errors.append(f"Dataset {dataset.id}: {str(e)}")
                logger.error(f"Error calculating size for dataset {dataset.id}: {e}")

        if not dry_run:
            await self.db.commit()

        return {
            "datasets_found": len(datasets),
            "datasets_updated": updated if not dry_run else 0,
            "total_size_bytes": total_size,
            "total_size_formatted": format_bytes(total_size),
            "dry_run": dry_run,
            "errors": errors,
        }
