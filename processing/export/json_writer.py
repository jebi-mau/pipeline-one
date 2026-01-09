"""JSON format export writer."""

from __future__ import annotations

import gzip
import json
import logging
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class JSONExportConfig:
    """Configuration for JSON export."""

    include_point_clouds: bool = False  # Large, usually omitted
    include_masks: bool = False  # Very large, usually omitted
    include_tracks: bool = True
    include_calibration: bool = True
    include_metadata: bool = True

    # Output options
    compress: bool = True
    pretty_print: bool = False
    indent: int = 2


class JSONWriter:
    """
    Exports full results to JSON format with extended metadata.

    Provides complete traceability from output annotations back to
    source SVO2 files and frames.
    """

    def __init__(
        self,
        output_path: str | Path,
        config: JSONExportConfig | None = None,
    ):
        """
        Initialize JSON writer.

        Args:
            output_path: Output file path
            config: Export configuration
        """
        self.output_path = Path(output_path)
        self.config = config or JSONExportConfig()

    def export_from_job(
        self,
        job_output_dir: str | Path,
        job_config: dict | None = None,
    ) -> Path:
        """
        Export a processed job to JSON format.

        Args:
            job_output_dir: Directory containing processed job data
            job_config: Original job configuration

        Returns:
            Path to exported JSON file
        """
        job_dir = Path(job_output_dir)

        # Build export data structure
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "format": "svo2-sam3-analyzer",
        }

        if self.config.include_metadata:
            export_data["metadata"] = self._collect_metadata(job_dir, job_config)

        # Collect frames and annotations
        export_data["sequences"] = []

        sequences = [d for d in job_dir.iterdir() if d.is_dir()]

        for seq_dir in sequences:
            seq_data = self._export_sequence(seq_dir)
            if seq_data:
                export_data["sequences"].append(seq_data)

        # Write output
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.config.compress:
            output_file = self.output_path.with_suffix(".json.gz")
            with gzip.open(output_file, "wt", encoding="utf-8") as f:
                json.dump(export_data, f, indent=self.config.indent if self.config.pretty_print else None, default=self._json_serializer)
        else:
            output_file = self.output_path.with_suffix(".json")
            with open(output_file, "w") as f:
                json.dump(export_data, f, indent=self.config.indent if self.config.pretty_print else None, default=self._json_serializer)

        logger.info(f"Exported results to {output_file}")
        return output_file

    def _collect_metadata(
        self,
        job_dir: Path,
        job_config: dict | None,
    ) -> dict:
        """Collect job metadata."""
        metadata = {
            "job_directory": str(job_dir),
            "config": job_config or {},
        }

        # Count statistics
        total_frames = 0
        total_detections = 0
        total_tracks = 0

        for seq_dir in job_dir.iterdir():
            if not seq_dir.is_dir():
                continue

            # Count frames
            registry_file = seq_dir / "frame_registry.json"
            if registry_file.exists():
                with open(registry_file) as f:
                    registry = json.load(f)
                total_frames += len(registry.get("frames", []))

            # Count detections
            detections_file = seq_dir / "detections" / "detections.json"
            if detections_file.exists():
                with open(detections_file) as f:
                    det_data = json.load(f)
                total_detections += det_data.get("total_detections", 0)

            # Count tracks
            tracks_file = seq_dir / "tracks.json"
            if tracks_file.exists():
                with open(tracks_file) as f:
                    tracks_data = json.load(f)
                total_tracks += tracks_data.get("total_tracks", 0)

        metadata["statistics"] = {
            "total_frames": total_frames,
            "total_detections": total_detections,
            "total_tracks": total_tracks,
        }

        return metadata

    def _export_sequence(self, seq_dir: Path) -> dict | None:
        """Export a single sequence."""
        registry_file = seq_dir / "frame_registry.json"
        if not registry_file.exists():
            return None

        with open(registry_file) as f:
            registry = json.load(f)

        seq_data = {
            "name": seq_dir.name,
            "svo2_file": registry.get("svo2_file"),
            "svo2_hash": registry.get("svo2_hash"),
            "total_frames": registry.get("total_frames", 0),
            "extracted_frames": registry.get("extracted_frames", 0),
        }

        # Include calibration
        if self.config.include_calibration:
            calib_file = seq_dir / "calib" / "calibration.json"
            if calib_file.exists():
                with open(calib_file) as f:
                    seq_data["calibration"] = json.load(f)

        # Include tracks
        if self.config.include_tracks:
            tracks_file = seq_dir / "tracks.json"
            if tracks_file.exists():
                with open(tracks_file) as f:
                    tracks_data = json.load(f)
                seq_data["tracks"] = tracks_data.get("tracks", [])

        # Export frames with annotations
        seq_data["frames"] = []

        # Load detections
        detections_data = {}
        detections_file = seq_dir / "detections" / "detections.json"
        if detections_file.exists():
            with open(detections_file) as f:
                det_json = json.load(f)
            detections_data = det_json.get("frames", {})

        for frame_info in registry.get("frames", []):
            frame_data = {
                "frame_id": frame_info["frame_id"],
                "sequence_index": frame_info["sequence_index"],
                "svo2_frame_index": frame_info["svo2_frame_index"],
                "timestamp_ns": frame_info["timestamp_ns"],
                "files": {
                    "image_left": frame_info.get("image_left"),
                    "image_right": frame_info.get("image_right"),
                    "depth": frame_info.get("depth"),
                    "point_cloud": frame_info.get("point_cloud"),
                    "imu": frame_info.get("imu"),
                },
            }

            # Add detections
            frame_dets = detections_data.get(frame_info["frame_id"], {})
            frame_data["detections"] = frame_dets.get("detections", [])

            # Add 3D labels if available
            label_file = seq_dir / "label_2" / f"{frame_info['sequence_index']:06d}.txt"
            if label_file.exists():
                frame_data["labels_3d"] = self._parse_kitti_labels(label_file)

            seq_data["frames"].append(frame_data)

        return seq_data

    def _parse_kitti_labels(self, label_file: Path) -> list[dict]:
        """Parse KITTI format labels."""
        labels = []

        with open(label_file) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 15:
                    continue

                label = {
                    "type": parts[0],
                    "truncated": float(parts[1]),
                    "occluded": int(parts[2]),
                    "alpha": float(parts[3]),
                    "bbox_2d": [float(x) for x in parts[4:8]],
                    "dimensions": {
                        "height": float(parts[8]),
                        "width": float(parts[9]),
                        "length": float(parts[10]),
                    },
                    "location": {
                        "x": float(parts[11]),
                        "y": float(parts[12]),
                        "z": float(parts[13]),
                    },
                    "rotation_y": float(parts[14]),
                }

                if len(parts) > 15:
                    label["score"] = float(parts[15])

                labels.append(label)

        return labels

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for special types."""
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, Path):
            return str(obj)
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
