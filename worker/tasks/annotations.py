"""Annotation processing and training data export tasks."""

import json
import logging
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from worker.celery_app import app
from worker.db import get_db_engine

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    name="worker.tasks.annotations.export_training_data",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(IOError, OSError),
    retry_backoff=True,
)
def export_training_data(
    self,
    dataset_id: str,
    output_directory: str | None = None,
    format: str = "both",  # "tfrecord", "coco", or "both"
    split_ratio: list[float] | None = None,
    include_unmatched: bool = False,
    labels_filter: list[str] | None = None,
    shuffle_seed: int | None = 42,
) -> dict[str, Any]:
    """
    Export training data in TFRecord and/or COCO format.

    Args:
        dataset_id: Dataset UUID
        output_directory: Output directory (default: data/output/{dataset_id}/training)
        format: Export format ("tfrecord", "coco", or "both")
        split_ratio: Train/val/test split ratios (default: [0.7, 0.2, 0.1])
        include_unmatched: Include unmatched annotations
        labels_filter: Only export specific labels
        shuffle_seed: Random seed for shuffling

    Returns:
        Export result statistics
    """
    from backend.app.models.external_annotation import ExternalAnnotation
    from backend.app.models.frame import Frame, FrameMetadata
    from backend.app.models.job import ProcessingJob

    logger.info(f"Exporting training data for dataset: {dataset_id}")

    split_ratio = split_ratio or [0.7, 0.2, 0.1]

    # Set output directory
    output_dir = Path(output_directory or f"data/output/{dataset_id}/training")
    output_dir.mkdir(parents=True, exist_ok=True)

    engine = get_db_engine()

    # Get all frames with annotations for this dataset
    with engine.connect() as conn:
        # Get frames from jobs linked to this dataset
        frames_query = (
            select(Frame)
            .join(ProcessingJob)
            .where(ProcessingJob.dataset_id == UUID(dataset_id))
        )
        frames_result = conn.execute(frames_query)
        frames = {str(f.id): f for f in frames_result.fetchall()}

        # Get frame metadata for dimensions
        frame_ids_list = list(frames.keys())
        frame_metadata: dict[str, tuple[int, int]] = {}
        if frame_ids_list:
            metadata_query = select(FrameMetadata).where(
                FrameMetadata.frame_id.in_([UUID(fid) for fid in frame_ids_list])
            )
            metadata_result = conn.execute(metadata_query)
            for meta in metadata_result.fetchall():
                if meta.image_width and meta.image_height:
                    frame_metadata[str(meta.frame_id)] = (meta.image_width, meta.image_height)

        # Get matched annotations
        ann_query = select(ExternalAnnotation).where(
            ExternalAnnotation.is_matched == True
        )
        if labels_filter:
            ann_query = ann_query.where(ExternalAnnotation.label.in_(labels_filter))
        if not include_unmatched:
            ann_query = ann_query.where(ExternalAnnotation.frame_id.isnot(None))

        ann_result = conn.execute(ann_query)
        annotations = ann_result.fetchall()

    # Group annotations by frame
    frame_annotations: dict[str, list] = {}
    for ann in annotations:
        frame_id = str(ann.frame_id) if ann.frame_id else None
        if frame_id and frame_id in frames:
            if frame_id not in frame_annotations:
                frame_annotations[frame_id] = []
            frame_annotations[frame_id].append(ann)

    # Get list of frames with annotations
    frame_ids = list(frame_annotations.keys())

    if shuffle_seed is not None:
        random.seed(shuffle_seed)
        random.shuffle(frame_ids)

    # Split data
    total = len(frame_ids)
    train_end = int(total * split_ratio[0])
    val_end = train_end + int(total * split_ratio[1])

    train_ids = frame_ids[:train_end]
    val_ids = frame_ids[train_end:val_end]
    test_ids = frame_ids[val_end:]

    logger.info(f"Split: train={len(train_ids)}, val={len(val_ids)}, test={len(test_ids)}")

    # Update progress
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": total,
            "message": "Starting export...",
        },
    )

    # Collect all unique labels
    all_labels = set()
    for anns in frame_annotations.values():
        for ann in anns:
            all_labels.add(ann.label)
    label_to_id = {label: idx for idx, label in enumerate(sorted(all_labels))}

    # Export COCO format
    coco_dir = output_dir / "coco"
    if format in ("coco", "both"):
        _export_coco(
            coco_dir,
            frames,
            frame_annotations,
            frame_metadata,
            train_ids,
            val_ids,
            test_ids,
            label_to_id,
            self,
        )

    # Export TFRecords
    tfrecord_dir = output_dir / "tfrecords"
    if format in ("tfrecord", "both"):
        _export_tfrecords(
            tfrecord_dir,
            frames,
            frame_annotations,
            frame_metadata,
            train_ids,
            val_ids,
            test_ids,
            label_to_id,
            self,
        )

    # Save split files
    splits_dir = output_dir / "splits"
    splits_dir.mkdir(exist_ok=True)
    _write_split_file(splits_dir / "train.txt", train_ids)
    _write_split_file(splits_dir / "val.txt", val_ids)
    _write_split_file(splits_dir / "test.txt", test_ids)

    # Save metadata
    metadata = {
        "dataset_id": dataset_id,
        "export_time": datetime.now(timezone.utc).isoformat(),
        "format": format,
        "total_images": total,
        "train_count": len(train_ids),
        "val_count": len(val_ids),
        "test_count": len(test_ids),
        "total_annotations": sum(len(anns) for anns in frame_annotations.values()),
        "labels": list(sorted(all_labels)),
        "label_map": label_to_id,
        "split_ratio": split_ratio,
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Export complete: {output_dir}")

    return {
        "dataset_id": dataset_id,
        "output_directory": str(output_dir),
        "format": format,
        "total_images": total,
        "total_annotations": metadata["total_annotations"],
        "train_count": len(train_ids),
        "val_count": len(val_ids),
        "test_count": len(test_ids),
        "labels": list(sorted(all_labels)),
    }


def _write_split_file(path: Path, frame_ids: list[str]) -> None:
    """Write frame IDs to a split file."""
    with open(path, "w") as f:
        for frame_id in frame_ids:
            f.write(f"{frame_id}\n")


def _export_coco(
    output_dir: Path,
    frames: dict,
    frame_annotations: dict,
    frame_metadata: dict[str, tuple[int, int]],
    train_ids: list[str],
    val_ids: list[str],
    test_ids: list[str],
    label_to_id: dict[str, int],
    task,
) -> None:
    """Export annotations in COCO format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    annotations_dir = output_dir / "annotations"
    images_dir.mkdir(exist_ok=True)
    annotations_dir.mkdir(exist_ok=True)

    # Default dimensions if metadata not available
    DEFAULT_WIDTH, DEFAULT_HEIGHT = 1920, 1080

    # Create category list
    categories = [
        {"id": idx, "name": label, "supercategory": "object"}
        for label, idx in label_to_id.items()
    ]

    def create_coco_dataset(split_name: str, frame_ids: list[str]) -> dict:
        images = []
        annotations = []
        ann_id = 1

        for idx, frame_id in enumerate(frame_ids):
            if frame_id not in frames:
                continue

            frame = frames[frame_id]
            anns = frame_annotations.get(frame_id, [])

            # Get dimensions from metadata or use defaults
            width, height = frame_metadata.get(frame_id, (DEFAULT_WIDTH, DEFAULT_HEIGHT))

            # Image info
            image_info = {
                "id": idx + 1,
                "file_name": f"{frame_id}.jpg",
                "width": width,
                "height": height,
            }
            images.append(image_info)

            # Copy/link image (skip for now, just reference)
            # In production, copy actual image files

            # Annotations
            for ann in anns:
                if ann.bbox_x is None:
                    continue

                coco_ann = {
                    "id": ann_id,
                    "image_id": idx + 1,
                    "category_id": label_to_id.get(ann.label, 0),
                    "bbox": [ann.bbox_x, ann.bbox_y, ann.bbox_width, ann.bbox_height],
                    "area": ann.bbox_width * ann.bbox_height if ann.bbox_width and ann.bbox_height else 0,
                    "iscrowd": 0,
                }
                annotations.append(coco_ann)
                ann_id += 1

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": idx + 1,
                    "total": len(frame_ids),
                    "message": f"Exporting COCO {split_name}...",
                },
            )

        return {
            "images": images,
            "annotations": annotations,
            "categories": categories,
        }

    # Export each split
    for split_name, split_ids in [
        ("train", train_ids),
        ("val", val_ids),
        ("test", test_ids),
    ]:
        if not split_ids:
            continue

        coco_data = create_coco_dataset(split_name, split_ids)
        output_file = annotations_dir / f"instances_{split_name}.json"
        with open(output_file, "w") as f:
            json.dump(coco_data, f)

        logger.info(f"Exported COCO {split_name}: {len(coco_data['images'])} images, {len(coco_data['annotations'])} annotations")


def _export_tfrecords(
    output_dir: Path,
    frames: dict,
    frame_annotations: dict,
    frame_metadata: dict[str, tuple[int, int]],
    train_ids: list[str],
    val_ids: list[str],
    test_ids: list[str],
    label_to_id: dict[str, int],
    task,
) -> None:
    """Export annotations in TFRecord format."""
    try:
        import tensorflow as tf
    except ImportError:
        logger.warning("TensorFlow not available - skipping TFRecord export")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Default dimensions if metadata not available
    DEFAULT_WIDTH, DEFAULT_HEIGHT = 1920, 1080

    def create_tf_example(frame_id: str, frame, annotations: list) -> bytes | None:
        """Create a TF Example from frame and annotations."""
        # In production, load actual image data
        # For now, create placeholder
        image_path = frame.image_left_path if frame else None
        if not image_path:
            return None

        # Read image if available
        full_path = Path(image_path)
        if not full_path.exists():
            return None

        try:
            with open(full_path, "rb") as f:
                image_data = f.read()
        except Exception:
            return None

        # Extract bboxes
        xmins, xmaxs, ymins, ymaxs = [], [], [], []
        classes_text, classes = [], []

        # Get dimensions from metadata or use defaults
        width, height = frame_metadata.get(frame_id, (DEFAULT_WIDTH, DEFAULT_HEIGHT))

        for ann in annotations:
            if ann.bbox_x is None:
                continue

            # Normalize coordinates
            xmins.append(ann.bbox_x / width)
            xmaxs.append((ann.bbox_x + ann.bbox_width) / width)
            ymins.append(ann.bbox_y / height)
            ymaxs.append((ann.bbox_y + ann.bbox_height) / height)
            classes_text.append(ann.label.encode("utf-8"))
            classes.append(label_to_id.get(ann.label, 0))

        # Create TF Example
        feature = {
            "image/height": tf.train.Feature(int64_list=tf.train.Int64List(value=[height])),
            "image/width": tf.train.Feature(int64_list=tf.train.Int64List(value=[width])),
            "image/filename": tf.train.Feature(bytes_list=tf.train.BytesList(value=[frame_id.encode()])),
            "image/source_id": tf.train.Feature(bytes_list=tf.train.BytesList(value=[frame_id.encode()])),
            "image/encoded": tf.train.Feature(bytes_list=tf.train.BytesList(value=[image_data])),
            "image/format": tf.train.Feature(bytes_list=tf.train.BytesList(value=[b"png"])),
            "image/object/bbox/xmin": tf.train.Feature(float_list=tf.train.FloatList(value=xmins)),
            "image/object/bbox/xmax": tf.train.Feature(float_list=tf.train.FloatList(value=xmaxs)),
            "image/object/bbox/ymin": tf.train.Feature(float_list=tf.train.FloatList(value=ymins)),
            "image/object/bbox/ymax": tf.train.Feature(float_list=tf.train.FloatList(value=ymaxs)),
            "image/object/class/text": tf.train.Feature(bytes_list=tf.train.BytesList(value=classes_text)),
            "image/object/class/label": tf.train.Feature(int64_list=tf.train.Int64List(value=classes)),
        }

        example = tf.train.Example(features=tf.train.Features(feature=feature))
        return example.SerializeToString()

    def write_tfrecords(split_name: str, frame_ids: list[str], shard_size: int = 100):
        """Write TFRecords with sharding."""
        split_dir = output_dir / split_name
        split_dir.mkdir(exist_ok=True)

        records_written = 0
        shard_idx = 0
        writer = None

        for idx, frame_id in enumerate(frame_ids):
            if idx % shard_size == 0:
                if writer:
                    writer.close()
                shard_path = split_dir / f"shard_{shard_idx:05d}.tfrecord"
                writer = tf.io.TFRecordWriter(str(shard_path))
                shard_idx += 1

            frame = frames.get(frame_id)
            annotations = frame_annotations.get(frame_id, [])

            example = create_tf_example(frame_id, frame, annotations)
            if example:
                writer.write(example)
                records_written += 1

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": idx + 1,
                    "total": len(frame_ids),
                    "message": f"Writing TFRecords {split_name}...",
                },
            )

        if writer:
            writer.close()

        return records_written

    # Export each split
    for split_name, split_ids in [
        ("train", train_ids),
        ("val", val_ids),
        ("test", test_ids),
    ]:
        if not split_ids:
            continue

        count = write_tfrecords(split_name, split_ids)
        logger.info(f"Exported TFRecords {split_name}: {count} records")


@app.task(
    bind=True,
    name="worker.tasks.annotations.rematch_annotations",
)
def rematch_annotations(self, import_id: str, match_by: str = "filename") -> dict:
    """
    Re-run annotation matching for an import.

    Useful when frames have been added after initial import.

    Args:
        import_id: Annotation import UUID
        match_by: Matching strategy ("filename" or "frame_index")

    Returns:
        Matching statistics
    """
    from backend.app.models.external_annotation import AnnotationImport, ExternalAnnotation
    from backend.app.models.frame import Frame
    from backend.app.models.job import ProcessingJob

    logger.info(f"Re-matching annotations for import: {import_id}")

    engine = get_db_engine()

    with engine.connect() as conn:
        # Get import record
        import_result = conn.execute(
            select(AnnotationImport).where(AnnotationImport.id == UUID(import_id))
        )
        import_record = import_result.first()
        if import_record is None:
            raise ValueError(f"Import {import_id} not found")

        dataset_id = import_record.dataset_id

        # Get frames for this dataset
        frames_query = (
            select(Frame)
            .join(ProcessingJob)
            .where(ProcessingJob.dataset_id == dataset_id)
        )
        frames_result = conn.execute(frames_query)
        frames = frames_result.fetchall()

        # Build lookup
        if match_by == "filename":
            frame_lookup = {}
            for frame in frames:
                if frame.image_left_path:
                    filename = Path(frame.image_left_path).name
                    frame_lookup[filename] = frame.id
                    frame_lookup[Path(filename).stem] = frame.id
        else:
            frame_lookup = {str(f.svo2_frame_index): f.id for f in frames}

        # Get annotations
        ann_result = conn.execute(
            select(ExternalAnnotation).where(ExternalAnnotation.import_id == UUID(import_id))
        )
        annotations = ann_result.fetchall()

    matched = 0
    for ann in annotations:
        frame_id = None

        # Try to match
        image_name = ann.source_image_name
        frame_id = frame_lookup.get(image_name)

        if frame_id is None:
            filename = Path(image_name).name
            frame_id = frame_lookup.get(filename)

        if frame_id is None:
            stem = Path(image_name).stem
            frame_id = frame_lookup.get(stem)

        if frame_id:
            with engine.connect() as conn:
                conn.execute(
                    ExternalAnnotation.__table__.update()
                    .where(ExternalAnnotation.id == ann.id)
                    .values(
                        frame_id=frame_id,
                        is_matched=True,
                        match_confidence=1.0,
                    )
                )
                conn.commit()
            matched += 1

    # Update import record
    with engine.connect() as conn:
        conn.execute(
            AnnotationImport.__table__.update()
            .where(AnnotationImport.id == UUID(import_id))
            .values(
                matched_frames=matched,
                unmatched_images=len(annotations) - matched,
            )
        )
        conn.commit()

    logger.info(f"Re-matched {matched}/{len(annotations)} annotations")

    return {
        "import_id": import_id,
        "total_annotations": len(annotations),
        "matched": matched,
        "unmatched": len(annotations) - matched,
    }
