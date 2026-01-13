"""Annotation import and management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.annotation import (
    AnnotationImportDetail,
    AnnotationImportListResponse,
    AnnotationImportRequest,
    AnnotationImportResponse,
    AnnotationMatchStats,
    ExternalAnnotationListResponse,
    FrameAnnotationsResponse,
    TrainingExportRequest,
    TrainingExportResponse,
)
from backend.app.services.annotation_service import AnnotationService

router = APIRouter()


@router.post(
    "/datasets/{dataset_id}/annotations/import",
    response_model=AnnotationImportResponse,
)
async def import_annotations(
    dataset_id: UUID,
    request: AnnotationImportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationImportResponse:
    """
    Import annotations from external annotation tool.

    Supported tools and formats:
    - CVAT: XML (default), JSON
    - COCO: JSON

    Annotations will be matched to frames by filename or frame index.
    """
    service = AnnotationService(db)
    try:
        return await service.import_annotations(
            dataset_id=dataset_id,
            source_path=request.source_path,
            source_tool=request.source_tool,
            source_format=request.source_format,
            match_by=request.match_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/datasets/{dataset_id}/annotations/imports",
    response_model=AnnotationImportListResponse,
)
async def list_imports(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AnnotationImportListResponse:
    """
    List all annotation imports for a dataset.
    """
    service = AnnotationService(db)
    imports, total = await service.list_imports(
        dataset_id=dataset_id,
        limit=limit,
        offset=offset,
    )
    return AnnotationImportListResponse(
        imports=imports,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/annotations/imports/{import_id}",
    response_model=AnnotationImportDetail,
)
async def get_import(
    import_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationImportDetail:
    """
    Get annotation import details.
    """
    service = AnnotationService(db)
    result = await service.get_import_detail(import_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Import not found")
    return result


@router.delete("/annotations/imports/{import_id}", status_code=204)
async def delete_import(
    import_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete an annotation import and all its annotations.
    """
    service = AnnotationService(db)
    success = await service.delete_import(import_id)
    if not success:
        raise HTTPException(status_code=404, detail="Import not found")


@router.get(
    "/annotations/imports/{import_id}/annotations",
    response_model=ExternalAnnotationListResponse,
)
async def list_annotations(
    import_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    matched_only: Annotated[bool, Query(description="Only show matched annotations")] = False,
    label: Annotated[str | None, Query(description="Filter by label")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExternalAnnotationListResponse:
    """
    List annotations from an import with filtering.
    """
    service = AnnotationService(db)
    annotations, total, matched, unmatched = await service.list_annotations(
        import_id=import_id,
        matched_only=matched_only,
        label=label,
        limit=limit,
        offset=offset,
    )
    return ExternalAnnotationListResponse(
        annotations=annotations,
        total=total,
        matched=matched,
        unmatched=unmatched,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/annotations/imports/{import_id}/stats",
    response_model=AnnotationMatchStats,
)
async def get_match_stats(
    import_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationMatchStats:
    """
    Get matching statistics for an import.
    """
    service = AnnotationService(db)
    result = await service.get_match_stats(import_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Import not found")
    return result


@router.get(
    "/frames/{frame_id}/annotations",
    response_model=FrameAnnotationsResponse,
)
async def get_frame_annotations(
    frame_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameAnnotationsResponse:
    """
    Get all external annotations for a specific frame.
    """
    service = AnnotationService(db)
    result = await service.get_frame_annotations(frame_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Frame not found")
    return result


@router.post(
    "/datasets/{dataset_id}/export/training",
    response_model=TrainingExportResponse,
)
async def export_training_data(
    dataset_id: UUID,
    request: TrainingExportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingExportResponse:
    """
    Export training data in TFRecord and/or COCO format.

    This starts a background task that:
    1. Pairs frames with their external annotations
    2. Generates TFRecords with images and bounding boxes
    3. Creates COCO JSON annotation files
    4. Splits data into train/val/test sets
    """
    # Trigger Celery task
    from worker.tasks.annotations import export_training_data as export_task

    task = export_task.delay(
        str(dataset_id),
        request.output_directory,
        request.format,
        list(request.split_ratio),
        request.include_unmatched,
        request.labels_filter,
        request.shuffle_seed,
    )

    return TrainingExportResponse(
        dataset_id=dataset_id,
        status="started",
        output_directory=request.output_directory or f"data/output/{dataset_id}/training",
        format=request.format,
        total_images=0,  # Will be updated by task
        total_annotations=0,
        train_count=0,
        val_count=0,
        test_count=0,
        message=f"Export task started with ID: {task.id}",
    )
