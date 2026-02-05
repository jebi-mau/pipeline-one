"""Celery task definitions."""

# Import tasks to register them with Celery
from worker.tasks import (
    annotations,
    dataset,
    extraction,
    orchestrator,
    reconstruction,
    segmentation,
    tracking,
    training_export,
)

__all__ = [
    "annotations",
    "dataset",
    "extraction",
    "orchestrator",
    "reconstruction",
    "segmentation",
    "tracking",
    "training_export",
]
