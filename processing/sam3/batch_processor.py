"""Batch processing for SAM 3 inference."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

import cv2
import numpy as np
import torch

from processing.sam3.predictor import Detection, SAM3Config, SAM3Predictor, SegmentationResult
from processing.svo2.frame_registry import FrameEntry, FrameRegistry

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 8
    num_workers: int = 4
    prefetch_factor: int = 2

    # Memory management
    clear_cache_every: int = 10  # Clear GPU cache every N batches
    max_memory_gb: float = 20.0  # Maximum GPU memory to use


@dataclass
class BatchResult:
    """Result from batch processing."""

    processed_frames: int
    total_detections: int
    failed_frames: int
    total_time_ms: float
    avg_time_per_frame_ms: float


class SAM3BatchProcessor:
    """
    Batch processor for efficient SAM 3 inference.

    Handles:
    - Batched GPU inference
    - Memory management
    - Progress tracking
    - Result aggregation
    """

    def __init__(
        self,
        predictor: SAM3Predictor,
        batch_config: BatchConfig | None = None,
    ):
        """
        Initialize batch processor.

        Args:
            predictor: SAM3Predictor instance
            batch_config: Batch processing configuration
        """
        self.predictor = predictor
        self.config = batch_config or BatchConfig()

        self._results: dict[str, SegmentationResult] = {}

    def process_registry(
        self,
        registry: FrameRegistry,
        object_classes: list[dict],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> BatchResult:
        """
        Process all frames in a registry.

        Args:
            registry: Frame registry with frames to process
            object_classes: Object classes to detect
            progress_callback: Optional callback(current, total, message)

        Returns:
            BatchResult with processing statistics
        """
        import time

        start_time = time.perf_counter()

        # Get pending frames
        frames = list(registry.get_pending_segmentation())
        total_frames = len(frames)

        if total_frames == 0:
            logger.info("No frames pending segmentation")
            return BatchResult(
                processed_frames=0,
                total_detections=0,
                failed_frames=0,
                total_time_ms=0,
                avg_time_per_frame_ms=0,
            )

        logger.info(f"Processing {total_frames} frames with batch size {self.config.batch_size}")

        processed = 0
        total_detections = 0
        failed = 0

        # Process in batches
        for batch_idx, batch in enumerate(self._batch_frames(frames)):
            if progress_callback:
                progress_callback(
                    processed,
                    total_frames,
                    f"Batch {batch_idx + 1}: {len(batch)} frames",
                )

            try:
                batch_results = self._process_batch(batch, registry, object_classes)

                for frame_id, result in batch_results.items():
                    self._results[frame_id] = result
                    registry.update_status(
                        frame_id,
                        segmentation_complete=True,
                        detection_count=result.detection_count,
                    )
                    total_detections += result.detection_count
                    processed += 1

            except Exception as e:
                logger.error(f"Batch {batch_idx} failed: {e}")
                failed += len(batch)
                # Clear cache on error to recover memory
                self._clear_gpu_cache()

            # Memory management - check periodically and when memory is high
            if batch_idx > 0 and batch_idx % self.config.clear_cache_every == 0:
                self._clear_gpu_cache()
            elif not self._check_gpu_memory():
                self._clear_gpu_cache()

        total_time_ms = (time.perf_counter() - start_time) * 1000

        return BatchResult(
            processed_frames=processed,
            total_detections=total_detections,
            failed_frames=failed,
            total_time_ms=total_time_ms,
            avg_time_per_frame_ms=total_time_ms / max(processed, 1),
        )

    def process_images(
        self,
        images: list[tuple[str, np.ndarray]],
        object_classes: list[dict],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, SegmentationResult]:
        """
        Process a list of images directly.

        Args:
            images: List of (frame_id, image) tuples
            object_classes: Object classes to detect
            progress_callback: Optional callback(current, total, message)

        Returns:
            Dictionary of frame_id -> SegmentationResult
        """
        results = {}

        for idx, (frame_id, image) in enumerate(images):
            if progress_callback:
                progress_callback(idx, len(images), f"Frame {frame_id}")

            try:
                prompts = self._create_prompts(object_classes)
                result = self.predictor.predict(image, prompts, frame_id)
                results[frame_id] = result

            except Exception as e:
                logger.error(f"Failed to process frame {frame_id}: {e}")
                results[frame_id] = SegmentationResult(frame_id=frame_id)

        return results

    def _batch_frames(
        self,
        frames: list[FrameEntry],
    ) -> Iterator[list[FrameEntry]]:
        """Yield batches of frames."""
        for i in range(0, len(frames), self.config.batch_size):
            yield frames[i : i + self.config.batch_size]

    def _process_batch(
        self,
        batch: list[FrameEntry],
        registry: FrameRegistry,
        object_classes: list[dict],
    ) -> dict[str, SegmentationResult]:
        """Process a batch of frames with memory-efficient image handling."""
        results = {}
        prompts = self._create_prompts(object_classes)

        # Process images one at a time to minimize memory footprint
        for frame in batch:
            image = None
            try:
                paths = registry.get_frame_paths(frame.frame_id)
                image_path = paths.get("image_left")

                if image_path is None or not image_path.exists():
                    logger.warning(f"Image not found for frame {frame.frame_id}")
                    results[frame.frame_id] = SegmentationResult(frame_id=frame.frame_id)
                    continue

                image = cv2.imread(str(image_path))
                if image is None:
                    logger.warning(f"Failed to load image: {image_path}")
                    results[frame.frame_id] = SegmentationResult(frame_id=frame.frame_id)
                    continue

                # Convert BGR to RGB
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                # Run inference
                result = self.predictor.predict(image, prompts, frame.frame_id)
                results[frame.frame_id] = result

            except Exception as e:
                logger.error(f"Inference failed for {frame.frame_id}: {e}")
                results[frame.frame_id] = SegmentationResult(frame_id=frame.frame_id)

            finally:
                # Explicit cleanup to release memory immediately
                del image

        # Clear GPU cache after each batch for better memory management
        self._clear_gpu_cache()

        return results

    def _create_prompts(self, object_classes: list[dict]) -> list[dict]:
        """Create prompts from object class definitions."""
        prompts = []

        for obj_class in object_classes:
            # Support both key naming conventions (class_id/id, class_name/name)
            prompt = {
                "class_id": obj_class.get("class_id") or obj_class.get("id", "unknown"),
                "class_name": obj_class.get("class_name") or obj_class.get("name", "Unknown"),
            }

            # Add text prompt if available (check both "text" and "prompt" keys)
            text_prompt = obj_class.get("text") or obj_class.get("prompt")
            if text_prompt:
                prompt["text"] = text_prompt

            # Add box prompt if available
            if "box" in obj_class:
                prompt["box"] = obj_class["box"]

            # Add point prompt if available
            if "points" in obj_class:
                prompt["points"] = obj_class["points"]
                prompt["point_labels"] = obj_class.get("point_labels", [1] * len(obj_class["points"]))

            prompts.append(prompt)

        return prompts

    def _clear_gpu_cache(self) -> None:
        """Clear GPU memory cache."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.debug("Cleared GPU cache")

    def _check_gpu_memory(self) -> bool:
        """
        Check if GPU memory usage is within limits.

        Returns:
            True if memory is within limits, False if we should clear cache
        """
        if not torch.cuda.is_available():
            return True

        # Get current GPU memory usage in GB
        allocated_gb = torch.cuda.memory_allocated() / (1024 ** 3)
        max_allowed = self.config.max_memory_gb

        if allocated_gb > max_allowed * 0.9:  # 90% threshold
            logger.warning(f"GPU memory usage high: {allocated_gb:.2f}GB / {max_allowed}GB")
            return False

        return True

    def get_results(self) -> dict[str, SegmentationResult]:
        """Get all processing results."""
        return self._results.copy()

    def get_result(self, frame_id: str) -> SegmentationResult | None:
        """Get result for a specific frame."""
        return self._results.get(frame_id)

    def save_results(
        self,
        output_dir: Path,
        include_masks: bool = False,
    ) -> Path:
        """
        Save results to disk.

        Args:
            output_dir: Output directory
            include_masks: Whether to save mask images

        Returns:
            Path to results file
        """
        import json

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save detections as JSON
        detections_file = output_dir / "detections.json"

        data = {
            "total_frames": len(self._results),
            "total_detections": sum(r.detection_count for r in self._results.values()),
            "frames": {},
        }

        for frame_id, result in self._results.items():
            frame_data = {
                "detection_count": result.detection_count,
                "inference_time_ms": result.inference_time_ms,
                "detections": [],
            }

            for det in result.detections:
                det_data = {
                    "class_id": det.class_id,
                    "class_name": det.class_name,
                    "confidence": det.confidence,
                    "bbox": list(det.bbox),
                    "area": det.area,
                    "centroid": list(det.centroid),
                }
                frame_data["detections"].append(det_data)

            data["frames"][frame_id] = frame_data

        with open(detections_file, "w") as f:
            json.dump(data, f, indent=2)

        # Save masks if requested
        if include_masks:
            masks_dir = output_dir / "masks"
            masks_dir.mkdir(exist_ok=True)

            for frame_id, result in self._results.items():
                for idx, det in enumerate(result.detections):
                    mask_file = masks_dir / f"{frame_id}_{idx:03d}.png"
                    mask_uint8 = (det.mask * 255).astype(np.uint8)
                    cv2.imwrite(str(mask_file), mask_uint8)

        logger.info(f"Saved results to {output_dir}")
        return detections_file

    def clear_results(self) -> None:
        """Clear all cached results."""
        self._results.clear()
        self._clear_gpu_cache()
