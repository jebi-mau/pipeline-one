"""Main API router that aggregates all route modules."""

from fastapi import APIRouter

from backend.app.api.routes import config, data, export, files, jobs

api_router = APIRouter()

# Include all route modules
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(data.router, prefix="/data", tags=["data"])
