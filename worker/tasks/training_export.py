"""Training dataset export task."""

import json
import logging
import os
import random
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from worker.celery_app import app
from worker.db import get_db_connection

logger = logging.getLogger(__name__)

# Base output directory for training datasets
TRAINING_OUTPUT_DIR = Path(
    os.getenv("TRAINING_OUTPUT_DIR", "/home/atlas/dev/pipe1/data/training_datasets")
)


def update_training_dataset_progress(
    dataset_id: str,
    progress: float,
    status: str | None = None,
    **kwargs,
) -> bool:
    """Update training dataset progress in database."""
    try:
        with get_db_connection() as conn:
            params = {
                "dataset_id": dataset_id,
                "progress": progress,
                "updated_at": datetime.now(timezone.utc),
            }

            set_clauses = [
                "progress = :progress",
                "updated_at = :updated_at",
            ]

            if status:
                set_clauses.append("status = :status")
                params["status"] = status

            for key, value in kwargs.items():
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

            sql = f"""
                UPDATE training_datasets
                SET {', '.join(set_clauses)}
                WHERE id = :dataset_id
            """

            result = conn.execute(text(sql), params)
            conn.commit()
            return result.rowcount > 0

    except Exception as e:
        logger.error(f"Failed to update training dataset progress: {e}")
        return False


def get_job_frames(job_id: str) -> list[dict]:
    """Get all frames for a job from the data files."""
    job_output_dir = Path(f"/home/atlas/dev/pipe1/data/output/{job_id}")
    frames = []

    if not job_output_dir.exists():
        return frames

    # Find all sequence directories
    for seq_dir in job_output_dir.iterdir():
        if not seq_dir.is_dir():
            continue

        # Load frame registry
        registry_path = seq_dir / "frame_registry.json"
        if not registry_path.exists():
            continue

        with open(registry_path) as f:
            registry = json.load(f)

        # Load detections
        detections_path = seq_dir / "detections" / "detections.json"
        detections_data = {}
        if detections_path.exists():
            with open(detections_path) as f:
                det_json = json.load(f)
                detections_data = det_json.get("frames", {})

        for frame_info in registry.get("frames", []):
            frame_id = frame_info.get("frame_id", "")

            # Build frame data
            frame_data = {
                "frame_id": frame_id,
                "sequence_dir": str(seq_dir),
                "svo2_frame_index": frame_info.get("svo2_frame_index", 0),
                "image_left": str(seq_dir / frame_info.get("image_left", "")),
                "image_right": str(seq_dir / frame_info.get("image_right", "")) if frame_info.get("image_right") else None,
                "depth": str(seq_dir / frame_info.get("depth", "")) if frame_info.get("depth") else None,
                "annotations": [],
            }

            # Get annotations for this frame
            frame_detections = detections_data.get(frame_id, {})
            for i, det in enumerate(frame_detections.get("detections", [])):
                bbox = det.get("bbox", [0, 0, 0, 0])
                annotation = {
                    "id": f"{frame_id}_{i}",
                    "class_name": det.get("class_name", "unknown"),
                    "confidence": det.get("confidence", 0.0),
                    "bbox": bbox,  # [x1, y1, x2, y2]
                    "mask_path": str(seq_dir / "detections" / "masks" / f"{frame_id}_{i:03d}.png"),
                }
                frame_data["annotations"].append(annotation)

            frames.append(frame_data)

    return frames


def filter_frames(
    frames: list[dict],
    filter_config: dict,
) -> list[dict]:
    """Apply filters to frames and annotations."""
    excluded_classes = set(filter_config.get("excluded_classes", []))
    excluded_annotation_ids = set(filter_config.get("excluded_annotation_ids", []))
    excluded_frame_indices = set(filter_config.get("excluded_frame_indices", []))

    filtered_frames = []

    for i, frame in enumerate(frames):
        # Skip excluded frame indices
        if i in excluded_frame_indices:
            continue

        # Filter annotations
        filtered_annotations = []
        for ann in frame.get("annotations", []):
            # Skip excluded classes
            if ann["class_name"] in excluded_classes:
                continue
            # Skip individually excluded annotations
            if ann["id"] in excluded_annotation_ids:
                continue
            filtered_annotations.append(ann)

        # Include frame if it has any annotations after filtering
        # (or if we want to include empty frames)
        if filtered_annotations:
            frame_copy = frame.copy()
            frame_copy["annotations"] = filtered_annotations
            filtered_frames.append(frame_copy)

    return filtered_frames


def split_frames(
    frames: list[dict],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    shuffle_seed: int | None,
) -> dict[str, list[dict]]:
    """Split frames into train/val/test sets."""
    if shuffle_seed is not None:
        random.seed(shuffle_seed)
        frames = frames.copy()
        random.shuffle(frames)

    total = len(frames)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    return {
        "train": frames[:train_end],
        "val": frames[train_end:val_end],
        "test": frames[val_end:],
    }


