"""Point cloud processing with Open3D."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

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


@dataclass
class PointCloudStats:
    """Statistics about a point cloud."""

    num_points: int
    centroid: tuple[float, float, float]
    min_bound: tuple[float, float, float]
    max_bound: tuple[float, float, float]
    mean_z: float  # Mean depth
    std_z: float   # Depth standard deviation


class PointCloudProcessor:
    """
    Point cloud processing utilities using Open3D.

    Provides filtering, downsampling, and analysis functions.
    """

    def __init__(self):
        """Initialize processor."""
        if not OPEN3D_AVAILABLE:
            logger.warning("Open3D not available - some functions will be limited")

    def filter_outliers(
        self,
        points: NDArray[np.float32],
        nb_neighbors: int = 20,
        std_ratio: float = 2.0,
    ) -> NDArray[np.float32]:
        """
        Remove statistical outliers from point cloud.

        Args:
            points: Input point cloud (N x 3)
            nb_neighbors: Number of neighbors for statistical analysis
            std_ratio: Standard deviation threshold

        Returns:
            Filtered point cloud
        """
        if len(points) < nb_neighbors:
            return points

        if not OPEN3D_AVAILABLE:
            # Fallback: simple distance-based filtering
            centroid = np.mean(points, axis=0)
            distances = np.linalg.norm(points - centroid, axis=1)
            threshold = np.mean(distances) + std_ratio * np.std(distances)
            return points[distances <= threshold]

        # Convert to Open3D point cloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        # Statistical outlier removal
        _, inlier_indices = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors,
            std_ratio=std_ratio,
        )

        return points[inlier_indices]

    def filter_by_distance(
        self,
        points: NDArray[np.float32],
        min_distance: float = 0.3,
        max_distance: float = 100.0,
    ) -> NDArray[np.float32]:
        """
        Filter points by distance from origin.

        Args:
            points: Input point cloud (N x 3)
            min_distance: Minimum distance threshold
            max_distance: Maximum distance threshold

        Returns:
            Filtered point cloud
        """
        distances = np.linalg.norm(points, axis=1)
        mask = (distances >= min_distance) & (distances <= max_distance)
        return points[mask]

    def filter_by_height(
        self,
        points: NDArray[np.float32],
        min_height: float | None = None,
        max_height: float | None = None,
        height_axis: int = 2,  # Z axis by default
    ) -> NDArray[np.float32]:
        """
        Filter points by height.

        Args:
            points: Input point cloud (N x 3)
            min_height: Minimum height threshold
            max_height: Maximum height threshold
            height_axis: Which axis represents height (0, 1, or 2)

        Returns:
            Filtered point cloud
        """
        heights = points[:, height_axis]

        mask = np.ones(len(points), dtype=bool)
        if min_height is not None:
            mask &= heights >= min_height
        if max_height is not None:
            mask &= heights <= max_height

        return points[mask]

    def downsample(
        self,
        points: NDArray[np.float32],
        voxel_size: float = 0.05,
    ) -> NDArray[np.float32]:
        """
        Downsample point cloud using voxel grid.

        Args:
            points: Input point cloud (N x 3)
            voxel_size: Size of voxels for downsampling (meters)

        Returns:
            Downsampled point cloud
        """
        if len(points) == 0:
            return points

        if not OPEN3D_AVAILABLE:
            # Fallback: random sampling
            target_points = int(len(points) * 0.1)  # Keep 10%
            if target_points < len(points):
                indices = np.random.choice(len(points), target_points, replace=False)
                return points[indices]
            return points

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        downsampled = pcd.voxel_down_sample(voxel_size=voxel_size)
        return np.asarray(downsampled.points).astype(np.float32)

    def compute_normals(
        self,
        points: NDArray[np.float32],
        radius: float = 0.1,
        max_nn: int = 30,
    ) -> NDArray[np.float32]:
        """
        Compute point normals.

        Args:
            points: Input point cloud (N x 3)
            radius: Search radius for normal estimation
            max_nn: Maximum number of neighbors

        Returns:
            Normal vectors (N x 3)
        """
        if not OPEN3D_AVAILABLE or len(points) == 0:
            return np.zeros_like(points)

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=radius,
                max_nn=max_nn,
            )
        )

        return np.asarray(pcd.normals).astype(np.float32)

    def get_statistics(
        self,
        points: NDArray[np.float32],
    ) -> PointCloudStats:
        """
        Compute point cloud statistics.

        Args:
            points: Input point cloud (N x 3)

        Returns:
            PointCloudStats object
        """
        if len(points) == 0:
            return PointCloudStats(
                num_points=0,
                centroid=(0.0, 0.0, 0.0),
                min_bound=(0.0, 0.0, 0.0),
                max_bound=(0.0, 0.0, 0.0),
                mean_z=0.0,
                std_z=0.0,
            )

        centroid = tuple(np.mean(points, axis=0).tolist())
        min_bound = tuple(np.min(points, axis=0).tolist())
        max_bound = tuple(np.max(points, axis=0).tolist())

        return PointCloudStats(
            num_points=len(points),
            centroid=centroid,
            min_bound=min_bound,
            max_bound=max_bound,
            mean_z=float(np.mean(points[:, 2])),
            std_z=float(np.std(points[:, 2])),
        )

    def segment_ground_plane(
        self,
        points: NDArray[np.float32],
        distance_threshold: float = 0.1,
        ransac_n: int = 3,
        num_iterations: int = 100,
    ) -> tuple[NDArray[np.float32], NDArray[np.float32], tuple[float, float, float, float]]:
        """
        Segment ground plane using RANSAC.

        Args:
            points: Input point cloud (N x 3)
            distance_threshold: RANSAC distance threshold
            ransac_n: Number of points for RANSAC
            num_iterations: Number of RANSAC iterations

        Returns:
            Tuple of (ground_points, non_ground_points, plane_coefficients)
        """
        if not OPEN3D_AVAILABLE or len(points) < 10:
            return np.array([]), points, (0.0, 0.0, 1.0, 0.0)

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        plane_model, inliers = pcd.segment_plane(
            distance_threshold=distance_threshold,
            ransac_n=ransac_n,
            num_iterations=num_iterations,
        )

        ground_indices = np.array(inliers)
        non_ground_indices = np.setdiff1d(np.arange(len(points)), ground_indices)

        ground_points = points[ground_indices]
        non_ground_points = points[non_ground_indices]

        return ground_points, non_ground_points, tuple(plane_model)

    def cluster_dbscan(
        self,
        points: NDArray[np.float32],
        eps: float = 0.5,
        min_points: int = 10,
    ) -> list[NDArray[np.float32]]:
        """
        Cluster point cloud using DBSCAN.

        Args:
            points: Input point cloud (N x 3)
            eps: DBSCAN epsilon (cluster distance)
            min_points: Minimum points per cluster

        Returns:
            List of point clouds, one per cluster
        """
        if not OPEN3D_AVAILABLE or len(points) < min_points:
            return [points] if len(points) > 0 else []

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        labels = np.array(pcd.cluster_dbscan(
            eps=eps,
            min_points=min_points,
        ))

        # Get unique labels (excluding noise label -1)
        unique_labels = np.unique(labels)
        unique_labels = unique_labels[unique_labels >= 0]

        clusters = []
        for label in unique_labels:
            cluster_points = points[labels == label]
            if len(cluster_points) >= min_points:
                clusters.append(cluster_points)

        return clusters

    def merge_point_clouds(
        self,
        point_clouds: list[NDArray[np.float32]],
        colors: list[NDArray[np.float32]] | None = None,
    ) -> tuple[NDArray[np.float32], NDArray[np.float32] | None]:
        """
        Merge multiple point clouds.

        Args:
            point_clouds: List of point clouds to merge
            colors: Optional list of color arrays

        Returns:
            Merged point cloud and optional merged colors
        """
        if not point_clouds:
            return np.array([]).reshape(0, 3), None

        merged_points = np.vstack(point_clouds)

        if colors is not None and len(colors) == len(point_clouds):
            merged_colors = np.vstack(colors)
        else:
            merged_colors = None

        return merged_points.astype(np.float32), merged_colors
