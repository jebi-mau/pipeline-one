"""SVO2 data extraction to disk."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from processing.svo2.reader import CameraCalibration, FrameData, SVO2Reader

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for SVO2 extraction."""

    # What to extract
    extract_left_rgb: bool = True
    extract_right_rgb: bool = True
    extract_depth: bool = True
    extract_point_cloud: bool = True
    extract_imu: bool = True

    # Frame selection
    frame_skip: int = 1  # Process every Nth frame (1 = all frames)
    start_frame: int = 0
    end_frame: int | None = None

    # Output formats
    image_format: str = "png"  # png, jpg
    depth_format: str = "png16"  # png16 (16-bit), npy, exr
    point_cloud_format: str = "ply"  # ply, pcd, npy

    # Image compression
    jpeg_quality: int = 95
    png_compression: int = 3

    # Depth settings
    depth_scale: float = 1000.0  # Scale factor for 16-bit (1000 = mm)
    max_depth: float = 100.0  # Maximum depth in meters


@dataclass
class ExtractionResult:
    """Result of SVO2 extraction."""

    output_dir: Path
    frame_count: int
    extracted_frames: int
    failed_frames: int
    calibration_file: Path | None
    frame_registry_file: Path | None


class SVO2Extractor:
    """
    Extracts data from SVO2 files to disk in organized format.

    Output structure:
        output_dir/
        ├── image_2/        # Left RGB (000000.png, 000001.png, ...)
        ├── image_3/        # Right RGB
        ├── depth/          # Depth maps (16-bit PNG in mm or NPY)
        ├── velodyne/       # Point clouds (PLY)
        ├── oxts/           # IMU data (txt files)
        ├── calib/          # Camera calibration
        └── frame_registry.json
    """

    def __init__(
        self,
        reader: SVO2Reader,
        output_dir: str | Path,
        config: ExtractionConfig | None = None,
    ):
        """
        Initialize extractor.

        Args:
            reader: Open SVO2Reader instance
            output_dir: Directory to write extracted data
            config: Extraction configuration
        """
        self.reader = reader
        self.output_dir = Path(output_dir)
        self.config = config or ExtractionConfig()

        # Create output directories
        self._setup_directories()

        # Frame registry
        self._frame_registry: list[dict] = []

    def _setup_directories(self) -> None:
        """Create output directory structure."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.config.extract_left_rgb:
            (self.output_dir / "image_2").mkdir(exist_ok=True)

        if self.config.extract_right_rgb:
            (self.output_dir / "image_3").mkdir(exist_ok=True)

        if self.config.extract_depth:
            (self.output_dir / "depth").mkdir(exist_ok=True)

        if self.config.extract_point_cloud:
            (self.output_dir / "velodyne").mkdir(exist_ok=True)

        if self.config.extract_imu:
            (self.output_dir / "oxts").mkdir(exist_ok=True)

        (self.output_dir / "calib").mkdir(exist_ok=True)

    def extract(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ExtractionResult:
        """
        Extract all frames from the SVO2 file.

        Args:
            progress_callback: Optional callback(current, total, message)

        Returns:
            ExtractionResult with extraction statistics
        """
        if not self.reader.is_open:
            raise RuntimeError("SVO2 reader is not open")

        # Determine frame range
        total_frames = self.reader.frame_count
        end_frame = self.config.end_frame or total_frames

        frames_to_process = list(range(
            self.config.start_frame,
            min(end_frame, total_frames),
            self.config.frame_skip,
        ))

        extracted = 0
        failed = 0

        logger.info(f"Starting extraction: {len(frames_to_process)} frames")

        for idx, frame_idx in enumerate(frames_to_process):
            if progress_callback:
                progress_callback(idx, len(frames_to_process), f"Frame {frame_idx}")

            try:
                # Seek to frame
                if not self.reader.seek(frame_idx):
                    logger.warning(f"Failed to seek to frame {frame_idx}")
                    failed += 1
                    continue

                # Read frame data
                frame_data = self.reader.read_frame(
                    extract_left=self.config.extract_left_rgb,
                    extract_right=self.config.extract_right_rgb,
                    extract_depth=self.config.extract_depth,
                    extract_point_cloud=self.config.extract_point_cloud,
                    extract_imu=self.config.extract_imu,
                )

                if frame_data is None:
                    logger.warning(f"Failed to read frame {frame_idx}")
                    failed += 1
                    continue

                # Extract frame
                registry_entry = self._extract_frame(frame_data, idx)
                self._frame_registry.append(registry_entry)
                extracted += 1

            except Exception as e:
                logger.error(f"Error extracting frame {frame_idx}: {e}")
                failed += 1

        # Save calibration
        calib_file = self._save_calibration()

        # Save frame registry
        registry_file = self._save_frame_registry()

        logger.info(f"Extraction complete: {extracted} extracted, {failed} failed")

        return ExtractionResult(
            output_dir=self.output_dir,
            frame_count=total_frames,
            extracted_frames=extracted,
            failed_frames=failed,
            calibration_file=calib_file,
            frame_registry_file=registry_file,
        )

    def _extract_frame(self, frame: FrameData, sequence_index: int) -> dict:
        """
        Extract a single frame to disk.

        Args:
            frame: Frame data to extract
            sequence_index: Index in output sequence (for filename)

        Returns:
            Registry entry dict
        """
        # Generate unique frame ID
        frame_id = f"{self.reader.file_hash}_{frame.frame_index:06d}"
        filename_base = f"{sequence_index:06d}"

        registry = {
            "frame_id": frame_id,
            "sequence_index": sequence_index,
            "svo2_frame_index": frame.frame_index,
            "svo2_file": self.reader.file_path.name,
            "timestamp_ns": frame.timestamp_ns,
        }

        # Save left image
        if self.config.extract_left_rgb and frame.image_left is not None:
            path = self._save_image(
                frame.image_left,
                self.output_dir / "image_2" / f"{filename_base}.{self.config.image_format}",
            )
            registry["image_left"] = str(path.relative_to(self.output_dir))

        # Save right image
        if self.config.extract_right_rgb and frame.image_right is not None:
            path = self._save_image(
                frame.image_right,
                self.output_dir / "image_3" / f"{filename_base}.{self.config.image_format}",
            )
            registry["image_right"] = str(path.relative_to(self.output_dir))

        # Save depth
        if self.config.extract_depth and frame.depth is not None:
            path = self._save_depth(
                frame.depth,
                self.output_dir / "depth" / filename_base,
            )
            registry["depth"] = str(path.relative_to(self.output_dir))

        # Save point cloud
        if self.config.extract_point_cloud and frame.point_cloud is not None:
            path = self._save_point_cloud(
                frame.point_cloud,
                self.output_dir / "velodyne" / filename_base,
            )
            registry["point_cloud"] = str(path.relative_to(self.output_dir))

        # Save IMU data
        if self.config.extract_imu and frame.imu is not None:
            path = self._save_imu(
                frame.imu,
                self.output_dir / "oxts" / f"{filename_base}.txt",
            )
            registry["imu"] = str(path.relative_to(self.output_dir))

        return registry

    def _save_image(self, image: np.ndarray, path: Path) -> Path:
        """Save RGB image to disk."""
        # Convert BGR to RGB if needed (OpenCV uses BGR)
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        if path.suffix.lower() in [".jpg", ".jpeg"]:
            cv2.imwrite(
                str(path),
                cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality],
            )
        else:
            cv2.imwrite(
                str(path),
                cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_PNG_COMPRESSION, self.config.png_compression],
            )

        return path

    def _save_depth(self, depth: np.ndarray, path_base: Path) -> Path:
        """Save depth map to disk."""
        if self.config.depth_format == "png16":
            # Convert to 16-bit PNG (millimeters)
            depth_clipped = np.clip(depth, 0, self.config.max_depth)
            depth_mm = (depth_clipped * self.config.depth_scale).astype(np.uint16)
            # Set invalid values to 0
            depth_mm[~np.isfinite(depth)] = 0

            path = path_base.with_suffix(".png")
            cv2.imwrite(str(path), depth_mm)

        elif self.config.depth_format == "npy":
            path = path_base.with_suffix(".npy")
            np.save(path, depth)

        elif self.config.depth_format == "exr":
            path = path_base.with_suffix(".exr")
            cv2.imwrite(str(path), depth)

        else:
            raise ValueError(f"Unknown depth format: {self.config.depth_format}")

        return path

    def _save_point_cloud(self, point_cloud: np.ndarray, path_base: Path) -> Path:
        """Save point cloud to disk."""
        if self.config.point_cloud_format == "ply":
            path = path_base.with_suffix(".ply")
            self._write_ply(point_cloud, path)

        elif self.config.point_cloud_format == "npy":
            path = path_base.with_suffix(".npy")
            np.save(path, point_cloud)

        elif self.config.point_cloud_format == "bin":
            # KITTI binary format (x, y, z, intensity)
            path = path_base.with_suffix(".bin")
            self._write_kitti_bin(point_cloud, path)

        else:
            raise ValueError(f"Unknown point cloud format: {self.config.point_cloud_format}")

        return path

    def _write_ply(self, point_cloud: np.ndarray, path: Path) -> None:
        """Write point cloud to PLY file."""
        # Reshape if needed (H x W x 4 -> N x 4)
        if len(point_cloud.shape) == 3:
            points = point_cloud.reshape(-1, point_cloud.shape[-1])
        else:
            points = point_cloud

        # Filter invalid points
        valid_mask = np.isfinite(points[:, :3]).all(axis=1)
        points = points[valid_mask]

        # Write PLY header and data
        with open(path, "w") as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {len(points)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            if points.shape[1] >= 4:
                f.write("property uchar red\n")
                f.write("property uchar green\n")
                f.write("property uchar blue\n")
            f.write("end_header\n")

            for point in points:
                if points.shape[1] >= 4:
                    # XYZRGBA format - extract RGB from packed value
                    rgba = point[3].view(np.uint32)
                    r = (rgba >> 0) & 0xFF
                    g = (rgba >> 8) & 0xFF
                    b = (rgba >> 16) & 0xFF
                    f.write(f"{point[0]:.6f} {point[1]:.6f} {point[2]:.6f} {r} {g} {b}\n")
                else:
                    f.write(f"{point[0]:.6f} {point[1]:.6f} {point[2]:.6f}\n")

    def _write_kitti_bin(self, point_cloud: np.ndarray, path: Path) -> None:
        """Write point cloud to KITTI binary format."""
        # Reshape if needed
        if len(point_cloud.shape) == 3:
            points = point_cloud.reshape(-1, point_cloud.shape[-1])
        else:
            points = point_cloud

        # Filter invalid points
        valid_mask = np.isfinite(points[:, :3]).all(axis=1)
        points = points[valid_mask]

        # Convert to KITTI format: x, y, z, intensity
        kitti_points = np.zeros((len(points), 4), dtype=np.float32)
        kitti_points[:, :3] = points[:, :3]

        # Use normalized Z as intensity if no intensity available
        if points.shape[1] >= 4:
            # Extract intensity from RGBA
            rgba = points[:, 3].view(np.uint32)
            intensity = ((rgba >> 0) & 0xFF) / 255.0
            kitti_points[:, 3] = intensity.astype(np.float32)
        else:
            kitti_points[:, 3] = 1.0

        kitti_points.tofile(path)

    def _save_imu(self, imu, path: Path) -> Path:
        """Save IMU data to KITTI oxts format."""
        oxts = imu.to_oxts_format()

        # Convert quaternion to Euler angles (roll, pitch, yaw) in radians
        roll, pitch, yaw = self._quaternion_to_euler(
            oxts["qw"], oxts["qx"], oxts["qy"], oxts["qz"]
        )

        with open(path, "w") as f:
            # KITTI oxts format: lat lon alt roll pitch yaw vn ve vf vl vu ax ay az af al au wx wy wz wf wl wu pos_accuracy vel_accuracy
            # We use a simplified format with available data
            values = [
                0.0,  # lat
                0.0,  # lon
                0.0,  # alt
                roll,  # roll (radians)
                pitch,  # pitch (radians)
                yaw,  # yaw (radians)
                0.0,  # vn
                0.0,  # ve
                0.0,  # vf
                0.0,  # vl
                0.0,  # vu
                oxts["ax"],  # ax
                oxts["ay"],  # ay
                oxts["az"],  # az
                0.0,  # af
                0.0,  # al
                0.0,  # au
                oxts["wx"],  # wx
                oxts["wy"],  # wy
                oxts["wz"],  # wz
                0.0,  # wf
                0.0,  # wl
                0.0,  # wu
                0.0,  # pos_accuracy
                0.0,  # vel_accuracy
            ]
            f.write(" ".join(f"{v:.6f}" for v in values) + "\n")

        return path

    def _quaternion_to_euler(
        self, qw: float, qx: float, qy: float, qz: float
    ) -> tuple[float, float, float]:
        """
        Convert quaternion to Euler angles (roll, pitch, yaw).

        Args:
            qw, qx, qy, qz: Quaternion components

        Returns:
            Tuple of (roll, pitch, yaw) in radians
        """
        import math

        # Roll (x-axis rotation)
        sinr_cosp = 2.0 * (qw * qx + qy * qz)
        cosr_cosp = 1.0 - 2.0 * (qx * qx + qy * qy)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        # Pitch (y-axis rotation)
        sinp = 2.0 * (qw * qy - qz * qx)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)  # Use 90 degrees if out of range
        else:
            pitch = math.asin(sinp)

        # Yaw (z-axis rotation)
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw

    def _save_calibration(self) -> Path:
        """Save camera calibration to KITTI format."""
        calib = self.reader.calibration
        kitti_calib = calib.to_kitti_format()

        calib_file = self.output_dir / "calib" / "calib.txt"
        with open(calib_file, "w") as f:
            for key, value in kitti_calib.items():
                f.write(f"{key}: {value}\n")

        # Also save full calibration as JSON
        json_file = self.output_dir / "calib" / "calibration.json"
        with open(json_file, "w") as f:
            json.dump({
                "left": {
                    "fx": calib.fx_left,
                    "fy": calib.fy_left,
                    "cx": calib.cx_left,
                    "cy": calib.cy_left,
                    "distortion": calib.distortion_left,
                },
                "right": {
                    "fx": calib.fx_right,
                    "fy": calib.fy_right,
                    "cx": calib.cx_right,
                    "cy": calib.cy_right,
                    "distortion": calib.distortion_right,
                },
                "baseline": calib.baseline,
                "resolution": {
                    "width": calib.width,
                    "height": calib.height,
                },
            }, f, indent=2)

        return calib_file

    def _save_frame_registry(self) -> Path:
        """Save frame registry to JSON."""
        registry_file = self.output_dir / "frame_registry.json"

        registry_data = {
            "svo2_file": self.reader.file_path.name,
            "svo2_hash": self.reader.file_hash,
            "total_frames": self.reader.frame_count,
            "extracted_frames": len(self._frame_registry),
            "config": {
                "frame_skip": self.config.frame_skip,
                "start_frame": self.config.start_frame,
                "end_frame": self.config.end_frame,
                "depth_format": self.config.depth_format,
                "point_cloud_format": self.config.point_cloud_format,
            },
            "frames": self._frame_registry,
        }

        with open(registry_file, "w") as f:
            json.dump(registry_data, f, indent=2)

        return registry_file
