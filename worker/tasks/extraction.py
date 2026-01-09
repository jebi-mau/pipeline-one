"""SVO2 extraction task."""

import logging
from pathlib import Path
from typing import Any

from worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="worker.tasks.extraction.extract_svo2")
def extract_svo2(
    self,
    job_id: str,
    svo2_file: str,
    config: dict,
) -> dict[str, Any]:
    """
    Extract frames from a single SVO2 file.

    Args:
        job_id: Processing job UUID
        svo2_file: Path to SVO2 file
        config: Extraction configuration

    Returns:
        Extraction result with frame registry path
    """
    from processing.svo2.extractor import ExtractionConfig, SVO2Extractor
    from processing.svo2.reader import SVO2Reader

    logger.info(f"Extracting SVO2: {svo2_file}")

    # Create output directory
    output_base = config.get("output_dir", f"data/output/{job_id}")
    svo2_name = Path(svo2_file).stem
    output_dir = Path(output_base) / svo2_name

    # Configure extraction
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
    )

    # Progress callback
    def progress_callback(current: int, total: int, message: str) -> None:
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

    try:
        # Open SVO2 file
        with SVO2Reader(svo2_file, depth_mode=config.get("depth_mode", "NEURAL")) as reader:
            # Create extractor
            extractor = SVO2Extractor(reader, output_dir, extraction_config)

            # Run extraction
            result = extractor.extract(progress_callback=progress_callback)

        logger.info(f"Extraction complete: {result.extracted_frames} frames")

        return {
            "status": "completed",
            "svo2_file": svo2_file,
            "output_dir": str(result.output_dir),
            "frame_count": result.frame_count,
            "extracted_frames": result.extracted_frames,
            "failed_frames": result.failed_frames,
            "frame_registry": str(result.frame_registry_file),
            "calibration": str(result.calibration_file),
        }

    except Exception as e:
        logger.error(f"Extraction failed for {svo2_file}: {e}")
        return {
            "status": "failed",
            "svo2_file": svo2_file,
            "error": str(e),
        }


@app.task(name="worker.tasks.extraction.validate_svo2")
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
