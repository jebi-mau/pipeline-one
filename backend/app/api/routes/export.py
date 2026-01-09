"""Export API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.export import ExportRequest, ExportResponse, ExportStatus
from backend.app.services.export_service import ExportService

router = APIRouter()


@router.post("/{job_id}", response_model=ExportResponse, status_code=202)
async def create_export(
    job_id: UUID,
    export_request: ExportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportResponse:
    """
    Create a new export for a completed job.

    Supports KITTI, COCO, and JSON formats.
    """
    service = ExportService(db)
    export = await service.create_export(job_id, export_request)
    if export is None:
        raise HTTPException(status_code=404, detail="Job not found or not completed")
    return export


@router.get("/{job_id}/status", response_model=ExportStatus)
async def get_export_status(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Literal["kitti", "coco", "json"] = "kitti",
) -> ExportStatus:
    """
    Get the status of an export operation.
    """
    service = ExportService(db)
    status = await service.get_export_status(job_id, format)
    if status is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return status


@router.get("/{job_id}/kitti")
async def download_kitti_export(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Download KITTI-format dataset as a ZIP file.
    """
    service = ExportService(db)
    file_path = await service.get_export_file(job_id, "kitti")
    if file_path is None:
        raise HTTPException(status_code=404, detail="Export not found or not ready")
    return FileResponse(
        path=file_path,
        filename=f"job_{job_id}_kitti.zip",
        media_type="application/zip",
    )


@router.get("/{job_id}/coco")
async def download_coco_export(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Download COCO-format annotations as a JSON file.
    """
    service = ExportService(db)
    file_path = await service.get_export_file(job_id, "coco")
    if file_path is None:
        raise HTTPException(status_code=404, detail="Export not found or not ready")
    return FileResponse(
        path=file_path,
        filename=f"job_{job_id}_coco.json",
        media_type="application/json",
    )


@router.get("/{job_id}/json")
async def download_json_export(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Download full results as JSON with extended metadata.
    """
    service = ExportService(db)
    file_path = await service.get_export_file(job_id, "json")
    if file_path is None:
        raise HTTPException(status_code=404, detail="Export not found or not ready")
    return FileResponse(
        path=file_path,
        filename=f"job_{job_id}_results.json",
        media_type="application/json",
    )


@router.get("/{job_id}/csv")
async def download_csv_export(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Download summary statistics as CSV.
    """
    service = ExportService(db)
    file_path = await service.get_export_file(job_id, "csv")
    if file_path is None:
        raise HTTPException(status_code=404, detail="Export not found or not ready")
    return FileResponse(
        path=file_path,
        filename=f"job_{job_id}_summary.csv",
        media_type="text/csv",
    )


@router.delete("/{job_id}/{format}", status_code=204)
async def delete_export(
    job_id: UUID,
    format: Literal["kitti", "coco", "json", "csv"],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete an export and its files.
    """
    service = ExportService(db)
    success = await service.delete_export(job_id, format)
    if not success:
        raise HTTPException(status_code=404, detail="Export not found")
