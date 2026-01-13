"""Object tracking task."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from worker.celery_app import app
from worker.db import update_job_progress

logger = logging.getLogger(__name__)

# Default output base directory (configurable via environment)
OUTPUT_BASE = Path(os.getenv("PIPELINE_OUTPUT_DIR", "data/output"))


@app.task(
    bind=True,
    name="worker.tasks.tracking.run_tracking",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(IOError, OSError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def run_tracking(
    self,
    reconstruction_result: dict | None,
    job_id: str,
    config: dict,
) -> dict[str, Any]:
    """
    Run object tracking across frames.

    Args:
        reconstruction_result: Results from reconstruction stage
        job_id: Processing job UUID
        config: Tracking configuration

    Returns:
        Tracking result summary
    """
    from processing.tracking.bytetrack import ByteTrackConfig
    from processing.tracking.track_manager import TrackManager
    from processing.svo2.frame_registry import FrameRegistry

    logger.info(f"Running tracking for job {job_id}")

    if reconstruction_result is None:
        return {"status": "skipped", "reason": "No reconstruction results", "total_detections": 0}

    # Preserve total_detections from previous stages
    total_detections = reconstruction_result.get("total_detections", 0)

    # Get output directory from config or use default
    output_dir = Path(config.get("output_directory", OUTPUT_BASE / job_id))
    if not output_dir.exists():
        return {"status": "skipped", "reason": f"Output directory not found: {output_dir}", "total_detections": total_detections}

    # Configuration
    track_config = ByteTrackConfig(
        track_thresh=config.get("track_thresh", 0.5),
        track_buffer=config.get("track_buffer", 30),
        match_thresh=config.get("match_thresh", 0.8),
        min_box_area=config.get("min_box_area", 10),
        use_3d_iou=config.get("use_3d_iou", True),
    )

    # Get progress range from config (default to old behavior)
    progress_range = config.get("progress_range", (90, 100))
    range_start, range_end = progress_range

    # Progress callback
    def progress_callback(current: int, total: int, message: str) -> None:
        # Update Celery state
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": "tracking",
                "current": current,
                "total": total,
                "message": message,
            },
        )

        # Update database progress (stage 4 = tracking)
        # Calculate overall progress based on assigned range
        stage_progress = (current / total * 100) if total > 0 else 0
        range_size = range_end - range_start
        overall_progress = range_start + (stage_progress / 100 * range_size)

        update_job_progress(
            job_id=job_id,
            stage=4,
            progress=overall_progress,
            stage_progress=stage_progress,
            processed_frames=current,
        )

    try:
        # Find all frame registries
        registry_files = list(output_dir.glob("*/frame_registry.json"))

        track_manager = TrackManager(track_config)
        total_tracks = 0

        for registry_path in registry_files:
            registry = FrameRegistry.from_extraction_result(registry_path)

            # Load frame labels
            labels_dir = registry_path.parent / "label_2"
            if not labels_dir.exists():
                logger.warning(f"Labels not found: {labels_dir}")
                continue

            # Process frames in order
            frames = sorted(
                registry.iter_frames(),
                key=lambda f: f.sequence_index,
            )

            for idx, frame in enumerate(frames):
                progress_callback(idx, len(frames), f"Frame {frame.sequence_index}")

                # Load 3D detections
                label_file = labels_dir / f"{frame.sequence_index:06d}.txt"
                if not label_file.exists():
                    continue

                detections = []
                with open(label_file) as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) < 15:
                            continue

                        # Parse KITTI format
                        class_name = parts[0]
                        h, w, l = map(float, parts[8:11])
                        x, y, z = map(float, parts[11:14])
                        rotation_y = float(parts[14])

                        # Score from file or default
                        score = float(parts[15]) if len(parts) > 15 else 0.8

                        detections.append({
                            "bbox_3d": (x, y, z, w, h, l, rotation_y),
                            "class_id": class_name.lower(),
                            "class_name": class_name,
                            "score": score,
                        })

                # Update tracker
                if detections:
                    tracks = track_manager.update(
                        detections,
                        frame.sequence_index,
                        frame.timestamp_ns,
                    )

                # Update registry
                registry.update_status(
                    frame.frame_id,
                    tracking_complete=True,
                )

            registry.save()

            # Save tracks for this sequence
            tracks_file = registry_path.parent / "tracks.json"
            track_manager.save(tracks_file)

            # Get stats
            stats = track_manager.get_statistics()
            total_tracks += stats["total_tracks"]

            # Reset for next sequence
            track_manager.reset()

        logger.info(f"Tracking complete: {total_tracks} tracks")

        return {
            "status": "completed",
            "total_tracks": total_tracks,
            "total_detections": total_detections,
        }

    except Exception as e:
        logger.error(f"Tracking failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "total_detections": total_detections if 'total_detections' in dir() else 0,
        }


@app.task(name="worker.tasks.tracking.merge_tracks")
def merge_tracks(
    track_files: list[str],
    output_file: str,
) -> dict[str, Any]:
    """
    Merge track files from multiple sequences.

    Args:
        track_files: List of track JSON files
        output_file: Output merged track file

    Returns:
        Merge result
    """
    all_tracks = []
    next_id = 1

    for track_file in track_files:
        track_path = Path(track_file)
        if not track_path.exists():
            continue

        with open(track_path) as f:
            data = json.load(f)

        for track in data.get("tracks", []):
            # Reassign track ID to ensure uniqueness
            track["track_id"] = next_id
            next_id += 1
            all_tracks.append(track)

    # Save merged tracks
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "total_tracks": len(all_tracks),
            "tracks": all_tracks,
        }, f, indent=2)

    return {
        "status": "completed",
        "total_tracks": len(all_tracks),
        "output_file": str(output_path),
    }
