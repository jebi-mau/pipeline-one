"""Review mode and training dataset API routes."""

import logging
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.review import (
    AnnotationStatsResponse,
    DiversityAnalysisRequest,
    DiversityAnalysisResponse,
    FrameBatchRequest,
    FrameBatchResponse,
    TrainingDatasetDetail,
    TrainingDatasetListResponse,
    TrainingDatasetRequest,
    TrainingDatasetResponse,
)
from backend.app.services.diversity_service import DiversityService
from backend.app.services.review_service import ReviewService
from backend.app.services.training_dataset_service import TrainingDatasetService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Annotation Statistics
# =============================================================================


@router.get(
    "/jobs/{job_id}/annotation-stats",
    response_model=AnnotationStatsResponse,
)
async def get_annotation_stats(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationStatsResponse:
    """
    Get aggregated annotation statistics by class for filtering UI.

    Returns class-level statistics including total count, frame count,
    average confidence, and all annotation IDs for individual filtering.
    """
    try:
        service = ReviewService(db)
        return await service.get_annotation_stats(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting annotation stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get annotation statistics")


# =============================================================================
# Frame Batch for Playback
# =============================================================================


@router.get(
    "/jobs/{job_id}/frames/batch",
    response_model=FrameBatchResponse,
)
async def get_frames_batch(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    start_index: Annotated[int, Query(ge=0)] = 0,
    count: Annotated[int, Query(ge=1, le=100)] = 24,
) -> FrameBatchResponse:
    """
    Get batch of frames for video playback buffering.

    Returns minimal frame data optimized for playback UI.
    """
    try:
        service = ReviewService(db)
        return await service.get_frame_batch(job_id, start_index, count)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Frame Diversity Analysis
# =============================================================================


@router.post(
    "/jobs/{job_id}/diversity/analyze",
    response_model=DiversityAnalysisResponse,
)
async def analyze_frame_diversity(
    job_id: UUID,
    request: DiversityAnalysisRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DiversityAnalysisResponse:
    """
    Analyze frame diversity using perceptual hashing and motion estimation.

    This endpoint computes:
    - Perceptual hashes (dHash) for visual similarity detection
    - Motion scores via frame differencing

    Results are cached for fast re-analysis with different thresholds.
    """
    try:
        service = DiversityService(db)
        return await service.analyze_diversity(
            job_id,
            similarity_threshold=request.similarity_threshold,
            motion_threshold=request.motion_threshold,
            camera=request.sample_camera,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing diversity: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze frame diversity")


@router.get(
    "/jobs/{job_id}/diversity/status",
    response_model=DiversityAnalysisResponse,
)
async def get_diversity_status(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    similarity_threshold: Annotated[float, Query(ge=0, le=1)] = 0.85,
    motion_threshold: Annotated[float, Query(ge=0, le=1)] = 0.02,
) -> DiversityAnalysisResponse:
    """
    Get cached diversity analysis status or compute with default thresholds.

    If cached data exists, recomputes selection with provided thresholds.
    """
    try:
        service = DiversityService(db)
        cache = await service.get_cached_analysis(job_id)

        if cache and cache.status == "complete":
            # Re-run selection with new thresholds using cached data
            return await service.analyze_diversity(
                job_id,
                similarity_threshold=similarity_threshold,
                motion_threshold=motion_threshold,
                use_cache=True,
            )

        return DiversityAnalysisResponse(
            job_id=str(job_id),
            status="pending" if not cache else cache.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Training Dataset Management
# =============================================================================


@router.post(
    "/jobs/{job_id}/training-dataset",
    response_model=TrainingDatasetResponse,
    status_code=201,
)
async def create_training_dataset(
    job_id: UUID,
    request: TrainingDatasetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingDatasetResponse:
    """
    Create a new training dataset from filtered job results.

    The export process runs asynchronously. Use the status endpoint
    to track progress.
    """
    try:
        service = TrainingDatasetService(db)
        dataset = await service.create_training_dataset(job_id, request)

        # Queue export task (will be implemented in worker)
        from worker.tasks.training_export import export_training_dataset

        export_training_dataset.delay(
            str(dataset.id),
            str(job_id),
            request.format,
            request.filter_config.model_dump(),
            {
                "train_ratio": request.train_ratio,
                "val_ratio": request.val_ratio,
                "test_ratio": request.test_ratio,
                "shuffle_seed": request.shuffle_seed,
                "include_masks": request.include_masks,
                "include_depth": request.include_depth,
                "include_3d_boxes": request.include_3d_boxes,
            },
        )

        return TrainingDatasetResponse(
            id=dataset.id,
            job_id=dataset.source_job_id,
            name=dataset.name,
            status=dataset.status,
            progress=dataset.progress,
            total_frames=dataset.total_frames,
            total_annotations=dataset.total_annotations,
            train_count=dataset.train_count,
            val_count=dataset.val_count,
            test_count=dataset.test_count,
            created_at=dataset.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating training dataset: {e}")
        raise HTTPException(status_code=500, detail="Failed to create training dataset")


@router.get(
    "/training-datasets",
    response_model=TrainingDatasetListResponse,
)
async def list_training_datasets(
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: Annotated[UUID | None, Query(description="Filter by source job")] = None,
) -> TrainingDatasetListResponse:
    """List all training datasets, optionally filtered by source job."""
    service = TrainingDatasetService(db)
    return await service.list_training_datasets(job_id)


@router.get(
    "/training-datasets/{dataset_id}",
    response_model=TrainingDatasetDetail,
)
async def get_training_dataset(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingDatasetDetail:
    """Get training dataset details including lineage information."""
    service = TrainingDatasetService(db)
    dataset = await service.get_training_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Training dataset not found")
    return dataset


@router.get(
    "/training-datasets/{dataset_id}/status",
    response_model=TrainingDatasetResponse,
)
async def get_training_dataset_status(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingDatasetResponse:
    """Get training dataset export progress and status."""
    service = TrainingDatasetService(db)
    dataset = await service.get_training_dataset_response(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Training dataset not found")
    return dataset


@router.get("/training-datasets/{dataset_id}/download/{format}")
async def download_training_dataset(
    dataset_id: UUID,
    format: Literal["kitti", "coco"],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Download exported training dataset.

    Returns a ZIP file containing the dataset in the requested format.
    """
    service = TrainingDatasetService(db)
    dataset = await service.get_training_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Training dataset not found")

    if dataset.status != "complete":
        raise HTTPException(
            status_code=400,
            detail=f"Dataset export not complete. Status: {dataset.status}",
        )

    # Get the appropriate path
    if format == "kitti":
        file_path = dataset.kitti_path
    else:
        file_path = dataset.coco_path

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Format '{format}' not available for this dataset",
        )

    path = Path(file_path)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Export file not found on disk",
        )

    return FileResponse(
        path=path,
        filename=f"{dataset.name}_{format}.zip",
        media_type="application/zip",
    )
