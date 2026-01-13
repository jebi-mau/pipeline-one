"""Dataset management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.dataset import (
    DatasetCamerasResponse,
    DatasetCreate,
    DatasetDetailResponse,
    DatasetFileDetail,
    DatasetListResponse,
    DatasetPrepareRequest,
    DatasetPrepareResponse,
    DatasetResponse,
    DatasetScanRequest,
    DatasetScanResponse,
    DatasetUpdate,
)
from backend.app.services.dataset_service import DatasetService

router = APIRouter()


@router.post("", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    data: DatasetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetResponse:
    """
    Create a new dataset with rich metadata.

    A dataset represents a collection of SVO2 files from a data collection session.
    After creation, use the /scan endpoint to discover SVO2 files in the source folder.
    """
    service = DatasetService(db)
    return await service.create_dataset(data)


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    db: Annotated[AsyncSession, Depends(get_db)],
    customer: Annotated[str | None, Query(description="Filter by customer")] = None,
    site: Annotated[str | None, Query(description="Filter by site")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DatasetListResponse:
    """
    List all datasets with optional filtering.
    """
    service = DatasetService(db)
    datasets, total = await service.list_datasets(
        limit=limit,
        offset=offset,
        customer=customer,
        site=site,
        status=status,
    )
    return DatasetListResponse(
        datasets=datasets,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetDetailResponse:
    """
    Get dataset details including discovered files.
    """
    service = DatasetService(db)
    dataset = await service.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.patch("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: UUID,
    data: DatasetUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetResponse:
    """
    Update dataset metadata.
    """
    service = DatasetService(db)
    dataset = await service.update_dataset(dataset_id, data)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a dataset and all its associated files.
    """
    service = DatasetService(db)
    success = await service.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")


