"""Processing job management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobResponse,
    JobResultsResponse,
    JobStatusUpdate,
)
from backend.app.services.job_service import JobService

router = APIRouter()


@router.post("/create", response_model=JobResponse, status_code=201)
async def create_job(
    job_data: JobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """
    Create a new processing job.

    The job will be created in 'pending' status and must be started explicitly.
    """
    service = JobService(db)
    job = await service.create_job(job_data)
    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Annotated[str | None, Query(description="Filter by job status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobListResponse:
    """
    List all processing jobs with optional filtering.
    """
    service = JobService(db)
    jobs, total = await service.list_jobs(status=status, limit=limit, offset=offset)
    return JobListResponse(jobs=jobs, total=total, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """
    Get job details by ID.
    """
    service = JobService(db)
    job = await service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/start", response_model=JobStatusUpdate)
async def start_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusUpdate:
    """
    Start processing a pending job.
    """
    service = JobService(db)
    result = await service.start_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.post("/{job_id}/pause", response_model=JobStatusUpdate)
async def pause_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusUpdate:
    """
    Pause a running job.
    """
    service = JobService(db)
    result = await service.pause_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.post("/{job_id}/resume", response_model=JobStatusUpdate)
async def resume_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusUpdate:
    """
    Resume a paused job.
    """
    service = JobService(db)
    result = await service.resume_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.post("/{job_id}/cancel", response_model=JobStatusUpdate)
async def cancel_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusUpdate:
    """
    Cancel a running or paused job.
    """
    service = JobService(db)
    result = await service.cancel_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.get("/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResultsResponse:
    """
    Get processing results for a completed job.
    """
    service = JobService(db)
    results = await service.get_job_results(job_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Job not found or not completed")
    return results


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a job and its associated data.
    """
    service = JobService(db)
    success = await service.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
