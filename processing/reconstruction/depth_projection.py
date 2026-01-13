"""Depth map projection to 3D points."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class CameraIntrinsics:
    """Camera intrinsic parameters."""

    fx: float  # Focal length x
    fy: float  # Focal length y
    cx: float  # Principal point x
    cy: float  # Principal point y
    width: int
    height: int

    @classmethod
    def from_calibration(cls, calib: dict) -> CameraIntrinsics:
        """Create from calibration dictionary."""
        return cls(
            fx=calib["fx"],
            fy=calib["fy"],
            cx=calib["cx"],
            cy=calib["cy"],
            width=calib.get("width", 1280),
            height=calib.get("height", 720),
        )

    def to_matrix(self) -> NDArray[np.float64]:
        """Convert to 3x3 intrinsic matrix."""
        return np.array([
            [self.fx, 0, self.cx],
            [0, self.fy, self.cy],
            [0, 0, 1],
        ], dtype=np.float64)

    def to_inverse_matrix(self) -> NDArray[np.float64]:
        """Get inverse intrinsic matrix."""
        return np.linalg.inv(self.to_matrix())


class DepthProjector:
    """
    Projects 2D points with depth to 3D coordinates.

    Uses camera intrinsics to back-project pixels to 3D space.
    """

    def __init__(self, intrinsics: CameraIntrinsics):
        """
        Initialize depth projector.

        Args:
            intrinsics: Camera intrinsic parameters
        """
        self.intrinsics = intrinsics

        # Pre-compute pixel coordinates grid
        self._u_grid, self._v_grid = np.meshgrid(
            np.arange(intrinsics.width),
            np.arange(intrinsics.height),
        )

        # Pre-compute normalized coordinates
        self._x_norm = (self._u_grid - intrinsics.cx) / intrinsics.fx
        self._y_norm = (self._v_grid - intrinsics.cy) / intrinsics.fy

    def project_depth_to_3d(
        self,
        depth: NDArray[np.float32],
        mask: NDArray[np.bool_] | None = None,
    ) -> NDArray[np.float32]:
        """
        Project depth map to 3D point cloud.

        Args:
            depth: Depth map (H x W, float32, in meters)
            mask: Optional binary mask (H x W) to filter points

        Returns:
            Point cloud (N x 3, float32) in camera coordinates
        """
        # Apply mask if provided
        if mask is not None:
            valid = mask & np.isfinite(depth) & (depth > 0)
        else:
            valid = np.isfinite(depth) & (depth > 0)

        # Get valid depth values
        z = depth[valid]

        # Back-project to 3D
        x = self._x_norm[valid] * z
        y = self._y_norm[valid] * z

        # Stack into point cloud (N x 3)
        points = np.stack([x, y, z], axis=-1).astype(np.float32)

        return points

    def project_pixel_to_3d(
        self,
        u: float,
        v: float,
        depth: float,
    ) -> tuple[float, float, float]:
        """
        Project a single pixel with depth to 3D.

        Args:
            u: Pixel x coordinate
            v: Pixel y coordinate
            depth: Depth value in meters

        Returns:
            (x, y, z) in camera coordinates
        """
        x = (u - self.intrinsics.cx) / self.intrinsics.fx * depth
        y = (v - self.intrinsics.cy) / self.intrinsics.fy * depth
        z = depth

        return (x, y, z)

    def project_bbox_to_3d(
        self,
        bbox: tuple[float, float, float, float],
        depth: NDArray[np.float32],
        mask: NDArray[np.bool_] | None = None,
    ) -> NDArray[np.float32]:
        """
        Project 2D bounding box region to 3D point cloud.

        Args:
            bbox: 2D bounding box (x1, y1, x2, y2)
            depth: Full depth map
            mask: Optional segmentation mask

        Returns:
            Point cloud for the bounding box region
        """
        x1, y1, x2, y2 = map(int, bbox)

        # Clamp to image bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(self.intrinsics.width, x2)
        y2 = min(self.intrinsics.height, y2)

        # Extract region
        depth_region = depth[y1:y2, x1:x2]

        if mask is not None:
            mask_region = mask[y1:y2, x1:x2]
        else:
            mask_region = None

        # Create local projector for the region
        h, w = depth_region.shape
        u_local, v_local = np.meshgrid(np.arange(w), np.arange(h))

        # Adjust for region offset
        u_global = u_local + x1
        v_global = v_local + y1

        # Compute 3D coordinates
        valid = np.isfinite(depth_region) & (depth_region > 0)
        if mask_region is not None:
            valid &= mask_region

        z = depth_region[valid]
        x = (u_global[valid] - self.intrinsics.cx) / self.intrinsics.fx * z
        y = (v_global[valid] - self.intrinsics.cy) / self.intrinsics.fy * z

        return np.stack([x, y, z], axis=-1).astype(np.float32)

    @staticmethod
    def transform_camera_to_kitti(
        points: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        """
        Transform points from ZED camera to KITTI coordinate system.

        ZED Camera: X-right, Y-down, Z-forward
        KITTI Velodyne: X-forward, Y-left, Z-up

        Transform:
            X_kitti = Z_zed
            Y_kitti = -X_zed
            Z_kitti = -Y_zed

        Args:
            points: Point cloud in camera coordinates (N x 3)

        Returns:
            Point cloud in KITTI coordinates (N x 3)
        """
        kitti_points = np.zeros_like(points)
        kitti_points[:, 0] = points[:, 2]   # X_kitti = Z_zed
        kitti_points[:, 1] = -points[:, 0]  # Y_kitti = -X_zed
        kitti_points[:, 2] = -points[:, 1]  # Z_kitti = -Y_zed

        return kitti_points

    @staticmethod
    def transform_kitti_to_camera(
        points: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        """
        Transform points from KITTI to camera coordinate system.

        Inverse of transform_camera_to_kitti.
        """
        cam_points = np.zeros_like(points)
        cam_points[:, 0] = -points[:, 1]  # X_zed = -Y_kitti
        cam_points[:, 1] = -points[:, 2]  # Y_zed = -Z_kitti
        cam_points[:, 2] = points[:, 0]   # Z_zed = X_kitti

        return cam_points

    @staticmethod
    def calculate_center_patch_distance(
        mask: NDArray[np.bool_],
        depth: NDArray[np.float32],
        patch_ratio: float = 0.10,
        min_samples: int = 10,
    ) -> float | None:
        """
        Calculate average depth from center patch of mask.

        Uses a circular patch centered at the mask centroid, with area equal
        to patch_ratio of the total mask area. This avoids edge noise from
        depth bleeding at object boundaries.

        Args:
            mask: Boolean segmentation mask (H x W)
            depth: Depth map in meters (H x W, float32)
            patch_ratio: Fraction of mask area for center patch (default 10%)
            min_samples: Minimum valid depth samples required

        Returns:
            Average depth in meters, or None if insufficient valid data
        """
        # Find mask pixels
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return None

        # Calculate centroid
        cx = xs.mean()
        cy = ys.mean()

        # Calculate center patch radius for desired area ratio
        mask_area = mask.sum()
        patch_area = mask_area * patch_ratio
        patch_radius = np.sqrt(patch_area / np.pi)

        # Create circular center patch mask
        y_coords, x_coords = np.ogrid[:mask.shape[0], :mask.shape[1]]
        distances_from_center = np.sqrt(
            (x_coords - cx) ** 2 + (y_coords - cy) ** 2
        )
        center_patch = (distances_from_center <= patch_radius) & mask

        # Sample depth values within the center patch
        depth_values = depth[center_patch]

        # Filter for valid (finite, positive) depth values
        valid = np.isfinite(depth_values) & (depth_values > 0)

        if valid.sum() < min_samples:
            return None

        return float(depth_values[valid].mean())
