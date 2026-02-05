"""SVO2 extraction task."""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage

from worker.celery_app import app
from worker.db import get_db_connection, record_stage_completion, update_job_progress

logger = logging.getLogger(__name__)


# =============================================================================
# Diversity Filter Functions
# =============================================================================


def compute_dhash(image: Image.Image, hash_size: int = 16) -> str:
    """
    Compute difference hash (dHash) for an image.
    Fast and effective for detecting near-duplicates.
    """
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(resized)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return "".join(format(byte, "02x") for byte in np.packbits(diff.flatten()))


def compute_hash_similarity(hash1: str, hash2: str) -> float:
    """Compute similarity between two hashes using Hamming distance (0-1)."""
    if len(hash1) != len(hash2):
        return 0.0
    bits1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
    bits2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
    diff_count = sum(b1 != b2 for b1, b2 in zip(bits1, bits2, strict=True))
    return 1.0 - (diff_count / len(bits1))


def compute_motion_score(prev_image: np.ndarray, curr_image: np.ndarray) -> float:
    """Compute motion score between two frames (0-1)."""
    try:
        diff = np.abs(prev_image.astype(np.float32) - curr_image.astype(np.float32))
        diff = ndimage.gaussian_filter(diff, sigma=2)
        return float(np.mean(diff) / 255.0)
    except Exception:
        return 0.0


def apply_diversity_filter(
    frame_registry_path: Path,
    output_dir: Path,
    similarity_threshold: float = 0.85,
    motion_threshold: float = 0.02,
) -> tuple[int, int]:
    """
    Apply diversity filtering to extracted frames.

    Removes similar/low-motion frames from disk and updates frame registry.

    Args:
        frame_registry_path: Path to frame_registry.json
        output_dir: Output directory containing extracted frames
        similarity_threshold: Frames with similarity > this are duplicates (0-1)
        motion_threshold: Frames with motion < this are low-motion (0-1)

    Returns:
        Tuple of (frames_kept, frames_removed)
    """
    # Load frame registry
    with open(frame_registry_path) as f:
        registry = json.load(f)

    frames = registry.get("frames", [])
    if len(frames) < 2:
        return len(frames), 0

    logger.info(f"Running diversity filter on {len(frames)} frames "
                f"(similarity={similarity_threshold}, motion={motion_threshold})")

    # Compute hashes and motion scores
    frame_data: list[dict] = []
    prev_gray: np.ndarray | None = None

    for frame_info in frames:
        left_path = output_dir / frame_info.get("image_left", "")

        if not left_path.exists():
            frame_data.append({"frame": frame_info, "hash": "", "motion": 1.0, "keep": True})
            continue

        try:
            img = Image.open(left_path)
            img_gray = np.array(img.convert("L"))
            dhash = compute_dhash(img)

            # Compute motion relative to previous frame
            if prev_gray is not None:
                motion = compute_motion_score(prev_gray, img_gray)
            else:
                motion = 1.0  # First frame always has "motion"

            frame_data.append({
                "frame": frame_info,
                "hash": dhash,
                "motion": motion,
                "keep": True,
                "path": left_path,
            })

            prev_gray = img_gray
        except Exception as e:
            logger.warning(f"Error processing frame {frame_info.get('image_left')}: {e}")
            frame_data.append({"frame": frame_info, "hash": "", "motion": 1.0, "keep": True})

    # Apply diversity selection
    selected_hashes: list[str] = []

    for i, fd in enumerate(frame_data):
        if not fd["hash"]:
            continue

        # Skip low-motion frames (except first)
        if i > 0 and fd["motion"] < motion_threshold:
            fd["keep"] = False
            continue

        # Check similarity against selected frames
        is_duplicate = False
        for sel_hash in selected_hashes:
            similarity = compute_hash_similarity(fd["hash"], sel_hash)
            if similarity > similarity_threshold:
                is_duplicate = True
                break

        if is_duplicate:
            fd["keep"] = False
        else:
            selected_hashes.append(fd["hash"])

    # Remove non-diverse frames from disk
    frames_removed = 0
    kept_frames = []

    for fd in frame_data:
        if fd["keep"]:
            kept_frames.append(fd["frame"])
        else:
            frames_removed += 1
            frame_info = fd["frame"]

            # Remove frame files
            for key in ["image_left", "image_right", "depth", "point_cloud"]:
                file_path = frame_info.get(key)
                if file_path:
                    full_path = output_dir / file_path
                    if full_path.exists():
                        try:
                            full_path.unlink()
                        except Exception as e:
                            logger.warning(f"Failed to remove {full_path}: {e}")

    # Update sequence indices for remaining frames
    for i, frame in enumerate(kept_frames):
        frame["sequence_index"] = i

    # Update frame registry
    registry["frames"] = kept_frames
    registry["extracted_frames"] = len(kept_frames)
    registry["diversity_filtered"] = True
    registry["frames_removed_by_diversity"] = frames_removed

    with open(frame_registry_path, "w") as f:
        json.dump(registry, f, indent=2)

    logger.info(f"Diversity filter complete: kept {len(kept_frames)}, removed {frames_removed}")

    return len(kept_frames), frames_removed


