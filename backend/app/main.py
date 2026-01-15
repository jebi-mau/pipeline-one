"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.config import get_settings
from backend.app.core.logging import setup_logging
from backend.app.db.session import close_db, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description="Multi-Camera SVO2 Processing with SAM 3 Object Detection",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware - allow all origins for VPN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin for remote VPN access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health",
    }
