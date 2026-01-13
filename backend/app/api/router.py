"""Main API router that aggregates all route modules."""

from fastapi import APIRouter

from backend.app.api.routes import (
    annotations,
    cleanup,
    config,
    data,
    datasets,
    export,
    files,
    jobs,
    lineage,
    review,
)

api_router = APIRouter()

# Include all route modules
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(annotations.router, tags=["annotations"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(data.router, prefix="/data", tags=["data"])
api_router.include_router(lineage.router, prefix="/lineage", tags=["lineage"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(cleanup.router, prefix="/cleanup", tags=["cleanup"])