def parse_unix_timestamp_from_filename(filename: str) -> int | None:
    """
    Parse Unix timestamp from SVO2 filename.

    Supports formats like:
    - 1704067200.svo2
    - recording_1704067200.svo2
    - 2024-01-01_1704067200.svo2

    Args:
        filename: SVO2 filename

    Returns:
        Unix timestamp as integer, or None if not found
    """
    # Try to find a sequence of 10+ digits (Unix timestamp)
    match = re.search(r'(\d{10,13})', filename)
    if match:
        timestamp_str = match.group(1)
        # Handle millisecond timestamps (13 digits)
        if len(timestamp_str) == 13:
            return int(timestamp_str) // 1000
        return int(timestamp_str)
    return None


def ingest_frame_registry(
    job_id: str,
    svo2_file: str,
    frame_registry_path: str,
    dataset_file_id: str | None,
    original_filename: str,
    original_unix_timestamp: int | None,
) -> int:
    """
    Ingest frame registry JSON into database for lineage tracking.

    Args:
        job_id: Processing job UUID
        svo2_file: Full path to SVO2 file
        frame_registry_path: Path to frame_registry.json
        dataset_file_id: UUID of DatasetFile record (if from dataset)
        original_filename: Original SVO2 filename
        original_unix_timestamp: Unix timestamp parsed from filename

    Returns:
        Number of frames ingested
    """
    try:
        with open(frame_registry_path) as f:
            registry = json.load(f)

        frames_data = registry.get("frames", [])
        if not frames_data:
            logger.warning(f"No frames in registry: {frame_registry_path}")
            return 0

        with get_db_connection() as conn:
            ingested = 0
            for frame_info in frames_data:
                frame_id = str(uuid.uuid4())

                # Build insert SQL
                sql = """
                    INSERT INTO frames (
                        id, job_id, dataset_file_id,
                        svo2_file_path, svo2_frame_index,
                        original_svo2_filename, original_unix_timestamp,
                        timestamp_ns, timestamp_relative_ms,
                        image_left_path, image_right_path,
                        depth_path, point_cloud_path,
                        extraction_status, segmentation_status, reconstruction_status,
                        sequence_index, created_at, updated_at
                    ) VALUES (
                        :id, :job_id, :dataset_file_id,
                        :svo2_file_path, :svo2_frame_index,
                        :original_svo2_filename, :original_unix_timestamp,
                        :timestamp_ns, :timestamp_relative_ms,
                        :image_left_path, :image_right_path,
                        :depth_path, :point_cloud_path,
                        'extracted', 'pending', 'pending',
                        :sequence_index, :created_at, :updated_at
                    )
                """

                from sqlalchemy import text
                now = datetime.now(timezone.utc)

                conn.execute(text(sql), {
                    "id": frame_id,
                    "job_id": job_id,
                    "dataset_file_id": dataset_file_id,
                    "svo2_file_path": svo2_file,
                    "svo2_frame_index": frame_info.get("svo2_frame_index", 0),
                    "original_svo2_filename": original_filename,
                    "original_unix_timestamp": original_unix_timestamp,
                    "timestamp_ns": frame_info.get("timestamp_ns", 0),
                    "timestamp_relative_ms": frame_info.get("timestamp_relative_ms", 0.0),
                    "image_left_path": frame_info.get("image_left"),
                    "image_right_path": frame_info.get("image_right"),
                    "depth_path": frame_info.get("depth"),
                    "point_cloud_path": frame_info.get("point_cloud"),
                    "sequence_index": frame_info.get("sequence_index", 0),
                    "created_at": now,
                    "updated_at": now,
                })
                ingested += 1

            conn.commit()
            logger.info(f"Ingested {ingested} frames into database for job {job_id}")
            return ingested

    except Exception as e:
        logger.error(f"Failed to ingest frame registry: {e}")
        return 0


