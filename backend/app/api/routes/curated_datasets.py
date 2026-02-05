"""API routes for curated datasets."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.curated_dataset import (
    CuratedDatasetCreate,
    CuratedDatasetListPaginated,
    CuratedDatasetResponse,
    CuratedDatasetUpdate,
)
from backend.app.services.curated_dataset_service import CuratedDatasetService

router = APIRouter(prefix="/curated-datasets", tags=["curated-datasets"])


@router.post("", response_model=CuratedDatasetResponse, status_code=201)
async def create_curated_dataset(
    data: CuratedDatasetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CuratedDatasetResponse:
    """Create a new curated dataset from review filters.

    This endpoint is called when the user finishes reviewing a job and wants to
    save their filter configuration as a curated dataset for export.
    """
    service = CuratedDatasetService(db)
    try:
        return await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("", response_model=CuratedDatasetListPaginated)
async def list_curated_datasets(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    job_id: Annotated[UUID | None, Query()] = None,
) -> CuratedDatasetListPaginated:
    """List all curated datasets with pagination.

    Optionally filter by source job ID.
    """
    service = CuratedDatasetService(db)
    return await service.list(limit=limit, offset=offset, job_id=job_id)


@router.get("/{curated_id}", response_model=CuratedDatasetResponse)
async def get_curated_dataset(
    curated_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CuratedDatasetResponse:
    """Get a specific curated dataset by ID."""
    service = CuratedDatasetService(db)
    result = await service.get(curated_id)
    if not result:
        raise HTTPException(status_code=404, detail="Curated dataset not found")
    return result


@router.patch("/{curated_id}", response_model=CuratedDatasetResponse)
async def update_curated_dataset(
    curated_id: UUID,
    data: CuratedDatasetUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CuratedDatasetResponse:
    """Update curated dataset metadata (name and description only).

    Filter configuration is immutable after creation to ensure reproducibility.
    """
    service = CuratedDatasetService(db)
    result = await service.update(curated_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Curated dataset not found")
    return result


@router.delete("/{curated_id}", status_code=204)
async def delete_curated_dataset(
    curated_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a curated dataset.

    Note: This will NOT delete any training datasets that were exported from it.
    """
    service = CuratedDatasetService(db)
    success = await service.delete(curated_id)
    if not success:
        raise HTTPException(status_code=404, detail="Curated dataset not found")
