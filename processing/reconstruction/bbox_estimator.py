"""3D bounding box estimation from point clouds."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

from processing.reconstruction.point_cloud import PointCloudProcessor

# Check for Open3D availability
try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    o3d = None

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class BBoxMethod(Enum):
    """Bounding box estimation method."""

    AABB = "aabb"  # Axis-aligned bounding box
    OBB = "obb"    # Oriented bounding box
    PCA = "pca"    # PCA-based oriented box


@dataclass
class BBox3D:
    """3D bounding box in KITTI format."""

    # Center position (x, y, z) in KITTI coordinates
    center: tuple[float, float, float]

    # Dimensions (height, width, length) in meters
    # KITTI convention: height is Z, width is Y, length is X
    height: float  # Z dimension
    width: float   # Y dimension
    length: float  # X dimension

    # Rotation around vertical axis (radians)
    rotation_y: float

    # Additional info
    num_points: int = 0
    confidence: float = 1.0

    # Source detection info
    class_id: str = ""
    class_name: str = ""
    track_id: int = -1

    # Distance from camera (meters) - average depth of center patch
    distance: float | None = None

    def to_kitti_format(self) -> dict:
        """
        Convert to KITTI label format values.

        Returns dict with keys matching KITTI format:
        - type: Object class
        - truncated: Float from 0 (non-truncated) to 1 (truncated)
        - occluded: Integer (0, 1, 2, 3) indicating occlusion state
        - alpha: Observation angle
        - bbox: 2D bounding box (left, top, right, bottom)
        - dimensions: 3D object dimensions (height, width, length)
        - location: 3D object location (x, y, z) in camera coordinates
        - rotation_y: Rotation around Y-axis
        - score: Detection confidence
        """
        # Note: 2D bbox should be computed separately from projection
        return {
            "type": self.class_name or "Unknown",
            "truncated": 0.0,
            "occluded": 0,
            "alpha": self._compute_alpha(),
            "bbox": (-1, -1, -1, -1),  # Placeholder for 2D bbox
            "dimensions": (self.height, self.width, self.length),
            "location": self.center,
            "rotation_y": self.rotation_y,
            "score": self.confidence,
        }

    def _compute_alpha(self) -> float:
        """Compute observation angle (alpha) from rotation and position."""
        # Alpha = rotation_y - arctan2(x, z)
        x, _, z = self.center
        return float(self.rotation_y - np.arctan2(x, z))

    def to_kitti_string(self, bbox_2d: tuple[float, float, float, float] = (-1, -1, -1, -1)) -> str:
        """
        Convert to KITTI label format string.

        Args:
            bbox_2d: 2D bounding box (left, top, right, bottom)

        Returns:
            Single line in KITTI label format
        """
        kitti = self.to_kitti_format()
        kitti["bbox"] = bbox_2d

        return (
            f"{kitti['type']} "
            f"{kitti['truncated']:.2f} "
            f"{kitti['occluded']} "
            f"{kitti['alpha']:.2f} "
            f"{kitti['bbox'][0]:.2f} {kitti['bbox'][1]:.2f} "
            f"{kitti['bbox'][2]:.2f} {kitti['bbox'][3]:.2f} "
            f"{kitti['dimensions'][0]:.2f} {kitti['dimensions'][1]:.2f} {kitti['dimensions'][2]:.2f} "
            f"{kitti['location'][0]:.2f} {kitti['location'][1]:.2f} {kitti['location'][2]:.2f} "
            f"{kitti['rotation_y']:.2f}"
        )

    def get_corners(self) -> NDArray[np.float32]:
        """
        Get 8 corner points of the bounding box.

        Returns:
            Array of shape (8, 3) with corner coordinates
        """
        # Half dimensions
        l, w, h = self.length / 2, self.width / 2, self.height / 2

        # Corners in object coordinate system
        corners = np.array([
            [-l, -w, -h],
            [l, -w, -h],
            [l, w, -h],
            [-l, w, -h],
            [-l, -w, h],
            [l, -w, h],
            [l, w, h],
            [-l, w, h],
        ], dtype=np.float32)

        # Rotation matrix around Y axis
        c, s = np.cos(self.rotation_y), np.sin(self.rotation_y)
        R = np.array([
            [c, 0, s],
            [0, 1, 0],
            [-s, 0, c],
        ], dtype=np.float32)

        # Rotate and translate
        corners = corners @ R.T + np.array(self.center)

        return corners


# Size priors for common object classes (height, width, length in meters)
SIZE_PRIORS = {
    "car": {"height": (1.3, 1.8), "width": (1.5, 2.2), "length": (3.5, 5.5)},
    "truck": {"height": (2.5, 4.0), "width": (2.0, 2.8), "length": (5.0, 12.0)},
    "haul_truck": {"height": (4.0, 8.0), "width": (4.0, 8.0), "length": (8.0, 16.0)},
    "excavator": {"height": (3.0, 6.0), "width": (2.5, 5.0), "length": (6.0, 15.0)},
    "person": {"height": (1.4, 2.0), "width": (0.3, 0.8), "length": (0.3, 0.8)},
    "cyclist": {"height": (1.5, 2.0), "width": (0.5, 1.0), "length": (1.5, 2.5)},
}


class BBox3DEstimator:
    """
    Estimates 3D bounding boxes from object point clouds.

    Uses PCA-based orientation estimation and applies
    size priors for validation.
    """

    def __init__(
        self,
        method: BBoxMethod = BBoxMethod.PCA,
        min_points: int = 100,
        use_size_priors: bool = True,
    ):
        """
        Initialize estimator.

        Args:
            method: Bounding box estimation method
            min_points: Minimum points required for estimation
            use_size_priors: Whether to validate against size priors
        """
        self.method = method
        self.min_points = min_points
        self.use_size_priors = use_size_priors
        self.point_processor = PointCloudProcessor()

    def estimate(
        self,
        points: NDArray[np.float32],
        class_id: str = "",
        class_name: str = "",
        confidence: float = 1.0,
        filter_outliers: bool = True,
    ) -> BBox3D | None:
        """
        Estimate 3D bounding box from point cloud.

        Args:
            points: Object point cloud (N x 3) in KITTI coordinates
            class_id: Object class identifier
            class_name: Object class name
            confidence: Detection confidence
            filter_outliers: Whether to filter outliers first

        Returns:
            BBox3D object or None if estimation failed
        """
        if len(points) < self.min_points:
            logger.debug(f"Insufficient points: {len(points)} < {self.min_points}")
            return None

        # Filter outliers
        if filter_outliers:
            points = self.point_processor.filter_outliers(
                points,
                nb_neighbors=20,
                std_ratio=2.0,
            )

            if len(points) < self.min_points:
                logger.debug(f"Insufficient points after filtering: {len(points)}")
                return None

        # Estimate bounding box
        if self.method == BBoxMethod.AABB:
            bbox = self._estimate_aabb(points)
        elif self.method == BBoxMethod.OBB:
            bbox = self._estimate_obb(points)
        else:  # PCA
            bbox = self._estimate_pca(points)

        if bbox is None:
            return None

        # Set metadata
        bbox.class_id = class_id
        bbox.class_name = class_name
        bbox.confidence = confidence
        bbox.num_points = len(points)

        # Validate against size priors
        if self.use_size_priors and class_id:
            bbox = self._validate_size(bbox, class_id)

        return bbox

    def _estimate_aabb(self, points: NDArray[np.float32]) -> BBox3D:
        """Estimate axis-aligned bounding box."""
        min_pt = np.min(points, axis=0)
        max_pt = np.max(points, axis=0)

        center = tuple(((min_pt + max_pt) / 2).tolist())
        dims = max_pt - min_pt

        return BBox3D(
            center=center,
            length=float(dims[0]),  # X
            width=float(dims[1]),   # Y
            height=float(dims[2]),  # Z
            rotation_y=0.0,
        )

    def _estimate_obb(self, points: NDArray[np.float32]) -> BBox3D | None:
        """Estimate oriented bounding box using Open3D."""
        if not OPEN3D_AVAILABLE:
            return self._estimate_pca(points)

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        try:
            obb = pcd.get_oriented_bounding_box()

            center = tuple(obb.center.tolist())
            extent = obb.extent  # Full dimensions

            # Extract rotation angle around Y axis
            R = obb.R
            rotation_y = float(np.arctan2(R[0, 2], R[0, 0]))

            return BBox3D(
                center=center,
                length=float(extent[0]),
                width=float(extent[1]),
                height=float(extent[2]),
                rotation_y=rotation_y,
            )
        except Exception as e:
            logger.warning(f"OBB estimation failed: {e}")
            return self._estimate_aabb(points)

    def _estimate_pca(self, points: NDArray[np.float32]) -> BBox3D:
        """Estimate oriented bounding box using PCA."""
        # Center the points
        centroid = np.mean(points, axis=0)
        centered = points - centroid

        # PCA on XY plane (assuming Z is up in KITTI coordinates)
        xy_points = centered[:, :2]

        if len(xy_points) < 3:
            return self._estimate_aabb(points)

        # Compute covariance matrix
        cov = np.cov(xy_points.T)

        # Eigen decomposition
        eigenvalues, eigenvectors = np.linalg.eig(cov)

        # Sort by eigenvalue (descending)
        order = np.argsort(eigenvalues)[::-1]
        eigenvectors = eigenvectors[:, order]

        # Principal axis is the first eigenvector
        principal_axis = eigenvectors[:, 0]

        # Rotation angle around Z axis (in XY plane)
        rotation_y = float(np.arctan2(principal_axis[1], principal_axis[0]))

        # Rotate points to align with axes
        c, s = np.cos(-rotation_y), np.sin(-rotation_y)
        R = np.array([[c, -s], [s, c]])
        rotated_xy = centered[:, :2] @ R.T

        # Get bounding box in aligned coordinates
        min_xy = np.min(rotated_xy, axis=0)
        max_xy = np.max(rotated_xy, axis=0)
        min_z = np.min(centered[:, 2])
        max_z = np.max(centered[:, 2])

        # Dimensions
        length = float(max_xy[0] - min_xy[0])  # X
        width = float(max_xy[1] - min_xy[1])   # Y
        height = float(max_z - min_z)          # Z

        # Adjust center for Z offset
        center_z_offset = (max_z + min_z) / 2
        center = (
            float(centroid[0]),
            float(centroid[1]),
            float(centroid[2] + center_z_offset),
        )

        return BBox3D(
            center=center,
            length=length,
            width=width,
            height=height,
            rotation_y=rotation_y,
        )

    def _validate_size(self, bbox: BBox3D, class_id: str) -> BBox3D:
        """Validate and adjust bounding box against size priors."""
        priors = SIZE_PRIORS.get(class_id)
        if priors is None:
            return bbox

        # Check each dimension
        h_min, h_max = priors["height"]
        w_min, w_max = priors["width"]
        l_min, l_max = priors["length"]

        # Clamp dimensions to priors
        height = np.clip(bbox.height, h_min, h_max)
        width = np.clip(bbox.width, w_min, w_max)
        length = np.clip(bbox.length, l_min, l_max)

        # If dimensions are way off, reduce confidence
        dim_ratio = (
            (bbox.height / height if height > 0 else 1) *
            (bbox.width / width if width > 0 else 1) *
            (bbox.length / length if length > 0 else 1)
        )

        if dim_ratio < 0.5 or dim_ratio > 2.0:
            logger.debug(f"Large size mismatch for {class_id}: ratio={dim_ratio:.2f}")
            confidence = bbox.confidence * 0.7
        else:
            confidence = bbox.confidence

        return BBox3D(
            center=bbox.center,
            height=float(height),
            width=float(width),
            length=float(length),
            rotation_y=bbox.rotation_y,
            num_points=bbox.num_points,
            confidence=float(confidence),
            class_id=bbox.class_id,
            class_name=bbox.class_name,
            track_id=bbox.track_id,
            distance=bbox.distance,
        )

    def estimate_from_detection(
        self,
        mask: NDArray[np.bool_],
        depth: NDArray[np.float32],
        intrinsics: dict,
        class_id: str = "",
        class_name: str = "",
        confidence: float = 1.0,
    ) -> BBox3D | None:
        """
        Estimate 3D bounding box from 2D detection mask and depth.

        Args:
            mask: Binary segmentation mask (H x W)
            depth: Depth map in meters (H x W)
            intrinsics: Camera intrinsic parameters dict
            class_id: Object class identifier
            class_name: Object class name
            confidence: Detection confidence

        Returns:
            BBox3D object or None if estimation failed
        """
        from processing.reconstruction.depth_projection import CameraIntrinsics, DepthProjector

        # Create depth projector
        cam_intrinsics = CameraIntrinsics.from_calibration(intrinsics)
        projector = DepthProjector(cam_intrinsics)

        # Calculate center patch distance (10% area at mask centroid)
        distance = DepthProjector.calculate_center_patch_distance(mask, depth)

        # Project masked depth to 3D
        points = projector.project_depth_to_3d(depth, mask)

        if len(points) < self.min_points:
            return None

        # Transform to KITTI coordinates
        points = DepthProjector.transform_camera_to_kitti(points)

        # Estimate bounding box
        bbox = self.estimate(
            points,
            class_id=class_id,
            class_name=class_name,
            confidence=confidence,
        )

        # Set the calculated distance
        if bbox is not None:
            bbox.distance = distance

        return bbox
