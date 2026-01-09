"""ByteTrack multi-object tracker implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import linear_sum_assignment

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class TrackState(Enum):
    """Track lifecycle state."""

    TENTATIVE = 0  # New track, not yet confirmed
    CONFIRMED = 1  # Confirmed track
    DELETED = 2    # Track marked for deletion


@dataclass
class KalmanFilter:
    """Simple Kalman filter for track state estimation."""

    # State: [x, y, z, vx, vy, vz, w, h, l]
    # Position, velocity, and dimensions

    state: NDArray[np.float64]
    covariance: NDArray[np.float64]

    # Process and measurement noise
    process_noise: float = 0.05
    measurement_noise: float = 0.1

    def __post_init__(self):
        """Initialize covariance if not provided."""
        if self.covariance is None:
            self.covariance = np.eye(9) * 0.1

    def predict(self, dt: float = 1.0) -> None:
        """Predict next state."""
        # State transition matrix
        F = np.eye(9)
        F[0, 3] = dt  # x += vx * dt
        F[1, 4] = dt  # y += vy * dt
        F[2, 5] = dt  # z += vz * dt

        # Process noise
        Q = np.eye(9) * self.process_noise

        self.state = F @ self.state
        self.covariance = F @ self.covariance @ F.T + Q

    def update(self, measurement: NDArray[np.float64]) -> None:
        """Update state with measurement."""
        # Measurement matrix (observe position and dimensions)
        H = np.zeros((6, 9))
        H[0, 0] = 1  # x
        H[1, 1] = 1  # y
        H[2, 2] = 1  # z
        H[3, 6] = 1  # w
        H[4, 7] = 1  # h
        H[5, 8] = 1  # l

        # Measurement noise
        R = np.eye(6) * self.measurement_noise

        # Kalman gain
        S = H @ self.covariance @ H.T + R
        K = self.covariance @ H.T @ np.linalg.inv(S)

        # Update
        z = measurement[:6]  # [x, y, z, w, h, l]
        y = z - H @ self.state
        self.state = self.state + K @ y
        self.covariance = (np.eye(9) - K @ H) @ self.covariance

    @property
    def position(self) -> tuple[float, float, float]:
        """Get current position estimate."""
        return tuple(self.state[:3].tolist())

    @property
    def velocity(self) -> tuple[float, float, float]:
        """Get current velocity estimate."""
        return tuple(self.state[3:6].tolist())

    @property
    def dimensions(self) -> tuple[float, float, float]:
        """Get current dimension estimate (w, h, l)."""
        return tuple(self.state[6:9].tolist())


@dataclass
class STrack:
    """Single object track."""

    track_id: int
    state: TrackState = TrackState.TENTATIVE
    frame_id: int = 0
    start_frame: int = 0

    # Kalman filter
    kalman: KalmanFilter | None = None

    # Detection info
    class_id: str = ""
    class_name: str = ""
    score: float = 0.0

    # 3D bounding box (for visualization)
    bbox_3d: tuple[float, ...] | None = None

    # Track history
    history: list[dict] = field(default_factory=list)

    # Tracking metrics
    hits: int = 0
    time_since_update: int = 0

    @classmethod
    def from_detection(
        cls,
        track_id: int,
        bbox_3d: tuple[float, float, float, float, float, float, float],
        frame_id: int,
        class_id: str = "",
        class_name: str = "",
        score: float = 1.0,
    ) -> STrack:
        """
        Create track from 3D detection.

        Args:
            track_id: Unique track ID
            bbox_3d: (x, y, z, w, h, l, rotation_y)
            frame_id: Current frame index
            class_id: Object class ID
            class_name: Object class name
            score: Detection confidence

        Returns:
            New STrack instance
        """
        x, y, z, w, h, l, rot = bbox_3d

        # Initialize Kalman filter state
        state = np.array([x, y, z, 0, 0, 0, w, h, l], dtype=np.float64)
        covariance = np.eye(9) * 0.1

        kalman = KalmanFilter(state=state, covariance=covariance)

        return cls(
            track_id=track_id,
            state=TrackState.TENTATIVE,
            frame_id=frame_id,
            start_frame=frame_id,
            kalman=kalman,
            class_id=class_id,
            class_name=class_name,
            score=score,
            bbox_3d=bbox_3d,
            hits=1,
        )

    def predict(self) -> None:
        """Predict next state."""
        if self.kalman is not None:
            self.kalman.predict()
        self.time_since_update += 1

    def update(
        self,
        bbox_3d: tuple[float, float, float, float, float, float, float],
        frame_id: int,
        score: float,
    ) -> None:
        """
        Update track with new detection.

        Args:
            bbox_3d: (x, y, z, w, h, l, rotation_y)
            frame_id: Current frame index
            score: Detection confidence
        """
        x, y, z, w, h, l, rot = bbox_3d

        if self.kalman is not None:
            measurement = np.array([x, y, z, w, h, l], dtype=np.float64)
            self.kalman.update(measurement)

        self.bbox_3d = bbox_3d
        self.frame_id = frame_id
        self.score = score
        self.hits += 1
        self.time_since_update = 0

        # Update state
        if self.state == TrackState.TENTATIVE and self.hits >= 3:
            self.state = TrackState.CONFIRMED

        # Add to history
        self.history.append({
            "frame_id": frame_id,
            "position": (x, y, z),
            "score": score,
        })

    def mark_deleted(self) -> None:
        """Mark track for deletion."""
        self.state = TrackState.DELETED

    @property
    def is_confirmed(self) -> bool:
        """Check if track is confirmed."""
        return self.state == TrackState.CONFIRMED

    @property
    def is_deleted(self) -> bool:
        """Check if track is deleted."""
        return self.state == TrackState.DELETED

    @property
    def age(self) -> int:
        """Get track age in frames."""
        return self.frame_id - self.start_frame

    def get_position(self) -> tuple[float, float, float]:
        """Get current estimated position."""
        if self.kalman is not None:
            return self.kalman.position
        if self.bbox_3d is not None:
            return (self.bbox_3d[0], self.bbox_3d[1], self.bbox_3d[2])
        return (0.0, 0.0, 0.0)


@dataclass
class ByteTrackConfig:
    """Configuration for ByteTrack."""

    # Association thresholds
    track_thresh: float = 0.5     # Threshold for high-score detections
    track_buffer: int = 30        # Frames to keep lost track
    match_thresh: float = 0.8     # IoU threshold for matching

    # Track management
    min_box_area: float = 10.0    # Minimum 3D box volume
    confirm_hits: int = 3         # Hits to confirm track

    # 3D IoU settings
    use_3d_iou: bool = True       # Use 3D IoU for matching


class ByteTracker:
    """
    ByteTrack multi-object tracker.

    Based on the ByteTrack paper (Zhang et al., 2021) adapted for
    3D object tracking with Kalman filtering.
    """

    def __init__(self, config: ByteTrackConfig | None = None):
        """
        Initialize tracker.

        Args:
            config: Tracker configuration
        """
        self.config = config or ByteTrackConfig()

        self._tracks: list[STrack] = []
        self._lost_tracks: list[STrack] = []
        self._removed_tracks: list[STrack] = []

        self._next_track_id = 1
        self._frame_id = 0

    def update(
        self,
        detections: list[dict],
        frame_id: int,
    ) -> list[STrack]:
        """
        Update tracker with new detections.

        Args:
            detections: List of detection dicts with keys:
                - bbox_3d: (x, y, z, w, h, l, rotation_y)
                - class_id: Object class ID
                - class_name: Object class name
                - score: Detection confidence
            frame_id: Current frame index

        Returns:
            List of active tracks (confirmed only)
        """
        self._frame_id = frame_id

        # Separate high and low score detections
        high_score = []
        low_score = []

        for det in detections:
            if det["score"] >= self.config.track_thresh:
                high_score.append(det)
            else:
                low_score.append(det)

        # Predict track positions
        for track in self._tracks:
            track.predict()

        for track in self._lost_tracks:
            track.predict()

        # First association: high-score detections with confirmed tracks
        confirmed_tracks = [t for t in self._tracks if t.is_confirmed]
        unconfirmed_tracks = [t for t in self._tracks if not t.is_confirmed]

        matches, unmatched_tracks, unmatched_dets = self._associate(
            confirmed_tracks,
            high_score,
        )

        # Update matched tracks
        for track_idx, det_idx in matches:
            track = confirmed_tracks[track_idx]
            det = high_score[det_idx]
            track.update(det["bbox_3d"], frame_id, det["score"])

        # Second association: remaining tracks with low-score detections
        remaining_tracks = [confirmed_tracks[i] for i in unmatched_tracks]

        matches2, unmatched_tracks2, unmatched_dets2 = self._associate(
            remaining_tracks,
            low_score,
        )

        for track_idx, det_idx in matches2:
            track = remaining_tracks[track_idx]
            det = low_score[det_idx]
            track.update(det["bbox_3d"], frame_id, det["score"])

        # Mark unmatched tracks as lost
        for track_idx in unmatched_tracks2:
            track = remaining_tracks[track_idx]
            if track.time_since_update > self.config.track_buffer:
                track.mark_deleted()
            else:
                self._lost_tracks.append(track)

        # Third association: unconfirmed tracks with unmatched high-score detections
        remaining_dets = [high_score[i] for i in unmatched_dets]

        matches3, unmatched_unc, unmatched_dets3 = self._associate(
            unconfirmed_tracks,
            remaining_dets,
        )

        for track_idx, det_idx in matches3:
            track = unconfirmed_tracks[track_idx]
            det = remaining_dets[det_idx]
            track.update(det["bbox_3d"], frame_id, det["score"])

        # Remove old unconfirmed tracks
        for track_idx in unmatched_unc:
            track = unconfirmed_tracks[track_idx]
            track.mark_deleted()

        # Try to recover lost tracks
        remaining_dets2 = [remaining_dets[i] for i in unmatched_dets3]

        matches4, unmatched_lost, unmatched_dets4 = self._associate(
            self._lost_tracks,
            remaining_dets2,
        )

        for track_idx, det_idx in matches4:
            track = self._lost_tracks[track_idx]
            det = remaining_dets2[det_idx]
            track.update(det["bbox_3d"], frame_id, det["score"])
            track.state = TrackState.CONFIRMED
            self._tracks.append(track)

        # Remove old lost tracks
        for track in self._lost_tracks:
            if track.time_since_update > self.config.track_buffer:
                track.mark_deleted()

        # Initialize new tracks from unmatched detections
        for det_idx in unmatched_dets4:
            det = remaining_dets2[det_idx]
            if det["score"] >= self.config.track_thresh:
                track = STrack.from_detection(
                    track_id=self._next_track_id,
                    bbox_3d=det["bbox_3d"],
                    frame_id=frame_id,
                    class_id=det.get("class_id", ""),
                    class_name=det.get("class_name", ""),
                    score=det["score"],
                )
                self._next_track_id += 1
                self._tracks.append(track)

        # Update track lists
        self._tracks = [t for t in self._tracks if not t.is_deleted]
        self._lost_tracks = [t for t in self._lost_tracks if not t.is_deleted and t not in self._tracks]
        self._removed_tracks.extend([t for t in self._tracks if t.is_deleted])

        return [t for t in self._tracks if t.is_confirmed]

    def _associate(
        self,
        tracks: list[STrack],
        detections: list[dict],
    ) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        """
        Associate tracks with detections.

        Args:
            tracks: List of tracks
            detections: List of detection dicts

        Returns:
            Tuple of (matches, unmatched_tracks, unmatched_detections)
        """
        if len(tracks) == 0 or len(detections) == 0:
            return [], list(range(len(tracks))), list(range(len(detections)))

        # Compute cost matrix
        cost_matrix = self._compute_cost_matrix(tracks, detections)

        # Hungarian algorithm
        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        matches = []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_dets = list(range(len(detections)))

        for row, col in zip(row_indices, col_indices):
            if cost_matrix[row, col] <= 1 - self.config.match_thresh:
                matches.append((row, col))
                unmatched_tracks.remove(row)
                unmatched_dets.remove(col)

        return matches, unmatched_tracks, unmatched_dets

    def _compute_cost_matrix(
        self,
        tracks: list[STrack],
        detections: list[dict],
    ) -> NDArray[np.float64]:
        """Compute association cost matrix."""
        n_tracks = len(tracks)
        n_dets = len(detections)

        cost_matrix = np.zeros((n_tracks, n_dets), dtype=np.float64)

        for i, track in enumerate(tracks):
            for j, det in enumerate(detections):
                if self.config.use_3d_iou:
                    iou = self._compute_3d_iou(track, det["bbox_3d"])
                else:
                    iou = self._compute_center_distance(track, det["bbox_3d"])

                cost_matrix[i, j] = 1 - iou

        return cost_matrix

    def _compute_3d_iou(
        self,
        track: STrack,
        bbox_3d: tuple[float, ...],
    ) -> float:
        """
        Compute 3D IoU between track and detection.

        Simplified axis-aligned IoU computation.
        """
        if track.bbox_3d is None:
            return 0.0

        t_x, t_y, t_z, t_w, t_h, t_l, _ = track.bbox_3d
        d_x, d_y, d_z, d_w, d_h, d_l, _ = bbox_3d

        # Compute overlap in each dimension
        x_overlap = max(0, min(t_x + t_l/2, d_x + d_l/2) - max(t_x - t_l/2, d_x - d_l/2))
        y_overlap = max(0, min(t_y + t_w/2, d_y + d_w/2) - max(t_y - t_w/2, d_y - d_w/2))
        z_overlap = max(0, min(t_z + t_h/2, d_z + d_h/2) - max(t_z - t_h/2, d_z - d_h/2))

        intersection = x_overlap * y_overlap * z_overlap
        union = t_w * t_h * t_l + d_w * d_h * d_l - intersection

        if union <= 0:
            return 0.0

        return float(intersection / union)

    def _compute_center_distance(
        self,
        track: STrack,
        bbox_3d: tuple[float, ...],
    ) -> float:
        """Compute normalized center distance (1 - distance) as IoU substitute."""
        t_pos = track.get_position()
        d_pos = bbox_3d[:3]

        distance = np.sqrt(sum((t - d) ** 2 for t, d in zip(t_pos, d_pos)))

        # Normalize: assume max relevant distance is 50m
        max_dist = 50.0
        normalized = 1 - min(distance / max_dist, 1.0)

        return float(normalized)

    def get_all_tracks(self) -> list[STrack]:
        """Get all active tracks (including unconfirmed)."""
        return self._tracks.copy()

    def get_track_by_id(self, track_id: int) -> STrack | None:
        """Get specific track by ID."""
        for track in self._tracks:
            if track.track_id == track_id:
                return track
        return None

    def reset(self) -> None:
        """Reset tracker state."""
        self._tracks.clear()
        self._lost_tracks.clear()
        self._removed_tracks.clear()
        self._next_track_id = 1
        self._frame_id = 0