def export_kitti_format(
    frames: list[dict],
    output_dir: Path,
    split: str,
    include_masks: bool,
    include_depth: bool,
) -> int:
    """Export frames in KITTI format."""
    # Create KITTI directory structure
    image_dir = output_dir / "kitti" / split / "image_2"
    label_dir = output_dir / "kitti" / split / "label_2"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    if include_depth:
        depth_dir = output_dir / "kitti" / split / "depth"
        depth_dir.mkdir(parents=True, exist_ok=True)

    if include_masks:
        mask_dir = output_dir / "kitti" / split / "masks"
        mask_dir.mkdir(parents=True, exist_ok=True)

    annotation_count = 0

    for i, frame in enumerate(frames):
        frame_name = f"{i:06d}"

        # Copy image
        src_image = Path(frame["image_left"])
        if src_image.exists():
            shutil.copy2(src_image, image_dir / f"{frame_name}.png")

        # Copy depth if requested
        if include_depth and frame.get("depth"):
            src_depth = Path(frame["depth"])
            if src_depth.exists():
                shutil.copy2(src_depth, depth_dir / f"{frame_name}.png")

        # Write KITTI format labels
        labels = []
        for j, ann in enumerate(frame.get("annotations", [])):
            bbox = ann["bbox"]  # [x1, y1, x2, y2]
            class_name = ann["class_name"]

            # KITTI format: type truncated occluded alpha bbox_left bbox_top bbox_right bbox_bottom h w l x y z ry
            # We only have 2D data, so fill placeholders for 3D
            kitti_line = (
                f"{class_name} 0.0 0 0.0 "
                f"{bbox[0]:.2f} {bbox[1]:.2f} {bbox[2]:.2f} {bbox[3]:.2f} "
                f"0.0 0.0 0.0 0.0 0.0 0.0 0.0"
            )
            labels.append(kitti_line)
            annotation_count += 1

            # Copy mask if requested
            if include_masks:
                mask_path = Path(ann.get("mask_path", ""))
                if mask_path.exists():
                    shutil.copy2(mask_path, mask_dir / f"{frame_name}_{j:03d}.png")

        # Write label file
        with open(label_dir / f"{frame_name}.txt", "w") as f:
            f.write("\n".join(labels))

    return annotation_count


def export_coco_format(
    frames: list[dict],
    output_dir: Path,
    split: str,
    include_masks: bool,
) -> int:
    """Export frames in COCO format."""
    # Create COCO directory structure
    image_dir = output_dir / "coco" / split / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    if include_masks:
        mask_dir = output_dir / "coco" / split / "masks"
        mask_dir.mkdir(parents=True, exist_ok=True)

    # Build COCO annotation structure
    coco_data = {
        "info": {
            "description": f"Pipeline One Training Dataset - {split}",
            "version": "1.0",
            "year": datetime.now().year,
            "date_created": datetime.now().isoformat(),
        },
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": [],
    }

    # Track categories
    category_map = {}
    category_id = 1

    annotation_id = 1

    for i, frame in enumerate(frames):
        frame_name = f"{i:06d}"

        # Copy image
        src_image = Path(frame["image_left"])
        if src_image.exists():
            shutil.copy2(src_image, image_dir / f"{frame_name}.png")

            # Add image entry
            from PIL import Image

            with Image.open(src_image) as img:
                width, height = img.size

            coco_data["images"].append({
                "id": i + 1,
                "file_name": f"{frame_name}.png",
                "width": width,
                "height": height,
            })

        # Add annotations
        for j, ann in enumerate(frame.get("annotations", [])):
            class_name = ann["class_name"]

            # Add category if new
            if class_name not in category_map:
                category_map[class_name] = category_id
                coco_data["categories"].append({
                    "id": category_id,
                    "name": class_name,
                    "supercategory": "object",
                })
                category_id += 1

            bbox = ann["bbox"]  # [x1, y1, x2, y2]
            # COCO bbox format: [x, y, width, height]
            coco_bbox = [
                bbox[0],
                bbox[1],
                bbox[2] - bbox[0],
                bbox[3] - bbox[1],
            ]

            coco_data["annotations"].append({
                "id": annotation_id,
                "image_id": i + 1,
                "category_id": category_map[class_name],
                "bbox": coco_bbox,
                "area": coco_bbox[2] * coco_bbox[3],
                "iscrowd": 0,
            })
            annotation_id += 1

            # Copy mask if requested
            if include_masks:
                mask_path = Path(ann.get("mask_path", ""))
                if mask_path.exists():
                    shutil.copy2(mask_path, mask_dir / f"{frame_name}_{j:03d}.png")

    # Write COCO JSON
    ann_file = output_dir / "coco" / split / "annotations.json"
    with open(ann_file, "w") as f:
        json.dump(coco_data, f, indent=2)

    return annotation_id - 1


def get_directory_size(path: Path) -> int:
    """Calculate total size of a directory."""
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


