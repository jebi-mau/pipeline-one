"""Dataset management service."""

import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from backend.app.models.dataset import Dataset, DatasetFile
from backend.app.models.job import ProcessingJob
from backend.app.schemas.dataset import (
    CameraInfo,
    DatasetCamerasResponse,
    DatasetCreate,
    DatasetDetailResponse,
    DatasetFileDetail,
    DatasetFileSummary,
    DatasetPrepareResponse,
    DatasetResponse,
    DatasetScanResponse,
    DatasetUpdate,
    JobStats,
    JobSummary,
)

logger = logging.getLogger(__name__)

# Base output directory for datasets
OUTPUT_BASE = Path(os.getenv("PIPELINE_OUTPUT_DIR", "data/output"))


class DatasetService:
    """Service for managing datasets and their files."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dataset(self, data: DatasetCreate) -> DatasetResponse:
        """Create a new dataset."""
        dataset = Dataset(
            name=data.name,
            description=data.description,
            customer=data.customer,
            site=data.site,
            equipment=data.equipment,
            collection_date=data.collection_date,
            object_types=data.object_types,
            source_folder=data.source_folder,
            output_directory=data.output_directory,
            status="created",
        )
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(f"Created dataset {dataset.id}: {dataset.name}")
        return self._to_response(dataset)

    async def get_dataset(self, dataset_id: UUID) -> DatasetDetailResponse | None:
        """Get dataset by ID with files."""
        result = await self.db.execute(
            select(Dataset)
            .options(selectinload(Dataset.files))
            .where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            return None

        # Count linked jobs
        job_count_result = await self.db.execute(
            select(func.count(ProcessingJob.id))
            .where(ProcessingJob.dataset_id == dataset_id)
        )
        job_count = job_count_result.scalar() or 0

        return self._to_detail_response(dataset, job_count)

    async def _get_job_stats_for_datasets(
        self, dataset_ids: list[UUID]
    ) -> dict[UUID, JobStats]:
        """Fetch job statistics for multiple datasets efficiently."""
        if not dataset_ids:
            return {}

        # Query all jobs for these datasets (with config for object classes)
        result = await self.db.execute(
            select(ProcessingJob)
            .options(joinedload(ProcessingJob.config))
            .where(ProcessingJob.dataset_id.in_(dataset_ids))
            .order_by(ProcessingJob.created_at.desc())
        )
        jobs = result.unique().scalars().all()

        # Group jobs by dataset_id
        stats_by_dataset: dict[UUID, JobStats] = {
            did: JobStats() for did in dataset_ids
        }

        for job in jobs:
            if job.dataset_id is None:
                continue

            stats = stats_by_dataset.get(job.dataset_id)
            if stats is None:
                continue

            # Update counts
            stats.total += 1
            if job.status == "pending":
                stats.pending += 1
            elif job.status == "running":
                stats.running += 1
            elif job.status == "completed":
                stats.completed += 1
            elif job.status == "failed":
                stats.failed += 1

            # Add job summary
            # Get object class IDs from config (UUIDs stored as strings)
            object_class_ids = []
            if job.config and job.config.object_class_ids:
                object_class_ids = [str(oid) for oid in job.config.object_class_ids]

            stats.jobs.append(
                JobSummary(
                    id=job.id,
                    name=job.name,
                    status=job.status,
                    progress=job.progress,
                    current_stage_name=job.current_stage_name,
                    total_frames=job.total_frames,
                    processed_frames=job.processed_frames,
                    object_classes=object_class_ids,
                    created_at=job.created_at,
                    completed_at=job.completed_at,
                    error_message=job.error_message,
                )
            )

        return stats_by_dataset

    async def list_datasets(
        self,
        limit: int = 20,
        offset: int = 0,
        customer: str | None = None,
        site: str | None = None,
        status: str | None = None,
    ) -> tuple[list[DatasetResponse], int]:
        """List datasets with optional filtering."""
        query = select(Dataset)
        count_query = select(func.count(Dataset.id))

        if customer:
            query = query.where(Dataset.customer == customer)
            count_query = count_query.where(Dataset.customer == customer)
        if site:
            query = query.where(Dataset.site == site)
            count_query = count_query.where(Dataset.site == site)
        if status:
            query = query.where(Dataset.status == status)
            count_query = count_query.where(Dataset.status == status)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(Dataset.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        datasets = result.scalars().all()

        # Fetch job stats for all datasets in one query
        dataset_ids = [d.id for d in datasets]
        job_stats = await self._get_job_stats_for_datasets(dataset_ids)

        responses = [
            self._to_response(d, job_stats.get(d.id, JobStats()))
            for d in datasets
        ]
        return responses, total

    async def update_dataset(
        self, dataset_id: UUID, data: DatasetUpdate
    ) -> DatasetResponse | None:
        """Update dataset metadata."""
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            return None

        # Update fields that were provided
        if data.name is not None:
            dataset.name = data.name
        if data.description is not None:
            dataset.description = data.description
        if data.customer is not None:
            dataset.customer = data.customer
        if data.site is not None:
            dataset.site = data.site
        if data.equipment is not None:
            dataset.equipment = data.equipment
        if data.collection_date is not None:
            dataset.collection_date = data.collection_date
        if data.object_types is not None:
            dataset.object_types = data.object_types
        if data.source_folder is not None:
            dataset.source_folder = data.source_folder
            # Reset error when source folder is changed
            dataset.error_message = None
        if data.output_directory is not None:
            dataset.output_directory = data.output_directory
        if data.status is not None:
            dataset.status = data.status
            # Clear error message when status is reset
            if data.status == "created":
                dataset.error_message = None

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(f"Updated dataset {dataset_id}")
        return self._to_response(dataset)

    async def delete_dataset(self, dataset_id: UUID) -> bool:
        """Delete a dataset and its files."""
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            return False

        await self.db.delete(dataset)
        await self.db.commit()

        logger.info(f"Deleted dataset {dataset_id}")
        return True

    async def scan_folder(
        self,
        dataset_id: UUID,
        recursive: bool = True,
        extract_metadata: bool = True,
    ) -> DatasetScanResponse:
        """Scan source folder for SVO2 files."""
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Update status
        dataset.status = "scanning"
        await self.db.commit()

        source_path = Path(dataset.source_folder)
        if not source_path.exists():
            dataset.status = "failed"
            dataset.error_message = f"Source folder not found: {source_path}"
            await self.db.commit()
            raise ValueError(f"Source folder not found: {source_path}")

        # Find SVO2 files
        files_found = 0
        files_added = 0
        duplicates_skipped = 0
        total_size = 0
        errors: list[str] = []

        pattern = "**/*.svo2" if recursive else "*.svo2"
        for svo2_path in source_path.glob(pattern):
            files_found += 1

            try:
                # Check for duplicates by path
                existing = await self.db.execute(
                    select(DatasetFile).where(
                        DatasetFile.dataset_id == dataset_id,
                        DatasetFile.original_path == str(svo2_path),
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    duplicates_skipped += 1
                    continue

                # Get file info
                file_stat = svo2_path.stat()
                file_size = file_stat.st_size
                total_size += file_size

                # Calculate relative path
                relative_path = str(svo2_path.relative_to(source_path))

                # Create file record
                dataset_file = DatasetFile(
                    dataset_id=dataset_id,
                    original_path=str(svo2_path),
                    original_filename=svo2_path.name,
                    relative_path=relative_path,
                    file_size=file_size,
                    status="discovered",
                    discovered_at=datetime.now(timezone.utc),
                )

                # Extract metadata if requested
                if extract_metadata:
                    try:
                        metadata = await self._extract_svo2_metadata(svo2_path)
                        dataset_file.camera_id = metadata.get("camera_id")
                        dataset_file.camera_model = metadata.get("camera_model")
                        dataset_file.camera_serial = metadata.get("serial_number")
                        dataset_file.firmware_version = metadata.get("firmware_version")
                        dataset_file.frame_count = metadata.get("frame_count")
                        dataset_file.resolution_width = metadata.get("resolution", {}).get("width")
                        dataset_file.resolution_height = metadata.get("resolution", {}).get("height")
                        dataset_file.fps = metadata.get("fps")
                        dataset_file.file_hash = metadata.get("file_hash")
                        dataset_file.metadata = metadata
                    except Exception as e:
                        logger.warning(f"Failed to extract metadata from {svo2_path}: {e}")
                        errors.append(f"Metadata extraction failed for {svo2_path.name}: {str(e)}")

                self.db.add(dataset_file)
                files_added += 1

            except Exception as e:
                logger.error(f"Error processing {svo2_path}: {e}")
                errors.append(f"Error processing {svo2_path.name}: {str(e)}")

        # Update dataset statistics
        dataset.total_files = files_found - duplicates_skipped
        dataset.total_size_bytes = total_size
        dataset.status = "scanned"
        await self.db.commit()

        logger.info(
            f"Scanned dataset {dataset_id}: found {files_found} files, "
            f"added {files_added}, skipped {duplicates_skipped} duplicates"
        )

        return DatasetScanResponse(
            dataset_id=dataset_id,
            files_found=files_found,
            files_added=files_added,
            duplicates_skipped=duplicates_skipped,
            total_size_bytes=total_size,
            errors=errors,
        )

    async def _extract_svo2_metadata(self, svo2_path: Path) -> dict:
        """Extract metadata from SVO2 file using ZED SDK."""
        try:
            from processing.svo2.reader import SVO2Reader

            with SVO2Reader(svo2_path) as reader:
                metadata = reader.get_metadata()
                # Use serial number as camera_id
                metadata["camera_id"] = str(metadata.get("serial_number", "unknown"))
                return metadata

        except ImportError:
            # ZED SDK not available - return basic metadata
            logger.warning("ZED SDK not available - using basic metadata")
            file_hash = self._calculate_file_hash(svo2_path)
            return {
                "file_path": str(svo2_path),
                "file_name": svo2_path.name,
                "file_hash": file_hash,
                "file_size_mb": svo2_path.stat().st_size / (1024 * 1024),
                "camera_id": file_hash[:8],  # Use hash prefix as camera ID
            }

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of first 64KB of file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            hasher.update(f.read(65536))
        return hasher.hexdigest()[:16]

    async def prepare_files(
        self,
        dataset_id: UUID,
        output_directory: str | None = None,
    ) -> DatasetPrepareResponse:
        """Prepare (copy and rename) dataset files."""
        result = await self.db.execute(
            select(Dataset)
            .options(selectinload(Dataset.files))
            .where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise ValueError(f"Dataset {dataset_id} not found")

        if dataset.status not in ("scanned", "ready"):
            raise ValueError(
                f"Dataset must be scanned before preparing. Current status: {dataset.status}"
            )

        # Determine output directory
        output_dir = Path(output_directory or dataset.output_directory or OUTPUT_BASE / str(dataset_id))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Update dataset
        dataset.output_directory = str(output_dir)
        dataset.status = "preparing"
        await self.db.commit()

        # Count files to prepare
        files_to_prepare = sum(
            1 for f in dataset.files if f.status == "discovered"
        )

        logger.info(
            f"Preparing dataset {dataset_id}: {files_to_prepare} files to {output_dir}"
        )

        return DatasetPrepareResponse(
            dataset_id=dataset_id,
            status="preparing",
            files_to_prepare=files_to_prepare,
            message=f"Started preparation of {files_to_prepare} files",
        )

    async def copy_file(
        self,
        file_id: UUID,
        dataset_id: UUID,
        job_id: UUID | None = None,
    ) -> bool:
        """
        Copy and rename a single dataset file.

        This method is called by the Celery task to process files one at a time.
        """
        result = await self.db.execute(
            select(DatasetFile, Dataset)
            .join(Dataset)
            .where(DatasetFile.id == file_id)
        )
        row = result.first()
        if row is None:
            return False

        dataset_file, dataset = row[0], row[1]

        # Update status
        dataset_file.status = "copying"
        await self.db.commit()

        try:
            source_path = Path(dataset_file.original_path)
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            # Generate new filename with naming convention
            timestamp = int(datetime.now(timezone.utc).timestamp())
            camera_id = dataset_file.camera_id or "unknown"
            job_id_str = str(job_id)[:8] if job_id else str(dataset_id)[:8]

            new_filename = f"{job_id_str}_{timestamp}_{camera_id}_{dataset_file.original_filename}"

            # Create camera-specific subdirectory
            output_dir = Path(dataset.output_directory) / camera_id
            output_dir.mkdir(parents=True, exist_ok=True)

            dest_path = output_dir / new_filename

            # Copy the file
            shutil.copy2(source_path, dest_path)

            # Update file record
            dataset_file.renamed_path = str(dest_path)
            dataset_file.renamed_filename = new_filename
            dataset_file.status = "copied"
            dataset_file.copied_at = datetime.now(timezone.utc)

            # Update dataset prepared count
            dataset.prepared_files += 1

            await self.db.commit()

            logger.info(f"Copied file {file_id}: {source_path.name} -> {new_filename}")
            return True

        except Exception as e:
            dataset_file.status = "failed"
            dataset_file.error_message = str(e)
            await self.db.commit()

            logger.error(f"Failed to copy file {file_id}: {e}")
            return False

    async def get_dataset_files(
        self,
        dataset_id: UUID,
        status: str | None = None,
        camera_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DatasetFileDetail], int]:
        """Get files in a dataset."""
        query = select(DatasetFile).where(DatasetFile.dataset_id == dataset_id)
        count_query = select(func.count(DatasetFile.id)).where(
            DatasetFile.dataset_id == dataset_id
        )

        if status:
            query = query.where(DatasetFile.status == status)
            count_query = count_query.where(DatasetFile.status == status)
        if camera_id:
            query = query.where(DatasetFile.camera_id == camera_id)
            count_query = count_query.where(DatasetFile.camera_id == camera_id)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(DatasetFile.discovered_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)

        files = [self._to_file_detail(f) for f in result.scalars().all()]
        return files, total

    async def get_cameras(self, dataset_id: UUID) -> DatasetCamerasResponse:
        """Get cameras in a dataset."""
        result = await self.db.execute(
            select(
                DatasetFile.camera_id,
                DatasetFile.camera_model,
                DatasetFile.camera_serial,
                func.count(DatasetFile.id).label("file_count"),
                func.sum(DatasetFile.frame_count).label("total_frames"),
            )
            .where(DatasetFile.dataset_id == dataset_id)
            .group_by(
                DatasetFile.camera_id,
                DatasetFile.camera_model,
                DatasetFile.camera_serial,
            )
        )

        cameras = []
        for row in result.all():
            cameras.append(CameraInfo(
                camera_id=row.camera_id or "unknown",
                camera_model=row.camera_model,
                camera_serial=row.camera_serial,
                file_count=row.file_count,
                total_frames=row.total_frames,
            ))

        return DatasetCamerasResponse(
            dataset_id=dataset_id,
            cameras=cameras,
        )

    def _to_response(
        self, dataset: Dataset, job_stats: JobStats | None = None
    ) -> DatasetResponse:
        """Convert dataset model to response schema."""
        return DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            customer=dataset.customer,
            site=dataset.site,
            equipment=dataset.equipment,
            collection_date=dataset.collection_date,
            object_types=dataset.object_types,
            source_folder=dataset.source_folder,
            output_directory=dataset.output_directory,
            status=dataset.status,
            total_files=dataset.total_files,
            total_size_bytes=dataset.total_size_bytes,
            prepared_files=dataset.prepared_files,
            error_message=dataset.error_message,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            job_stats=job_stats or JobStats(),
        )

    def _to_detail_response(
        self, dataset: Dataset, job_count: int
    ) -> DatasetDetailResponse:
        """Convert dataset model to detailed response schema."""
        files = [
            DatasetFileSummary(
                id=f.id,
                original_filename=f.original_filename,
                relative_path=f.relative_path,
                camera_id=f.camera_id,
                camera_model=f.camera_model,
                file_size=f.file_size,
                frame_count=f.frame_count,
                resolution=(
                    f"{f.resolution_width}x{f.resolution_height}"
                    if f.resolution_width and f.resolution_height
                    else None
                ),
                fps=f.fps,
                status=f.status,
                error_message=f.error_message,
            )
            for f in dataset.files
        ]

        return DatasetDetailResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            customer=dataset.customer,
            site=dataset.site,
            equipment=dataset.equipment,
            collection_date=dataset.collection_date,
            object_types=dataset.object_types,
            source_folder=dataset.source_folder,
            output_directory=dataset.output_directory,
            status=dataset.status,
            total_files=dataset.total_files,
            total_size_bytes=dataset.total_size_bytes,
            prepared_files=dataset.prepared_files,
            error_message=dataset.error_message,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            files=files,
            job_count=job_count,
        )

    def _to_file_detail(self, f: DatasetFile) -> DatasetFileDetail:
        """Convert file model to detail schema."""
        return DatasetFileDetail(
            id=f.id,
            dataset_id=f.dataset_id,
            original_path=f.original_path,
            original_filename=f.original_filename,
            relative_path=f.relative_path,
            renamed_path=f.renamed_path,
            renamed_filename=f.renamed_filename,
            camera_id=f.camera_id,
            camera_model=f.camera_model,
            camera_serial=f.camera_serial,
            firmware_version=f.firmware_version,
            file_hash=f.file_hash,
            file_size=f.file_size,
            frame_count=f.frame_count,
            recording_start_ns=f.recording_start_ns,
            recording_duration_ms=f.recording_duration_ms,
            resolution_width=f.resolution_width,
            resolution_height=f.resolution_height,
            fps=f.fps,
            status=f.status,
            discovered_at=f.discovered_at,
            copied_at=f.copied_at,
            error_message=f.error_message,
            metadata=f.metadata,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
