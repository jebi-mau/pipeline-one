"""FastAPI application entry point."""

import logging
import shutil
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.api.router import api_router
from backend.app.config import get_settings
from backend.app.core.logging import setup_logging
from backend.app.db.session import close_db, engine, init_db

logger = logging.getLogger(__name__)

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
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/health/deep")
async def deep_health_check() -> dict:
    """
    Deep health check endpoint with dependency status.

    Checks database, Redis, and disk space availability.
    Returns detailed status for monitoring and alerting.
    """
    services: dict[str, dict] = {}
    overall_status = "healthy"

    # Check database
    try:
        async with engine.begin() as conn:
            start = datetime.now(timezone.utc)
            await conn.execute(text("SELECT 1"))
            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            services["database"] = {
                "status": "up",
                "latency_ms": round(latency_ms, 2),
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services["database"] = {"status": "down", "error": str(e)}
        overall_status = "unhealthy"

    # Check Redis
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            socket_timeout=5,
        )
        start = datetime.now(timezone.utc)
        redis_client.ping()
        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        info = redis_client.info("memory")
        services["redis"] = {
            "status": "up",
            "latency_ms": round(latency_ms, 2),
            "memory_used_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
        }
        redis_client.close()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        services["redis"] = {"status": "down", "error": str(e)}
        overall_status = "unhealthy"

    # Check disk space
    try:
        data_path = settings.data_root
        if data_path.exists():
            usage = shutil.disk_usage(data_path)
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            used_percent = (usage.used / usage.total) * 100

            disk_status = "up"
            if free_gb < settings.disk_space_error_threshold_gb:
                disk_status = "critical"
                if overall_status == "healthy":
                    overall_status = "degraded"
            elif free_gb < settings.disk_space_warning_threshold_gb:
                disk_status = "warning"
                if overall_status == "healthy":
                    overall_status = "degraded"

            services["disk"] = {
                "status": disk_status,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 1),
                "path": str(data_path),
            }
        else:
            services["disk"] = {"status": "warning", "error": "Data path not found"}
    except Exception as e:
        logger.error(f"Disk health check failed: {e}")
        services["disk"] = {"status": "unknown", "error": str(e)}

    return {
        "status": overall_status,
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "services": services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health",
    }
