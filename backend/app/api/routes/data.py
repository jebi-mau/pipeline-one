"""Data access API routes for frame browsing and file serving."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.data import (
    CorrelationTableResponse,
    DataSummary,
    FrameDetail,
    FrameListResponse,
)
from backend.app.services.data_service import DataService

router = APIRouter()


@router.get("/jobs/{job_id}/summary", response_model=DataSummary)
async def get_data_summary(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataSummary:
    """
    Get summary of extracted data for a job.

    Returns statistics about frames, detections, and output files.
    """
    service = DataService(db)
    summary = await service.get_data_summary(job_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return summary


@router.get("/jobs/{job_id}/frames", response_model=FrameListResponse)
async def list_frames(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FrameListResponse:
    """
    List frames for a job with pagination.

    Returns frame summaries with detection counts and thumbnail URLs.
    """
    service = DataService(db)
    return await service.list_frames(job_id, limit=limit, offset=offset)


@router.get("/jobs/{job_id}/frames/{frame_id}", response_model=FrameDetail)
async def get_frame_detail(
    job_id: UUID,
    frame_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameDetail:
    """
    Get detailed information for a specific frame.

    Returns frame data including file URLs, annotations, and metadata.
    """
    service = DataService(db)
    frame = await service.get_frame_detail(job_id, frame_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="Frame not found")
    return frame


@router.get("/jobs/{job_id}/frames/{frame_id}/image/{image_type}")
async def get_frame_image(
    job_id: UUID,
    frame_id: str,
    image_type: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Serve a frame image file.

    Args:
        image_type: One of 'left', 'right', or 'depth'
    """
    if image_type not in ("left", "right", "depth"):
        raise HTTPException(status_code=400, detail="Invalid image type")

    service = DataService(db)
    file_path = service.get_frame_file_path(job_id, frame_id, image_type)

    if file_path is None or not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # Determine content type
    content_type = "image/png"
    if file_path.suffix.lower() in (".jpg", ".jpeg"):
        content_type = "image/jpeg"

    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=file_path.name,
    )


@router.get("/jobs/{job_id}/frames/{frame_id}/pointcloud")
async def get_frame_pointcloud(
    job_id: UUID,
    frame_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Serve a frame point cloud file.

    Returns PLY format point cloud data.
    """
    service = DataService(db)
    file_path = service.get_frame_file_path(job_id, frame_id, "pointcloud")

    if file_path is None or not file_path.exists():
        raise HTTPException(status_code=404, detail="Point cloud not found")

    return FileResponse(
        path=file_path,
        media_type="application/x-ply",
        filename=file_path.name,
    )


@router.get("/jobs/{job_id}/correlation", response_model=CorrelationTableResponse)
async def get_correlation_table(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CorrelationTableResponse:
    """
    Get correlation table showing data availability per frame.

    Shows which data types are available for each frame (RGB, depth, point cloud, etc.)
    """
    service = DataService(db)
    result = await service.get_correlation_table(job_id, limit=limit, offset=offset)
    if result is None:
        raise HTTPException(status_code=404, detail="Job data not found")
    return result


@router.get("/jobs/{job_id}/annotations/{annotation_id}/mask")
async def get_annotation_mask(
    job_id: UUID,
    annotation_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Serve a segmentation mask for an annotation.

    Args:
        annotation_id: Format is '{frame_id}_{detection_index}'
    """
    service = DataService(db)
    file_path = service.get_mask_file_path(job_id, annotation_id)

    if file_path is None or not file_path.exists():
        raise HTTPException(status_code=404, detail="Mask not found")

    return FileResponse(
        path=file_path,
        media_type="image/png",
        filename=file_path.name,
    )
