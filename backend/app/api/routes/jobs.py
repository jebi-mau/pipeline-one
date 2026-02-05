"""Processing job management API routes."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.job import (
    EstimateDurationRequest,
    EstimateDurationResponse,
    EstimateStorageRequest,
    EstimateStorageResponse,
    JobCreate,
    JobListResponse,
    JobResponse,
    JobResultsResponse,
    JobStatusUpdate,
    StageEstimate,
)
from backend.app.services.benchmark_service import BenchmarkService
from backend.app.services.job_service import JobService
from backend.app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

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


@router.post("/{job_id}/restart", response_model=JobStatusUpdate)
async def restart_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusUpdate:
    """
    Restart a failed or cancelled job.
    """
    service = JobService(db)
    result = await service.restart_job(job_id)
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


@router.post("/estimate-duration", response_model=EstimateDurationResponse)
async def estimate_job_duration(
    request: EstimateDurationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EstimateDurationResponse:
    """
    Estimate job duration before starting.

    This endpoint calculates an estimated processing time based on:
    - Total frames in the SVO2 files
    - Frame skip setting
    - Model variant (affects segmentation speed)
    - Historical performance benchmarks

    Use this to help users understand processing time before starting a job.
    """
    import os
    from pathlib import Path

    from sqlalchemy import or_, select

    from backend.app.models.dataset import DatasetFile

    # Calculate total frames
    total_frames = request.total_frames

    if total_frames is None:
        # First, try to get frame counts from database (fast, no ZED SDK needed)
        total_frames = 0
        files_found_in_db = set()

        if request.svo2_files:
            # Query database for matching files
            stmt = select(DatasetFile).where(
                or_(
                    DatasetFile.original_path.in_(request.svo2_files),
                    DatasetFile.renamed_path.in_(request.svo2_files),
                )
            )
            result = await db.execute(stmt)
            db_files = result.scalars().all()

            for db_file in db_files:
                if db_file.frame_count:
                    total_frames += db_file.frame_count
                    files_found_in_db.add(db_file.original_path)
                    if db_file.renamed_path:
                        files_found_in_db.add(db_file.renamed_path)
                    logger.debug(f"Using cached frame count {db_file.frame_count} for {db_file.original_filename}")

        # For any files not found in database, estimate based on file size
        for svo2_path in request.svo2_files:
            if svo2_path in files_found_in_db:
                continue

            if not os.path.exists(svo2_path):
                logger.warning(f"SVO2 file not found: {svo2_path}")
                continue

            # Estimate based on file size (rough approximation)
            # Assume ~1MB per frame for SVO2 files
            try:
                file_size = Path(svo2_path).stat().st_size
                estimated_frames = file_size // (1024 * 1024)  # 1MB per frame
                total_frames += max(estimated_frames, 100)
                logger.info(f"Estimated {estimated_frames} frames for {svo2_path} based on file size")
            except Exception as e:
                logger.error(f"Error estimating frames for {svo2_path}: {e}")
                total_frames += 1000  # Default estimate

    if total_frames == 0:
        raise HTTPException(
            status_code=400,
            detail="Could not determine frame count from provided files"
        )

    # Get estimate from benchmark service
    benchmark_service = BenchmarkService(db)
    estimate = await benchmark_service.estimate_job_duration(
        total_frames=total_frames,
        frame_skip=request.frame_skip,
        model_variant=request.sam3_model_variant,
        stages=request.stages_to_run,
    )

    # Convert breakdown to StageEstimate models
    breakdown = {}
    for stage, data in estimate.breakdown.items():
        breakdown[stage] = StageEstimate(
            frames=data["frames"],
            estimated_seconds=data["estimated_seconds"],
            fps=data["fps"],
        )

    return EstimateDurationResponse(
        estimated_total_frames=estimate.total_frames,
        estimated_duration_seconds=estimate.estimated_duration_seconds,
        estimated_duration_formatted=estimate.estimated_duration_formatted,
        breakdown=breakdown,
        confidence=estimate.confidence,
        based_on_jobs=estimate.based_on_jobs,
    )


@router.post("/estimate-storage", response_model=EstimateStorageResponse)
async def estimate_job_storage(
    request: EstimateStorageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EstimateStorageResponse:
    """
    Estimate storage required for a job before creation.

    This endpoint calculates estimated disk usage based on:
    - Total frames to process
    - Pipeline stages to run
    - Extraction options (point clouds, masks, images)
    - Frame skip setting

    Use this to warn users about insufficient disk space before starting a job.
    """
    storage_service = StorageService(db)

    result = await storage_service.check_storage_for_job(
        total_frames=request.total_frames,
        stages=request.stages_to_run,
        extract_point_clouds=request.extract_point_clouds,
        extract_right_image=request.extract_right_image,
        extract_masks=request.extract_masks,
        image_format=request.image_format,
        frame_skip=request.frame_skip,
    )

    return EstimateStorageResponse(**result)