@app.task(bind=True, name="worker.tasks.training_export.export_training_dataset")
def export_training_dataset(
    self,
    training_dataset_id: str,
    job_id: str,
    format: str,
    filter_config: dict,
    split_config: dict,
) -> dict[str, Any]:
    """
    Export filtered training dataset in KITTI and/or COCO format.

    Args:
        training_dataset_id: UUID of the TrainingDataset record
        job_id: Source processing job UUID
        format: Export format ("kitti", "coco", "both")
        filter_config: Filter configuration dict
        split_config: Split configuration dict

    Returns:
        Export statistics dict
    """
    logger.info(f"Starting training dataset export: {training_dataset_id}")

    try:
        # Update status to processing
        update_training_dataset_progress(
            training_dataset_id,
            progress=0.0,
            status="processing",
        )

        # Create output directory
        output_dir = TRAINING_OUTPUT_DIR / training_dataset_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load frames from job
        update_training_dataset_progress(training_dataset_id, progress=5.0)
        all_frames = get_job_frames(job_id)

        if not all_frames:
            raise ValueError(f"No frames found for job {job_id}")

        # Apply filters
        update_training_dataset_progress(training_dataset_id, progress=10.0)
        filtered_frames = filter_frames(all_frames, filter_config)

        if not filtered_frames:
            raise ValueError("No frames remaining after filtering")

        # Split into train/val/test
        update_training_dataset_progress(training_dataset_id, progress=15.0)
        splits = split_frames(
            filtered_frames,
            split_config["train_ratio"],
            split_config["val_ratio"],
            split_config["test_ratio"],
            split_config.get("shuffle_seed"),
        )

        # Export in requested format(s)
        include_masks = split_config.get("include_masks", True)
        include_depth = split_config.get("include_depth", True)

        total_annotations = 0
        kitti_path = None
        coco_path = None

        if format in ("kitti", "both"):
            update_training_dataset_progress(training_dataset_id, progress=20.0)
            for split_name, split_frames in splits.items():
                progress_offset = {"train": 20, "val": 40, "test": 50}[split_name]
                update_training_dataset_progress(
                    training_dataset_id, progress=float(progress_offset)
                )
                export_kitti_format(
                    split_frames,
                    output_dir,
                    split_name,
                    include_masks,
                    include_depth,
                )
            kitti_path = str(output_dir / "kitti")

        if format in ("coco", "both"):
            update_training_dataset_progress(training_dataset_id, progress=55.0)
            for split_name, split_frames in splits.items():
                progress_offset = {"train": 55, "val": 70, "test": 80}[split_name]
                update_training_dataset_progress(
                    training_dataset_id, progress=float(progress_offset)
                )
                ann_count = export_coco_format(
                    split_frames,
                    output_dir,
                    split_name,
                    include_masks,
                )
                total_annotations += ann_count
            coco_path = str(output_dir / "coco")

        # Calculate total annotations
        for split_frames in splits.values():
            for frame in split_frames:
                total_annotations += len(frame.get("annotations", []))

        # Calculate file size
        file_size = get_directory_size(output_dir)

        # Save lineage metadata
        lineage_file = output_dir / "lineage.json"
        lineage_data = {
            "training_dataset_id": training_dataset_id,
            "source_job_id": job_id,
            "filter_config": filter_config,
            "split_config": split_config,
            "format": format,
            "statistics": {
                "total_frames": len(filtered_frames),
                "total_annotations": total_annotations,
                "train_count": len(splits["train"]),
                "val_count": len(splits["val"]),
                "test_count": len(splits["test"]),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(lineage_file, "w") as f:
            json.dump(lineage_data, f, indent=2)

        # Update database with final statistics
        with get_db_connection() as conn:
            sql = """
                UPDATE training_datasets
                SET status = 'complete',
                    progress = 100.0,
                    total_frames = :total_frames,
                    total_annotations = :total_annotations,
                    train_count = :train_count,
                    val_count = :val_count,
                    test_count = :test_count,
                    output_directory = :output_directory,
                    kitti_path = :kitti_path,
                    coco_path = :coco_path,
                    file_size_bytes = :file_size_bytes,
                    completed_at = :completed_at,
                    updated_at = :updated_at
                WHERE id = :dataset_id
            """
            conn.execute(
                text(sql),
                {
                    "dataset_id": training_dataset_id,
                    "total_frames": len(filtered_frames),
                    "total_annotations": total_annotations,
                    "train_count": len(splits["train"]),
                    "val_count": len(splits["val"]),
                    "test_count": len(splits["test"]),
                    "output_directory": str(output_dir),
                    "kitti_path": kitti_path,
                    "coco_path": coco_path,
                    "file_size_bytes": file_size,
                    "completed_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            conn.commit()

        logger.info(f"Training dataset export complete: {training_dataset_id}")

        return {
            "status": "complete",
            "total_frames": len(filtered_frames),
            "total_annotations": total_annotations,
            "train_count": len(splits["train"]),
            "val_count": len(splits["val"]),
            "test_count": len(splits["test"]),
            "output_directory": str(output_dir),
        }

    except Exception as e:
        logger.error(f"Training dataset export failed: {e}")

        # Update database with error
        with get_db_connection() as conn:
            conn.execute(
                text("""
                    UPDATE training_datasets
                    SET status = 'failed',
                        error_message = :error_message,
                        updated_at = :updated_at
                    WHERE id = :dataset_id
                """),
                {
                    "dataset_id": training_dataset_id,
                    "error_message": str(e),
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            conn.commit()

        raise
