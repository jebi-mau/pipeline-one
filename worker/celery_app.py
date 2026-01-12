"""Celery application configuration."""

import os

from celery import Celery

# Redis URL from environment or default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

app = Celery(
    "svo2_sam3_analyzer",
    broker=f"{REDIS_URL}/0",
    backend=f"{REDIS_URL}/1",
    include=[
        "worker.tasks.extraction",
        "worker.tasks.segmentation",
        "worker.tasks.reconstruction",
        "worker.tasks.tracking",
        "worker.tasks.orchestrator",
    ],
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_time_limit=14400,  # 4 hours max (for large SVO2 files)
    task_soft_time_limit=12600,  # Soft limit at 3.5 hours

    # Worker settings
    worker_prefetch_multiplier=1,  # Fair task distribution
    worker_concurrency=2,  # 2 concurrent tasks per worker

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours

    # Task queues
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
        "gpu": {
            "exchange": "gpu",
            "routing_key": "gpu",
        },
    },
    task_default_queue="default",

    # Task routes
    task_routes={
        "worker.tasks.segmentation.*": {"queue": "gpu"},
        "worker.tasks.reconstruction.*": {"queue": "gpu"},
    },
)


if __name__ == "__main__":
    app.start()
