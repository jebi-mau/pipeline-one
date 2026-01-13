"""Lineage query API routes for data traceability."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.services.lineage_service import LineageService

router = APIRouter()


# Response schemas
class FrameLineageResponse(BaseModel):
    """Response for frame lineage query."""

    frame: dict
    dataset_file: dict | None
    dataset: dict | None
    job: dict | None
    annotations: list[dict]
    sensor_data: dict | None


class SVO2LineageResponse(BaseModel):
    """Response for SVO2/DatasetFile lineage query."""

    dataset_file: dict
    dataset: dict | None
    frames: list[dict]
    annotation_stats: dict


class AnnotationLineageResponse(BaseModel):
    """Response for annotation lineage query."""

    annotation: dict
    import_record: dict | None
    frame: dict | None
    svo2_file: dict | None
    dataset: dict | None


class DatasetSummaryResponse(BaseModel):
    """Response for dataset summary."""

    dataset: dict
    files: dict
    frames: dict
    annotations: dict
    jobs: dict


class LineageEventCreate(BaseModel):
    """Request to create a lineage event."""

    event_type: str = Field(..., description="Type of event: extraction, annotation_import, export, scan, prepare")
    dataset_id: UUID | None = None
    job_id: UUID | None = None
    dataset_file_id: UUID | None = None
    frame_id: UUID | None = None
    details: dict | None = None


class LineageEventResponse(BaseModel):
    """Response for a lineage event."""

    id: str
    event_type: str
    dataset_id: str | None
    job_id: str | None
    dataset_file_id: str | None
    frame_id: str | None
    details: dict | None
    created_at: str | None


class LineageEventsResponse(BaseModel):
    """Response for lineage events list."""

    events: list[LineageEventResponse]
    total: int


# Routes
@router.get("/frame/{frame_id}", response_model=FrameLineageResponse)
async def get_frame_lineage(
    frame_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameLineageResponse:
    """
    Get complete lineage for a frame.

    Returns frame details with full lineage to dataset file, dataset,
    processing job, annotations, and sensor data.
    """
    service = LineageService(db)
    result = await service.get_frame_lineage(frame_id)

    if not result:
        raise HTTPException(status_code=404, detail="Frame not found")

    return FrameLineageResponse(**result)


@router.get("/svo2/{dataset_file_id}", response_model=SVO2LineageResponse)
async def get_svo2_lineage(
    dataset_file_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SVO2LineageResponse:
    """
    Get lineage for an SVO2 file (DatasetFile).

    Returns SVO2 file details with parent dataset, all extracted frames,
    and annotation statistics.
    """
    service = LineageService(db)
    result = await service.get_svo2_lineage(dataset_file_id)

    if not result:
        raise HTTPException(status_code=404, detail="SVO2 file not found")

    return SVO2LineageResponse(**result)


@router.get("/annotation/{annotation_id}", response_model=AnnotationLineageResponse)
async def get_annotation_lineage(
    annotation_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationLineageResponse:
    """
    Get lineage for an external annotation.

    Returns annotation details with lineage back to frame, SVO2 file,
    and dataset.
    """
    service = LineageService(db)
    result = await service.get_annotation_lineage(annotation_id)

    if not result:
        raise HTTPException(status_code=404, detail="Annotation not found")

    return AnnotationLineageResponse(**result)


@router.get("/dataset/{dataset_id}/summary", response_model=DatasetSummaryResponse)
async def get_dataset_summary(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetSummaryResponse:
    """
    Get aggregated summary statistics for a dataset.

    Returns dataset info with file counts, frame counts, annotation stats,
    and processing status.
    """
    service = LineageService(db)
    result = await service.get_dataset_summary(dataset_id)

    if not result:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return DatasetSummaryResponse(**result)


@router.get("/events", response_model=LineageEventsResponse)
async def get_lineage_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: Annotated[UUID | None, Query(description="Filter by dataset")] = None,
    job_id: Annotated[UUID | None, Query(description="Filter by job")] = None,
    event_type: Annotated[str | None, Query(description="Filter by event type")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> LineageEventsResponse:
    """
    Get lineage events for audit trail.

    Events track operations like extraction, annotation import, and export
    to maintain full data provenance.
    """
    service = LineageService(db)
    events = await service.get_lineage_events(
        dataset_id=dataset_id,
        job_id=job_id,
        event_type=event_type,
        limit=limit,
    )

    return LineageEventsResponse(events=events, total=len(events))


@router.post("/events", response_model=LineageEventResponse, status_code=201)
async def create_lineage_event(
    data: LineageEventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LineageEventResponse:
    """
    Create a lineage event for audit trail.

    This endpoint is typically called by internal services to record
    data operations.
    """
    service = LineageService(db)
    event = await service.log_lineage_event(
        event_type=data.event_type,
        dataset_id=data.dataset_id,
        job_id=data.job_id,
        dataset_file_id=data.dataset_file_id,
        frame_id=data.frame_id,
        details=data.details,
    )

    return LineageEventResponse(
        id=str(event.id),
        event_type=event.event_type,
        dataset_id=str(event.dataset_id) if event.dataset_id else None,
        job_id=str(event.job_id) if event.job_id else None,
        dataset_file_id=str(event.dataset_file_id) if event.dataset_file_id else None,
        frame_id=str(event.frame_id) if event.frame_id else None,
        details=event.details,
        created_at=event.created_at.isoformat() if event.created_at else None,
    )
