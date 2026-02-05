"""SAM 3 model predictor for text-prompt segmentation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import torch

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Check for SAM 3 availability
try:
    from sam3.model.sam3_image_processor import Sam3Processor
    from sam3.model_builder import build_sam3_image_model
    SAM3_AVAILABLE = True
except ImportError:
    SAM3_AVAILABLE = False
    logger.warning("SAM 3 not available - install with: pip install /home/atlas/dev/sam3")


@dataclass
class Detection:
    """Single object detection result."""

    # 2D bounding box (x1, y1, x2, y2)
    bbox: tuple[float, float, float, float]

    # Segmentation mask (H x W, boolean)
    mask: NDArray[np.bool_]

    # Detection confidence
    confidence: float

    # Class information
    class_id: str
    class_name: str

    # Mask area
    area: int = 0

    # Centroid (x, y)
    centroid: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self):
        """Calculate derived properties."""
        if self.area == 0:
            self.area = int(np.sum(self.mask))

        if self.centroid == (0.0, 0.0):
            ys, xs = np.where(self.mask)
            if len(xs) > 0:
                self.centroid = (float(np.mean(xs)), float(np.mean(ys)))


@dataclass
class SegmentationResult:
    """Result from SAM 3 segmentation."""

    frame_id: str
    detections: list[Detection] = field(default_factory=list)
    inference_time_ms: float = 0.0

    @property
    def detection_count(self) -> int:
        """Get number of detections."""
        return len(self.detections)

    def filter_by_confidence(self, threshold: float) -> list[Detection]:
        """Get detections above confidence threshold."""
        return [d for d in self.detections if d.confidence >= threshold]

    def filter_by_class(self, class_ids: list[str]) -> list[Detection]:
        """Get detections of specific classes."""
        return [d for d in self.detections if d.class_id in class_ids]


@dataclass
class SAM3Config:
    """Configuration for SAM 3 inference."""

    # Model path (for HuggingFace downloaded checkpoints)
    model_path: Path | None = None

    # Inference parameters
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.7
    mask_threshold: float = 0.5
    max_detections: int = 100

    # GPU settings
    device: str = "cuda"
    precision: str = "fp16"  # fp32, fp16, bf16


class SAM3Predictor:
    """
    Wrapper for SAM 3 model inference.

    Supports native text-prompt based segmentation for detecting
    objects using open-vocabulary concepts (270K+ concepts).
    """

    def __init__(self, config: SAM3Config | None = None):
        """
        Initialize SAM 3 predictor.

        Args:
            config: Model configuration
        """
        self.config = config or SAM3Config()
        self._model = None
        self._processor = None
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded

    def load(self) -> None:
        """Load the SAM 3 model."""
        if self._is_loaded:
            return

        if not SAM3_AVAILABLE:
            logger.warning("SAM 3 not available - running in stub mode")
            self._is_loaded = True
            return

        logger.info("Loading SAM 3 model...")

        # Set device
        device = torch.device(self.config.device if torch.cuda.is_available() else "cpu")

        # Build SAM 3 model - this downloads from HuggingFace if needed
        self._model = build_sam3_image_model()

        # Create processor
        self._processor = Sam3Processor(self._model)

        self._is_loaded = True
        logger.info(f"SAM 3 model loaded on {device}")

    def unload(self) -> None:
        """Unload the model to free GPU memory."""
        if not self._is_loaded:
            return

        self._model = None
        self._processor = None
        self._is_loaded = False

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("SAM 3 model unloaded")

    def predict(
        self,
        image: NDArray[np.uint8],
        prompts: list[dict],
        frame_id: str = "",
    ) -> SegmentationResult:
        """
        Run segmentation on an image with text prompts.

        SAM 3 supports native open-vocabulary text prompts for 270K+ concepts.

        Args:
            image: RGB image (H x W x 3, uint8)
            prompts: List of prompts, each with keys:
                - class_id: Unique class identifier
                - class_name: Human-readable class name
                - text: Text prompt for the class (SAM 3 native support)
                - points: Optional point prompts [(x, y), ...]
                - box: Optional box prompt [x1, y1, x2, y2]
            frame_id: Optional frame identifier

        Returns:
            SegmentationResult with detections
        """
        if not self._is_loaded:
            raise RuntimeError("Model not loaded - call load() first")

        result = SegmentationResult(frame_id=frame_id)

        if not SAM3_AVAILABLE or self._processor is None:
            # Stub mode - return empty result
            return result

        import time

        from PIL import Image
        start_time = time.perf_counter()

        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(image)

        # Set image in processor
        inference_state = self._processor.set_image(pil_image)

        all_detections = []

        for prompt in prompts:
            class_id = prompt["class_id"]
            class_name = prompt["class_name"]

            try:
                # SAM 3 native text prompt support
                if "text" in prompt:
                    output = self._processor.set_text_prompt(
                        state=inference_state,
                        prompt=prompt["text"],
                    )

                    masks = output.get("masks", [])
                    boxes = output.get("boxes", [])
                    scores = output.get("scores", [])

                    # Process each detection
                    for _idx, (mask, box, score) in enumerate(zip(masks, boxes, scores, strict=False)):
                        if score < self.config.confidence_threshold:
                            continue

                        # Convert mask to numpy boolean array
                        if torch.is_tensor(mask):
                            mask_np = mask.cpu().numpy().astype(bool)
                        else:
                            mask_np = np.array(mask).astype(bool)

                        # Handle multi-dimensional masks
                        if mask_np.ndim > 2:
                            mask_np = mask_np.squeeze()

                        # Skip empty masks
                        if not np.any(mask_np):
                            continue

                        # Convert box to tuple
                        if torch.is_tensor(box):
                            box = box.cpu().numpy()
                        bbox = (
                            float(box[0]),
                            float(box[1]),
                            float(box[2]),
                            float(box[3]),
                        )

                        detection = Detection(
                            bbox=bbox,
                            mask=mask_np,
                            confidence=float(score),
                            class_id=class_id,
                            class_name=class_name,
                        )
                        all_detections.append(detection)

                # Point prompt fallback
                elif "points" in prompt:
                    output = self._processor.set_point_prompt(
                        state=inference_state,
                        points=prompt["points"],
                        labels=prompt.get("point_labels", [1] * len(prompt["points"])),
                    )
                    self._process_output(output, class_id, class_name, all_detections)

                # Box prompt fallback
                elif "box" in prompt:
                    output = self._processor.set_box_prompt(
                        state=inference_state,
                        box=prompt["box"],
                    )
                    self._process_output(output, class_id, class_name, all_detections)

            except Exception as e:
                logger.warning(f"Failed to process prompt {prompt}: {e}")
                continue

        # Apply NMS
        all_detections = self._apply_nms(all_detections)

        # Limit detections
        all_detections = sorted(
            all_detections,
            key=lambda d: d.confidence,
            reverse=True,
        )[:self.config.max_detections]

        result.detections = all_detections
        result.inference_time_ms = (time.perf_counter() - start_time) * 1000

        return result

    def _process_output(
        self,
        output: dict,
        class_id: str,
        class_name: str,
        detections: list[Detection],
    ) -> None:
        """Process SAM 3 output and add to detections list."""
        masks = output.get("masks", [])
        boxes = output.get("boxes", [])
        scores = output.get("scores", [])

        for mask, box, score in zip(masks, boxes, scores, strict=False):
            if score < self.config.confidence_threshold:
                continue

            if torch.is_tensor(mask):
                mask_np = mask.cpu().numpy().astype(bool)
            else:
                mask_np = np.array(mask).astype(bool)

            if mask_np.ndim > 2:
                mask_np = mask_np.squeeze()

            if not np.any(mask_np):
                continue

            if torch.is_tensor(box):
                box = box.cpu().numpy()

            detection = Detection(
                bbox=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                mask=mask_np,
                confidence=float(score),
                class_id=class_id,
                class_name=class_name,
            )
            detections.append(detection)

    def predict_with_text(
        self,
        image: NDArray[np.uint8],
        text_prompt: str,
        class_id: str = "detected",
        class_name: str = "Detected Object",
        frame_id: str = "",
    ) -> SegmentationResult:
        """
        Simplified text-only prediction.

        Args:
            image: RGB image (H x W x 3, uint8)
            text_prompt: Open-vocabulary text prompt (e.g., "car", "person in red shirt")
            class_id: Class identifier for detected objects
            class_name: Human-readable class name
            frame_id: Optional frame identifier

        Returns:
            SegmentationResult with detections
        """
        return self.predict(
            image=image,
            prompts=[{
                "class_id": class_id,
                "class_name": class_name,
                "text": text_prompt,
            }],
            frame_id=frame_id,
        )

    def _apply_nms(self, detections: list[Detection]) -> list[Detection]:
        """Apply Non-Maximum Suppression to detections."""
        if len(detections) <= 1:
            return detections

        # Sort by confidence
        detections = sorted(detections, key=lambda d: d.confidence, reverse=True)

        keep = []
        used = set()

        for i, det in enumerate(detections):
            if i in used:
                continue

            keep.append(det)

            for j in range(i + 1, len(detections)):
                if j in used:
                    continue

                # Calculate IoU
                iou = self._calculate_mask_iou(det.mask, detections[j].mask)
                if iou > self.config.iou_threshold:
                    used.add(j)

        return keep

    def _calculate_mask_iou(
        self,
        mask1: NDArray[np.bool_],
        mask2: NDArray[np.bool_],
    ) -> float:
        """Calculate Intersection over Union for two masks."""
        intersection = np.logical_and(mask1, mask2).sum()
        union = np.logical_or(mask1, mask2).sum()

        if union == 0:
            return 0.0

        return float(intersection / union)

    def get_gpu_memory_usage(self) -> dict:
        """Get current GPU memory usage."""
        if not torch.cuda.is_available():
            return {"available": False}

        return {
            "available": True,
            "allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
            "reserved_mb": torch.cuda.memory_reserved() / (1024 * 1024),
            "max_allocated_mb": torch.cuda.max_memory_allocated() / (1024 * 1024),
        }