@app.task(
    bind=True,
    name="worker.tasks.extraction.extract_svo2",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(IOError, OSError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def extract_svo2(
    self,
    job_id: str,
    svo2_file: str,
    config: dict,
    dataset_file_id: str | None = None,
) -> dict[str, Any]:
    """
    Extract frames from a single SVO2 file.

    Args:
        job_id: Processing job UUID
        svo2_file: Path to SVO2 file
        config: Extraction configuration
        dataset_file_id: Optional UUID of DatasetFile for lineage tracking

    Returns:
        Extraction result with frame registry path
    """
    from processing.svo2.extractor import ExtractionConfig, SVO2Extractor
    from processing.svo2.reader import SVO2Reader

    logger.info(f"Extracting SVO2: {svo2_file}")

    # Track stage timing
    stage_start_time = time.time()

    # Create output directory
    output_base = config.get("output_dir", f"data/output/{job_id}")
    svo2_name = Path(svo2_file).stem
    output_dir = Path(output_base) / svo2_name

    # Extract lineage metadata from filename for context
    original_filename = Path(svo2_file).name
    original_unix_timestamp = parse_unix_timestamp_from_filename(original_filename)

    # Configure extraction with lineage context
    extraction_config = ExtractionConfig(
        extract_left_rgb=config.get("extract_left_rgb", True),
        extract_right_rgb=config.get("extract_right_rgb", True),
        extract_depth=config.get("extract_depth", True),
        extract_point_cloud=config.get("extract_point_cloud", True),
        extract_imu=config.get("extract_imu", True),
        frame_skip=config.get("frame_skip", 1),
        start_frame=config.get("start_frame", 0),
        end_frame=config.get("end_frame"),
        image_format=config.get("image_format", "png"),
        depth_format=config.get("depth_format", "png16"),
        point_cloud_format=config.get("point_cloud_format", "ply"),
        # Lineage context for enhanced naming
        dataset_id=config.get("dataset_id"),
        original_unix_timestamp=original_unix_timestamp,
        use_enhanced_naming=config.get("use_enhanced_naming", False),
    )

    # Track total frames for this file
    total_frames_this_file = 0

    # Get progress range from config (default to old behavior)
    progress_range = config.get("progress_range", (0, 25))
    range_start, range_end = progress_range

    # Progress callback
    def progress_callback(current: int, total: int, message: str) -> None:
        nonlocal total_frames_this_file
        total_frames_this_file = total

        # Update Celery state
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": "extraction",
                "file": svo2_file,
                "current": current,
                "total": total,
                "message": message,
            },
        )

        # Update database progress (stage 1 = extraction)
        # Calculate overall progress based on assigned range
        stage_progress = (current / total * 100) if total > 0 else 0
        range_size = range_end - range_start
        overall_progress = range_start + (stage_progress / 100 * range_size)

        update_job_progress(
            job_id=job_id,
            stage=1,
            progress=overall_progress,
            stage_progress=stage_progress,
            total_frames=total,
            processed_frames=current,
        )

    try:
        # Open SVO2 file
        with SVO2Reader(svo2_file, depth_mode=config.get("depth_mode", "ULTRA")) as reader:
            # Create extractor
            extractor = SVO2Extractor(reader, output_dir, extraction_config)

            # Run extraction
            result = extractor.extract(progress_callback=progress_callback)

        logger.info(f"Extraction complete: {result.extracted_frames} frames")

        # Apply diversity filter if enabled
        frames_kept = result.extracted_frames
        frames_removed_by_diversity = 0

        if config.get("enable_diversity_filter", False):
            similarity_threshold = config.get("diversity_similarity_threshold", 0.85)
            motion_threshold = config.get("diversity_motion_threshold", 0.02)

            logger.info(f"Applying diversity filter (similarity={similarity_threshold}, motion={motion_threshold})")

            frames_kept, frames_removed_by_diversity = apply_diversity_filter(
                frame_registry_path=Path(result.frame_registry_file),
                output_dir=output_dir,
                similarity_threshold=similarity_threshold,
                motion_threshold=motion_threshold,
            )

            logger.info(f"Diversity filter: kept {frames_kept}, removed {frames_removed_by_diversity}")

        # Ingest frame registry into database for lineage tracking
        # (original_filename and original_unix_timestamp already extracted above)
        ingested_frames = 0
        if result.frame_registry_file and Path(result.frame_registry_file).exists():
            ingested_frames = ingest_frame_registry(
                job_id=job_id,
                svo2_file=svo2_file,
                frame_registry_path=str(result.frame_registry_file),
                dataset_file_id=dataset_file_id,
                original_filename=original_filename,
                original_unix_timestamp=original_unix_timestamp,
            )
            logger.info(f"Ingested {ingested_frames} frames into database")

        # Record stage duration for benchmarking
        # Note: Extraction may run multiple tasks in parallel for different files,
        # so we record for each file. The overall extraction duration will be
        # calculated from the longest-running extraction task.
        stage_duration = time.time() - stage_start_time
        record_stage_completion(
            job_id=job_id,
            stage="extraction",
            duration_seconds=stage_duration,
            total_frames=frames_kept,
        )

        logger.info(
            f"Extraction complete: {frames_kept} frames in {stage_duration:.1f}s "
            f"({frames_kept / stage_duration:.2f} fps)"
        )

        return {
            "status": "completed",
            "svo2_file": svo2_file,
            "output_dir": str(result.output_dir),
            "frame_count": result.frame_count,
            "extracted_frames": frames_kept,
            "failed_frames": result.failed_frames,
            "frames_removed_by_diversity": frames_removed_by_diversity,
            "frame_registry": str(result.frame_registry_file),
            "calibration": str(result.calibration_file),
            "ingested_frames": ingested_frames,
            "original_filename": original_filename,
            "original_unix_timestamp": original_unix_timestamp,
            "dataset_file_id": dataset_file_id,
            "duration_seconds": stage_duration,
        }

    except Exception as e:
        logger.error(f"Extraction failed for {svo2_file}: {e}")
        return {
            "status": "failed",
            "svo2_file": svo2_file,
            "error": str(e),
        }


@app.task(
    name="worker.tasks.extraction.validate_svo2",
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(IOError, OSError),
)
def validate_svo2(svo2_file: str) -> dict[str, Any]:
    """
    Validate an SVO2 file can be opened.

    Args:
        svo2_file: Path to SVO2 file

    Returns:
        Validation result with file metadata
    """
    from processing.svo2.reader import SVO2Reader

    try:
        with SVO2Reader(svo2_file) as reader:
            metadata = reader.get_metadata()

        return {
            "valid": True,
            "file": svo2_file,
            "metadata": metadata,
        }

    except Exception as e:
        return {
            "valid": False,
            "file": svo2_file,
            "error": str(e),
        }
