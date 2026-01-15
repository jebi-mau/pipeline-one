"""SAM 3 segmentation task."""

import logging
import time
from pathlib import Path
from typing import Any

from worker.celery_app import app
from worker.db import update_job_progress, record_stage_completion

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    name="worker.tasks.segmentation.run_segmentation",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(IOError, OSError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def run_segmentation(
    self,
    extraction_results: list[dict] | None,
    job_id: str,
    object_classes: list[dict],
    config: dict,
) -> dict[str, Any]:
    """
    Run SAM 3 segmentation on extracted frames.

    Args:
        extraction_results: Results from extraction stage
        job_id: Processing job UUID
        object_classes: Object class definitions for detection
        config: SAM 3 configuration

    Returns:
        Segmentation result summary
    """
    from processing.sam3.batch_processor import BatchConfig, SAM3BatchProcessor
    from processing.sam3.predictor import SAM3Config, SAM3Predictor
    from processing.svo2.frame_registry import FrameRegistry

    logger.info(f"Running segmentation for job {job_id}")

    # Track stage timing
    stage_start_time = time.time()

    # Get frame registries from extraction results
    if extraction_results is None:
        extraction_results = []
    # Handle single result (not wrapped in list)
    elif isinstance(extraction_results, dict):
        extraction_results = [extraction_results]

    registries = []
    for result in extraction_results:
        if isinstance(result, dict) and result.get("status") == "completed":
            registry_path = result.get("frame_registry")
            if registry_path:
                registries.append(Path(registry_path))

    if not registries:
        logger.warning("No frame registries found")
        return {
            "status": "skipped",
            "reason": "No frames to process",
        }

    # Configure SAM 3
    sam_config = SAM3Config(
        model_path=Path(config.get("model_path")) if config.get("model_path") else None,
        confidence_threshold=config.get("confidence_threshold", 0.5),
        iou_threshold=config.get("iou_threshold", 0.7),
        max_detections=config.get("max_detections", 100),
        device=config.get("device", "cuda"),
        precision=config.get("precision", "fp16"),
    )

    batch_config = BatchConfig(
        batch_size=config.get("batch_size", 8),
        num_workers=config.get("num_workers", 4),
        clear_cache_every=config.get("clear_cache_every", 10),
    )

    # Get progress range from config (default to old behavior)
    progress_range = config.get("progress_range", (25, 75))
    range_start, range_end = progress_range

    # Progress callback
    def progress_callback(current: int, total: int, message: str) -> None:
        # Update Celery state
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": "segmentation",
                "current": current,
                "total": total,
                "message": message,
            },
        )

        # Update database progress (stage 2 = segmentation)
        # Calculate overall progress based on assigned range
        stage_progress = (current / total * 100) if total > 0 else 0
        range_size = range_end - range_start
        overall_progress = range_start + (stage_progress / 100 * range_size)

        update_job_progress(
            job_id=job_id,
            stage=2,
            progress=overall_progress,
            stage_progress=stage_progress,
            total_frames=total,
            processed_frames=current,
        )

    try:
        # Load SAM 3 model
        predictor = SAM3Predictor(sam_config)
        predictor.load()

        # Create batch processor
        processor = SAM3BatchProcessor(predictor, batch_config)

        total_detections = 0
        total_frames = 0

        # Process each registry
        for registry_path in registries:
            registry = FrameRegistry.from_extraction_result(registry_path)

            result = processor.process_registry(
                registry,
                object_classes,
                progress_callback=progress_callback,
            )

            total_detections += result.total_detections
            total_frames += result.processed_frames

            # Save results
            output_dir = registry_path.parent / "detections"
            processor.save_results(output_dir, include_masks=True)

            # Update registry
            registry.save()

        # Unload model
        predictor.unload()

        # Record stage duration for benchmarking
        stage_duration = time.time() - stage_start_time
        record_stage_completion(
            job_id=job_id,
            stage="segmentation",
            duration_seconds=stage_duration,
            total_frames=total_frames,
        )

        logger.info(
            f"Segmentation complete: {total_detections} detections in {total_frames} frames "
            f"({stage_duration:.1f}s, {total_frames / stage_duration:.2f} fps)"
        )

        return {
            "status": "completed",
            "total_frames": total_frames,
            "total_detections": total_detections,
            "registries": [str(p) for p in registries],
            "duration_seconds": stage_duration,
        }

    except Exception as e:
        logger.error(f"Segmentation failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
        }


@app.task(name="worker.tasks.segmentation.segment_single_frame")
def segment_single_frame(
    image_path: str,
    object_classes: list[dict],
    config: dict,
) -> dict[str, Any]:
    """
    Run segmentation on a single image.

    Args:
        image_path: Path to image file
        object_classes: Object class definitions
        config: SAM 3 configuration

    Returns:
        Detection results
    """
    import cv2

    from processing.sam3.predictor import SAM3Config, SAM3Predictor

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return {"status": "failed", "error": f"Failed to load image: {image_path}"}

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Configure and run SAM 3
    sam_config = SAM3Config(
        confidence_threshold=config.get("confidence_threshold", 0.5),
    )

    predictor = SAM3Predictor(sam_config)
    predictor.load()

    # Create prompts
    prompts = [
        {
            "class_id": c.get("id", "unknown"),
            "class_name": c.get("name", "Unknown"),
            "text": c.get("prompt", ""),
        }
        for c in object_classes
    ]

    result = predictor.predict(image, prompts, frame_id=Path(image_path).stem)
    predictor.unload()

    return {
        "status": "completed",
        "image_path": image_path,
        "detection_count": result.detection_count,
        "inference_time_ms": result.inference_time_ms,
        "detections": [
            {
                "class_id": d.class_id,
                "class_name": d.class_name,
                "confidence": d.confidence,
                "bbox": list(d.bbox),
                "area": d.area,
            }
            for d in result.detections
        ],
    }
