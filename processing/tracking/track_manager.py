"""Track management and aggregation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import numpy as np

from processing.tracking.bytetrack import ByteTracker, ByteTrackConfig, STrack

logger = logging.getLogger(__name__)


@dataclass
class TrackPoint:
    """Single point in track trajectory."""

    frame_id: int
    timestamp_ns: int
    position: tuple[float, float, float]
    bbox_3d: tuple[float, ...] | None
    confidence: float


@dataclass
class Track:
    """Complete object track across frames."""

    track_id: int
    class_id: str
    class_name: str

    # Track bounds
    start_frame: int
    end_frame: int

    # Trajectory
    trajectory: list[TrackPoint] = field(default_factory=list)

    # Statistics
    total_frames: int = 0
    avg_confidence: float = 0.0

    def add_point(
        self,
        frame_id: int,
        timestamp_ns: int,
        position: tuple[float, float, float],
        bbox_3d: tuple[float, ...] | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Add a point to the track trajectory."""
        self.trajectory.append(TrackPoint(
            frame_id=frame_id,
            timestamp_ns=timestamp_ns,
            position=position,
            bbox_3d=bbox_3d,
            confidence=confidence,
        ))

        # Update bounds
        self.end_frame = max(self.end_frame, frame_id)
        self.total_frames = len(self.trajectory)

        # Update average confidence
        confidences = [p.confidence for p in self.trajectory]
        self.avg_confidence = sum(confidences) / len(confidences)

    def get_position_at_frame(self, frame_id: int) -> tuple[float, float, float] | None:
        """Get position at specific frame."""
        for point in self.trajectory:
            if point.frame_id == frame_id:
                return point.position
        return None

    def get_trajectory_array(self) -> np.ndarray:
        """Get trajectory as numpy array (N x 3)."""
        positions = [p.position for p in self.trajectory]
        return np.array(positions)

    def interpolate_position(self, frame_id: int) -> tuple[float, float, float] | None:
        """Interpolate position at frame (if between known frames)."""
        if not self.trajectory:
            return None

        # Find surrounding frames
        before = None
        after = None

        for point in self.trajectory:
            if point.frame_id == frame_id:
                return point.position
            elif point.frame_id < frame_id:
                before = point
            elif point.frame_id > frame_id and after is None:
                after = point
                break

        if before is None or after is None:
            return None

        # Linear interpolation
        t = (frame_id - before.frame_id) / (after.frame_id - before.frame_id)

        pos = tuple(
            before.position[i] + t * (after.position[i] - before.position[i])
            for i in range(3)
        )

        return pos

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "total_frames": self.total_frames,
            "avg_confidence": self.avg_confidence,
            "trajectory": [
                {
                    "frame_id": p.frame_id,
                    "timestamp_ns": p.timestamp_ns,
                    "position": list(p.position),
                    "bbox_3d": list(p.bbox_3d) if p.bbox_3d else None,
                    "confidence": p.confidence,
                }
                for p in self.trajectory
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Track:
        """Create from dictionary."""
        track = cls(
            track_id=data["track_id"],
            class_id=data["class_id"],
            class_name=data["class_name"],
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            total_frames=data.get("total_frames", 0),
            avg_confidence=data.get("avg_confidence", 0.0),
        )

        for p in data.get("trajectory", []):
            track.trajectory.append(TrackPoint(
                frame_id=p["frame_id"],
                timestamp_ns=p["timestamp_ns"],
                position=tuple(p["position"]),
                bbox_3d=tuple(p["bbox_3d"]) if p.get("bbox_3d") else None,
                confidence=p["confidence"],
            ))

        return track


class TrackManager:
    """
    Manages object tracking across a video sequence.

    Wraps ByteTracker and provides:
    - Track aggregation across frames
    - Track persistence and loading
    - Track statistics and analysis
    """

    def __init__(self, config: ByteTrackConfig | None = None):
        """
        Initialize track manager.

        Args:
            config: ByteTrack configuration
        """
        self.tracker = ByteTracker(config)
        self._tracks: dict[int, Track] = {}
        self._frame_id = 0

    def update(
        self,
        detections: list[dict],
        frame_id: int,
        timestamp_ns: int = 0,
    ) -> list[Track]:
        """
        Update tracker with new frame detections.

        Args:
            detections: List of detection dicts with keys:
                - bbox_3d: (x, y, z, w, h, l, rotation_y)
                - class_id: Object class ID
                - class_name: Object class name
                - score: Detection confidence
            frame_id: Current frame index
            timestamp_ns: Frame timestamp in nanoseconds

        Returns:
            List of currently active tracks
        """
        self._frame_id = frame_id

        # Update tracker
        active_stracks = self.tracker.update(detections, frame_id)

        # Update track records
        active_tracks = []

        for strack in active_stracks:
            # Get or create track record
            if strack.track_id not in self._tracks:
                self._tracks[strack.track_id] = Track(
                    track_id=strack.track_id,
                    class_id=strack.class_id,
                    class_name=strack.class_name,
                    start_frame=frame_id,
                    end_frame=frame_id,
                )

            track = self._tracks[strack.track_id]

            # Add current position
            position = strack.get_position()
            track.add_point(
                frame_id=frame_id,
                timestamp_ns=timestamp_ns,
                position=position,
                bbox_3d=strack.bbox_3d,
                confidence=strack.score,
            )

            active_tracks.append(track)

        return active_tracks

    def get_track(self, track_id: int) -> Track | None:
        """Get specific track by ID."""
        return self._tracks.get(track_id)

    def get_all_tracks(self) -> list[Track]:
        """Get all tracks (including completed)."""
        return list(self._tracks.values())

    def get_active_tracks(self) -> list[Track]:
        """Get currently active tracks."""
        active_ids = {t.track_id for t in self.tracker.get_all_tracks()}
        return [t for t in self._tracks.values() if t.track_id in active_ids]

    def get_tracks_at_frame(self, frame_id: int) -> list[Track]:
        """Get tracks present at specific frame."""
        return [
            t for t in self._tracks.values()
            if t.start_frame <= frame_id <= t.end_frame
        ]

    def iter_tracks(self) -> Iterator[Track]:
        """Iterate over all tracks."""
        yield from self._tracks.values()

    def get_statistics(self) -> dict:
        """Get tracking statistics."""
        tracks = list(self._tracks.values())

        if not tracks:
            return {
                "total_tracks": 0,
                "active_tracks": 0,
                "avg_track_length": 0,
                "max_track_length": 0,
                "total_frames": self._frame_id + 1,
            }

        lengths = [t.total_frames for t in tracks]
        active_count = len(self.get_active_tracks())

        # Class distribution
        class_counts = {}
        for track in tracks:
            class_counts[track.class_name] = class_counts.get(track.class_name, 0) + 1

        return {
            "total_tracks": len(tracks),
            "active_tracks": active_count,
            "avg_track_length": sum(lengths) / len(lengths),
            "max_track_length": max(lengths),
            "min_track_length": min(lengths),
            "total_frames": self._frame_id + 1,
            "class_distribution": class_counts,
        }

    def save(self, path: Path) -> None:
        """
        Save tracks to JSON file.

        Args:
            path: Output file path
        """
        data = {
            "total_tracks": len(self._tracks),
            "total_frames": self._frame_id + 1,
            "statistics": self.get_statistics(),
            "tracks": [t.to_dict() for t in self._tracks.values()],
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self._tracks)} tracks to {path}")

    def load(self, path: Path) -> None:
        """
        Load tracks from JSON file.

        Args:
            path: Input file path
        """
        with open(path) as f:
            data = json.load(f)

        self._tracks.clear()
        self._frame_id = data.get("total_frames", 0) - 1

        for track_data in data.get("tracks", []):
            track = Track.from_dict(track_data)
            self._tracks[track.track_id] = track

        logger.info(f"Loaded {len(self._tracks)} tracks from {path}")

    def reset(self) -> None:
        """Reset all tracking state."""
        self.tracker.reset()
        self._tracks.clear()
        self._frame_id = 0

    def filter_short_tracks(self, min_length: int = 5) -> None:
        """
        Remove tracks shorter than minimum length.

        Args:
            min_length: Minimum track length to keep
        """
        to_remove = [
            track_id for track_id, track in self._tracks.items()
            if track.total_frames < min_length
        ]

        for track_id in to_remove:
            del self._tracks[track_id]

        logger.info(f"Removed {len(to_remove)} short tracks (min_length={min_length})")

    def merge_tracks(
        self,
        track_id1: int,
        track_id2: int,
    ) -> Track | None:
        """
        Merge two tracks (for handling ID switches).

        Args:
            track_id1: First track ID (will be kept)
            track_id2: Second track ID (will be merged into first)

        Returns:
            Merged track or None if merge failed
        """
        track1 = self._tracks.get(track_id1)
        track2 = self._tracks.get(track_id2)

        if track1 is None or track2 is None:
            return None

        # Merge trajectories
        all_points = track1.trajectory + track2.trajectory
        all_points.sort(key=lambda p: p.frame_id)

        track1.trajectory = all_points
        track1.start_frame = min(track1.start_frame, track2.start_frame)
        track1.end_frame = max(track1.end_frame, track2.end_frame)
        track1.total_frames = len(all_points)

        # Remove merged track
        del self._tracks[track_id2]

        return track1
