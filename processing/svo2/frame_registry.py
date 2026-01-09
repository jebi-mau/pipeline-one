"""Frame registry for tracking extracted frames."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FrameEntry:
    """Single frame entry in the registry."""

    frame_id: str
    sequence_index: int
    svo2_frame_index: int
    svo2_file: str
    timestamp_ns: int

    # File paths (relative to output directory)
    image_left: str | None = None
    image_right: str | None = None
    depth: str | None = None
    point_cloud: str | None = None
    imu: str | None = None

    # Processing status
    segmentation_complete: bool = False
    reconstruction_complete: bool = False
    tracking_complete: bool = False

    # Detection count
    detection_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "frame_id": self.frame_id,
            "sequence_index": self.sequence_index,
            "svo2_frame_index": self.svo2_frame_index,
            "svo2_file": self.svo2_file,
            "timestamp_ns": self.timestamp_ns,
            "image_left": self.image_left,
            "image_right": self.image_right,
            "depth": self.depth,
            "point_cloud": self.point_cloud,
            "imu": self.imu,
            "segmentation_complete": self.segmentation_complete,
            "reconstruction_complete": self.reconstruction_complete,
            "tracking_complete": self.tracking_complete,
            "detection_count": self.detection_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FrameEntry:
        """Create from dictionary."""
        return cls(
            frame_id=data["frame_id"],
            sequence_index=data["sequence_index"],
            svo2_frame_index=data["svo2_frame_index"],
            svo2_file=data["svo2_file"],
            timestamp_ns=data["timestamp_ns"],
            image_left=data.get("image_left"),
            image_right=data.get("image_right"),
            depth=data.get("depth"),
            point_cloud=data.get("point_cloud"),
            imu=data.get("imu"),
            segmentation_complete=data.get("segmentation_complete", False),
            reconstruction_complete=data.get("reconstruction_complete", False),
            tracking_complete=data.get("tracking_complete", False),
            detection_count=data.get("detection_count", 0),
        )


@dataclass
class FrameRegistry:
    """
    Registry for tracking all extracted frames across multiple SVO2 files.

    Provides:
    - Unique frame IDs (svo2_hash_framenum)
    - Full traceability back to source SVO2
    - Processing status tracking
    - File path mapping
    """

    output_dir: Path
    frames: dict[str, FrameEntry] = field(default_factory=dict)

    # Metadata
    svo2_files: list[str] = field(default_factory=list)
    total_frames: int = 0

    def add_frame(self, entry: FrameEntry) -> None:
        """Add a frame to the registry."""
        self.frames[entry.frame_id] = entry

        if entry.svo2_file not in self.svo2_files:
            self.svo2_files.append(entry.svo2_file)

    def get_frame(self, frame_id: str) -> FrameEntry | None:
        """Get a frame by ID."""
        return self.frames.get(frame_id)

    def get_frames_by_svo2(self, svo2_file: str) -> list[FrameEntry]:
        """Get all frames from a specific SVO2 file."""
        return [
            frame for frame in self.frames.values()
            if frame.svo2_file == svo2_file
        ]

    def get_pending_segmentation(self) -> list[FrameEntry]:
        """Get frames pending segmentation."""
        return [
            frame for frame in self.frames.values()
            if not frame.segmentation_complete
        ]

    def get_pending_reconstruction(self) -> list[FrameEntry]:
        """Get frames pending 3D reconstruction."""
        return [
            frame for frame in self.frames.values()
            if frame.segmentation_complete and not frame.reconstruction_complete
        ]

    def get_pending_tracking(self) -> list[FrameEntry]:
        """Get frames pending tracking."""
        return [
            frame for frame in self.frames.values()
            if frame.reconstruction_complete and not frame.tracking_complete
        ]

    def update_status(
        self,
        frame_id: str,
        segmentation_complete: bool | None = None,
        reconstruction_complete: bool | None = None,
        tracking_complete: bool | None = None,
        detection_count: int | None = None,
    ) -> None:
        """Update processing status for a frame."""
        frame = self.frames.get(frame_id)
        if frame is None:
            logger.warning(f"Frame not found: {frame_id}")
            return

        if segmentation_complete is not None:
            frame.segmentation_complete = segmentation_complete
        if reconstruction_complete is not None:
            frame.reconstruction_complete = reconstruction_complete
        if tracking_complete is not None:
            frame.tracking_complete = tracking_complete
        if detection_count is not None:
            frame.detection_count = detection_count

    def get_statistics(self) -> dict:
        """Get processing statistics."""
        total = len(self.frames)
        segmented = sum(1 for f in self.frames.values() if f.segmentation_complete)
        reconstructed = sum(1 for f in self.frames.values() if f.reconstruction_complete)
        tracked = sum(1 for f in self.frames.values() if f.tracking_complete)
        total_detections = sum(f.detection_count for f in self.frames.values())

        return {
            "total_frames": total,
            "segmentation_complete": segmented,
            "segmentation_pending": total - segmented,
            "reconstruction_complete": reconstructed,
            "reconstruction_pending": total - reconstructed,
            "tracking_complete": tracked,
            "tracking_pending": total - tracked,
            "total_detections": total_detections,
            "svo2_files": len(self.svo2_files),
        }

    def save(self, path: Path | None = None) -> Path:
        """
        Save registry to JSON file.

        Args:
            path: Optional path, defaults to output_dir/frame_registry.json
        """
        if path is None:
            path = self.output_dir / "frame_registry.json"

        data = {
            "output_dir": str(self.output_dir),
            "svo2_files": self.svo2_files,
            "total_frames": self.total_frames,
            "statistics": self.get_statistics(),
            "frames": [frame.to_dict() for frame in self.frames.values()],
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved frame registry: {path}")
        return path

    @classmethod
    def load(cls, path: Path) -> FrameRegistry:
        """Load registry from JSON file."""
        with open(path) as f:
            data = json.load(f)

        registry = cls(
            output_dir=Path(data["output_dir"]),
            svo2_files=data.get("svo2_files", []),
            total_frames=data.get("total_frames", 0),
        )

        for frame_data in data.get("frames", []):
            entry = FrameEntry.from_dict(frame_data)
            registry.frames[entry.frame_id] = entry

        logger.info(f"Loaded frame registry: {len(registry.frames)} frames")
        return registry

    @classmethod
    def from_extraction_result(cls, registry_file: Path) -> FrameRegistry:
        """Create registry from extraction result file."""
        with open(registry_file) as f:
            data = json.load(f)

        output_dir = registry_file.parent
        registry = cls(
            output_dir=output_dir,
            svo2_files=[data.get("svo2_file", "")],
            total_frames=data.get("total_frames", 0),
        )

        for frame_data in data.get("frames", []):
            entry = FrameEntry(
                frame_id=frame_data["frame_id"],
                sequence_index=frame_data["sequence_index"],
                svo2_frame_index=frame_data["svo2_frame_index"],
                svo2_file=frame_data["svo2_file"],
                timestamp_ns=frame_data["timestamp_ns"],
                image_left=frame_data.get("image_left"),
                image_right=frame_data.get("image_right"),
                depth=frame_data.get("depth"),
                point_cloud=frame_data.get("point_cloud"),
                imu=frame_data.get("imu"),
            )
            registry.frames[entry.frame_id] = entry

        return registry

    def iter_frames(self, sorted_by: str = "sequence_index"):
        """
        Iterate over frames in order.

        Args:
            sorted_by: Field to sort by (sequence_index, timestamp_ns, frame_id)
        """
        frames = list(self.frames.values())

        if sorted_by == "sequence_index":
            frames.sort(key=lambda f: f.sequence_index)
        elif sorted_by == "timestamp_ns":
            frames.sort(key=lambda f: f.timestamp_ns)
        elif sorted_by == "frame_id":
            frames.sort(key=lambda f: f.frame_id)

        yield from frames

    def get_frame_paths(self, frame_id: str) -> dict[str, Path | None]:
        """Get absolute paths for a frame's files."""
        frame = self.frames.get(frame_id)
        if frame is None:
            return {}

        paths = {}
        if frame.image_left:
            paths["image_left"] = self.output_dir / frame.image_left
        if frame.image_right:
            paths["image_right"] = self.output_dir / frame.image_right
        if frame.depth:
            paths["depth"] = self.output_dir / frame.depth
        if frame.point_cloud:
            paths["point_cloud"] = self.output_dir / frame.point_cloud
        if frame.imu:
            paths["imu"] = self.output_dir / frame.imu

        return paths