@router.post("/{dataset_id}/scan", response_model=DatasetScanResponse)
async def scan_folder(
    dataset_id: UUID,
    request: DatasetScanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetScanResponse:
    """
    Scan the source folder for SVO2 files.

    This will discover all SVO2 files in the source folder (recursively if specified)
    and extract metadata from each file including camera serial number.
    """
    service = DatasetService(db)
    try:
        return await service.scan_folder(
            dataset_id,
            recursive=request.recursive,
            extract_metadata=request.extract_metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{dataset_id}/prepare", response_model=DatasetPrepareResponse)
async def prepare_files(
    dataset_id: UUID,
    request: DatasetPrepareRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetPrepareResponse:
    """
    Prepare (copy and rename) dataset files.

    This starts a background task that:
    1. Copies each SVO2 file to the output directory
    2. Renames files to include job_id, timestamp, and camera_id for traceability
    3. Organizes files into camera-specific subdirectories
    """
    service = DatasetService(db)
    try:
        result = await service.prepare_files(
            dataset_id,
            output_directory=request.output_directory,
        )

        # Trigger Celery task for actual file copying
        from worker.tasks.dataset import prepare_dataset_files

        prepare_dataset_files.delay(str(dataset_id))

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dataset_id}/files")
async def list_files(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Annotated[str | None, Query(description="Filter by file status")] = None,
    camera_id: Annotated[str | None, Query(description="Filter by camera ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """
    List files in a dataset with filtering.
    """
    service = DatasetService(db)
    files, total = await service.get_dataset_files(
        dataset_id,
        status=status,
        camera_id=camera_id,
        limit=limit,
        offset=offset,
    )
    return {
        "files": files,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{dataset_id}/cameras", response_model=DatasetCamerasResponse)
async def list_cameras(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetCamerasResponse:
    """
    List all cameras in a dataset.

    Returns aggregated information about each unique camera found in the dataset,
    including file counts and frame totals.
    """
    service = DatasetService(db)
    return await service.get_cameras(dataset_id)


@router.post("/{dataset_id}/extract-all")
async def extract_all_files(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    frame_skip: Annotated[int, Query(ge=1, le=100)] = 1,
    extract_numpy: Annotated[bool, Query(description="Export NumPy arrays")] = False,
    depth_mode: Annotated[str, Query(description="Depth computation mode")] = "NEURAL",
) -> dict:
    """
    Start extraction of all SVO2 files in the dataset.

    This creates a processing job that extracts frames from all prepared SVO2 files.
    Each file will be processed with the specified settings.
    """
    service = DatasetService(db)

    # Verify dataset exists and has prepared files
    dataset = await service.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.status not in ("ready", "completed", "processing"):
        raise HTTPException(
            status_code=400,
            detail=f"Dataset must be in 'ready' status to extract. Current status: {dataset.status}"
        )

    # Create extraction job for all files
    from worker.tasks.orchestrator import process_svo2_batch

    # Get all prepared files
    files, _ = await service.get_dataset_files(dataset_id, status="copied", limit=1000)
    if not files:
        raise HTTPException(status_code=400, detail="No prepared files found for extraction")

    file_paths = [f.renamed_path or f.original_path for f in files if f.renamed_path or f.original_path]

    # Create job configuration
    from backend.app.services.job_service import JobService
    from backend.app.schemas.job import JobCreate

    job_service = JobService(db)
    job = await job_service.create_job(
        JobCreate(
            name=f"Extract All - {dataset.name}",
            input_paths=file_paths,
            stages_to_run=["extraction"],
            config={
                "frame_skip": frame_skip,
                "extract_numpy": extract_numpy,
                "depth_mode": depth_mode,
            },
        ),
        dataset_id=dataset_id,
    )

    # Trigger extraction task
    process_svo2_batch.delay(str(job.id))

    return {
        "dataset_id": str(dataset_id),
        "job_id": str(job.id),
        "files_to_extract": len(file_paths),
        "status": "started",
        "message": f"Started extraction job for {len(file_paths)} files",
    }


@router.post("/{dataset_id}/export-training")
async def export_training_data(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Annotated[str, Query(description="Export format: yolo, coco, kitti")] = "yolo",
    include_unmatched: Annotated[bool, Query(description="Include unmatched annotations")] = False,
) -> dict:
    """
    Export matched annotations as training data.

    This creates an export package containing:
    - Images with matched annotations
    - Annotation files in the specified format (YOLO, COCO, KITTI)
    - A manifest with lineage information
    """
    service = DatasetService(db)

    # Verify dataset exists
    dataset = await service.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get annotation statistics
    from backend.app.services.lineage_service import LineageService
    lineage_service = LineageService(db)
    summary = await lineage_service.get_dataset_summary(dataset_id)

    if not summary or summary["annotations"]["matched"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No matched annotations found. Import and match annotations first."
        )

    # Create export task
    from backend.app.services.export_service import ExportService
    from backend.app.schemas.export import ExportRequest

    export_service = ExportService(db)
    export = await export_service.create_export(
        ExportRequest(
            dataset_id=dataset_id,
            format=format,
            include_unmatched=include_unmatched,
        )
    )

    # Trigger export task
    from worker.tasks.export import export_training_data_task

    export_training_data_task.delay(str(export.id))

    return {
        "dataset_id": str(dataset_id),
        "export_id": str(export.id),
        "format": format,
        "matched_annotations": summary["annotations"]["matched"],
        "status": "started",
        "message": f"Started training data export in {format} format",
    }


@router.get("/{dataset_id}/annotations/imports")
async def list_annotation_imports(
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    List all annotation imports for a dataset.
    """
    from sqlalchemy import select
    from backend.app.models.external_annotation import AnnotationImport

    query = (
        select(AnnotationImport)
        .where(AnnotationImport.dataset_id == dataset_id)
        .order_by(AnnotationImport.created_at.desc())
    )
    result = await db.execute(query)
    imports = result.scalars().all()

    return {
        "imports": [
            {
                "id": str(imp.id),
                "source_tool": imp.source_tool,
                "source_format": imp.source_format,
                "source_filename": imp.source_filename,
                "status": imp.status,
                "total_images": imp.total_images,
                "matched_frames": imp.matched_frames,
                "unmatched_images": imp.unmatched_images,
                "total_annotations": imp.total_annotations,
                "imported_at": imp.imported_at.isoformat() if imp.imported_at else None,
                "completed_at": imp.completed_at.isoformat() if imp.completed_at else None,
            }
            for imp in imports
        ],
        "total": len(imports),
    }
