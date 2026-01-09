"""3D reconstruction task."""

import json
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="worker.tasks.reconstruction.run_reconstruction")
def run_reconstruction(
    self,
    segmentation_result: dict | None,
    job_id: str,
    config: dict,
) -> dict[str, Any]:
    """
    Run 3D bounding box reconstruction.

    Args:
        segmentation_result: Results from segmentation stage
        job_id: Processing job UUID
        config: Reconstruction configuration

    Returns:
        Reconstruction result summary
    """
    from processing.reconstruction.bbox_estimator import BBox3DEstimator, BBoxMethod
    from processing.reconstruction.depth_projection import CameraIntrinsics, DepthProjector
    from processing.svo2.frame_registry import FrameRegistry

    logger.info(f"Running reconstruction for job {job_id}")

    if segmentation_result is None:
        return {"status": "skipped", "reason": "No segmentation results"}

    registries = segmentation_result.get("registries", [])
    if not registries:
        return {"status": "skipped", "reason": "No registries to process"}

    # Configuration
    min_points = config.get("min_points", 100)
    method = BBoxMethod(config.get("method", "pca"))
    use_size_priors = config.get("use_size_priors", True)

    # Progress callback
    def progress_callback(current: int, total: int, message: str) -> None:
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": "reconstruction",
                "current": current,
                "total": total,
                "message": message,
            },
        )

    try:
        # Create bbox estimator
        estimator = BBox3DEstimator(
            method=method,
            min_points=min_points,
            use_size_priors=use_size_priors,
        )

        total_objects = 0
        total_frames = 0

        for registry_path in registries:
            registry_path = Path(registry_path)
            registry = FrameRegistry.from_extraction_result(registry_path)

            # Load calibration
            calib_file = registry_path.parent / "calib" / "calibration.json"
            if calib_file.exists():
                with open(calib_file) as f:
                    calib = json.load(f)
                intrinsics = CameraIntrinsics.from_calibration(calib["left"])
            else:
                logger.warning(f"Calibration not found: {calib_file}")
                continue

            # Load detections
            detections_file = registry_path.parent / "detections" / "detections.json"
            if not detections_file.exists():
                logger.warning(f"Detections not found: {detections_file}")
                continue

            with open(detections_file) as f:
                detections_data = json.load(f)

            projector = DepthProjector(intrinsics)

            # Process each frame
            frames = list(registry.iter_frames())
            for idx, frame in enumerate(frames):
                progress_callback(idx, len(frames), f"Frame {frame.frame_id}")

                # Get frame paths
                paths = registry.get_frame_paths(frame.frame_id)
                depth_path = paths.get("depth")

                if depth_path is None or not depth_path.exists():
                    continue

                # Load depth map
                depth = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
                if depth is None:
                    continue

                # Convert from mm to meters if 16-bit
                if depth.dtype == np.uint16:
                    depth = depth.astype(np.float32) / 1000.0

                # Get frame detections
                frame_dets = detections_data.get("frames", {}).get(frame.frame_id, {})
                frame_detections = frame_dets.get("detections", [])

                # Load masks
                masks_dir = registry_path.parent / "detections" / "masks"
                bboxes_3d = []

                for det_idx, det in enumerate(frame_detections):
                    # Load mask
                    mask_file = masks_dir / f"{frame.frame_id}_{det_idx:03d}.png"
                    if mask_file.exists():
                        mask = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
                        mask = mask > 127
                    else:
                        # Create mask from bbox
                        bbox = det["bbox"]
                        mask = np.zeros(depth.shape[:2], dtype=bool)
                        x1, y1, x2, y2 = map(int, bbox)
                        mask[y1:y2, x1:x2] = True

                    # Project to 3D
                    points = projector.project_depth_to_3d(depth, mask)
                    if len(points) < min_points:
                        continue

                    # Transform to KITTI coordinates
                    points = DepthProjector.transform_camera_to_kitti(points)

                    # Estimate bounding box
                    bbox_3d = estimator.estimate(
                        points,
                        class_id=det.get("class_id", ""),
                        class_name=det.get("class_name", ""),
                        confidence=det.get("confidence", 1.0),
                    )

                    if bbox_3d is not None:
                        bboxes_3d.append(bbox_3d.to_kitti_format())
                        total_objects += 1

                # Save 3D bounding boxes
                if bboxes_3d:
                    bbox_file = registry_path.parent / "label_2" / f"{frame.sequence_index:06d}.txt"
                    bbox_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(bbox_file, "w") as f:
                        for bbox in bboxes_3d:
                            # Write KITTI format
                            dims = bbox["dimensions"]
                            loc = bbox["location"]
                            f.write(
                                f"{bbox['type']} "
                                f"{bbox['truncated']:.2f} {bbox['occluded']} "
                                f"{bbox['alpha']:.2f} "
                                f"-1 -1 -1 -1 "  # 2D bbox placeholder
                                f"{dims[0]:.2f} {dims[1]:.2f} {dims[2]:.2f} "
                                f"{loc[0]:.2f} {loc[1]:.2f} {loc[2]:.2f} "
                                f"{bbox['rotation_y']:.2f}\n"
                            )

                # Update registry
                registry.update_status(
                    frame.frame_id,
                    reconstruction_complete=True,
                )

                total_frames += 1

            registry.save()

        logger.info(f"Reconstruction complete: {total_objects} 3D objects in {total_frames} frames")

        return {
            "status": "completed",
            "total_frames": total_frames,
            "total_objects": total_objects,
        }

    except Exception as e:
        logger.error(f"Reconstruction failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
        }
