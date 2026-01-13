"""Export service for generating output files."""

import logging
from pathlib import Path
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.export import Export
from backend.app.models.job import ProcessingJob
from backend.app.schemas.export import ExportRequest, ExportResponse, ExportStatus

logger = logging.getLogger(__name__)


class ExportService:
    """Service for managing exports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_export(
        self, job_id: UUID, request: ExportRequest
    ) -> ExportResponse | None:
        """Create a new export for a job."""
        # Check if job exists and is completed
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None or job.status != "completed":
            return None

        # Check if export already exists
        existing_result = await self.db.execute(
            select(Export).where(
                Export.job_id == job_id,
                Export.format == request.format,
            )
        )
        existing_export = existing_result.scalar_one_or_none()
        if existing_export is not None:
            # Return existing export instead of creating duplicate
            return ExportResponse(
                id=existing_export.id,
                job_id=job_id,
                format=existing_export.format,
                status=existing_export.status,
                created_at=existing_export.created_at,
            )

        # Create export record
        export = Export(
            job_id=job_id,
            format=request.format,
            status="pending",
        )
        self.db.add(export)
        await self.db.flush()

        # TODO: Trigger Celery task to generate export

        logger.info(f"Created export {export.id} for job {job_id}: {request.format}")
        return ExportResponse(
            id=export.id,
            job_id=job_id,
            format=request.format,
            status="pending",
            created_at=export.created_at,
        )

    async def get_export_status(
        self, job_id: UUID, format: str
    ) -> ExportStatus | None:
        """Get export status."""
        result = await self.db.execute(
            select(Export).where(
                Export.job_id == job_id,
                Export.format == format,
            )
        )
        export = result.scalar_one_or_none()
        if export is None:
            return None

        return ExportStatus(
            id=export.id,
            job_id=export.job_id,
            format=export.format,
            status=export.status,
            progress=export.progress,
            file_size=export.file_size,
            output_path=export.output_path,
            error_message=export.error_message,
            created_at=export.created_at,
            completed_at=export.completed_at,
        )

    async def get_export_file(
        self, job_id: UUID, format: Literal["kitti", "coco", "json", "csv"]
    ) -> Path | None:
        """Get path to export file."""
        result = await self.db.execute(
            select(Export).where(
                Export.job_id == job_id,
                Export.format == format,
                Export.status == "completed",
            )
        )
        export = result.scalar_one_or_none()
        if export is None or export.output_path is None:
            return None

        path = Path(export.output_path)
        if not path.exists():
            return None

        return path

    async def delete_export(
        self, job_id: UUID, format: Literal["kitti", "coco", "json", "csv"]
    ) -> bool:
        """Delete an export and its files."""
        result = await self.db.execute(
            select(Export).where(
                Export.job_id == job_id,
                Export.format == format,
            )
        )
        export = result.scalar_one_or_none()
        if export is None:
            return False

        # Delete file if exists
        if export.output_path:
            path = Path(export.output_path)
            if path.exists():
                path.unlink()

        await self.db.delete(export)
        await self.db.commit()
        logger.info(f"Deleted export {export.id} for job {job_id}")
        return True
