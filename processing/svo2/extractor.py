"""SVO2 data extraction to disk."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from processing.svo2.reader import FrameData, SVO2Reader

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
    extract_numpy: bool = False  # Extract RGB frames as NumPy arrays for training

    # Frame selection
    frame_skip: int = 1  # Process every Nth frame (1 = all frames)
    start_frame: int = 0
    end_frame: int | None = None

    # Output formats
    image_format: str = "png"  # png, jpg
    depth_format: str = "png16"  # png16 (16-bit), npy, exr
    # Point cloud format:
    #   - "ply": ASCII PLY (~76MB per frame, human-readable)
    #   - "ply_binary": Binary PLY (~10MB per frame, recommended)
    #   - "npy": NumPy binary (~10MB per frame)
    #   - "bin": KITTI binary format
    point_cloud_format: str = "ply_binary"  # Default to binary for space efficiency

    # Image compression
    jpeg_quality: int = 95
    png_compression: int = 3

    # Depth settings
    depth_scale: float = 1000.0  # Scale factor for 16-bit (1000 = mm)
    max_depth: float = 100.0  # Maximum depth in meters

    # Lineage context for enhanced naming
    # When set, files are named: {dataset_id[:8]}_{svo2_timestamp}_{camera_serial}_{frame_index:06d}.ext
    dataset_id: str | None = None
    original_unix_timestamp: int | None = None
    use_enhanced_naming: bool = False  # Enable enhanced naming pattern


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
            (self.output_dir / "sensors" / "imu").mkdir(parents=True, exist_ok=True)

        if self.config.extract_numpy:
            (self.output_dir / "numpy" / "left").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "numpy" / "right").mkdir(parents=True, exist_ok=True)
            if self.config.extract_depth:
                (self.output_dir / "depth_numpy").mkdir(exist_ok=True)

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

        # Generate filename based on naming strategy
        if self.config.use_enhanced_naming:
            # Enhanced naming: {dataset_id[:8]}_{svo2_timestamp}_{camera_serial}_{frame_index:06d}
            dataset_prefix = (self.config.dataset_id or "unk")[:8]
            svo2_timestamp = self.config.original_unix_timestamp or 0
            camera_serial = self.reader.camera_serial or "unknown"
            filename_base = f"{dataset_prefix}_{svo2_timestamp}_{camera_serial}_{sequence_index:06d}"
        else:
            # Simple naming: {sequence_index:06d}
            filename_base = f"{sequence_index:06d}"

        registry = {
            "frame_id": frame_id,
            "sequence_index": sequence_index,
            "svo2_frame_index": frame.frame_index,
            "svo2_file": self.reader.file_path.name,
            "timestamp_ns": frame.timestamp_ns,
            "filename_base": filename_base,  # Store for lineage tracking
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

        # Save NumPy arrays (for training)
        if self.config.extract_numpy:
            if frame.image_left is not None:
                npy_path, meta_path = self._save_numpy_array(
                    frame.image_left,
                    self.output_dir / "numpy" / "left" / f"{filename_base}.npy",
                    frame,
                    "left",
                )
                registry["numpy_left"] = str(npy_path.relative_to(self.output_dir))

            if frame.image_right is not None:
                npy_path, meta_path = self._save_numpy_array(
                    frame.image_right,
                    self.output_dir / "numpy" / "right" / f"{filename_base}.npy",
                    frame,
                    "right",
                )
                registry["numpy_right"] = str(npy_path.relative_to(self.output_dir))

        # Save depth
        if self.config.extract_depth and frame.depth is not None:
            path = self._save_depth(
                frame.depth,
                self.output_dir / "depth" / filename_base,
            )
            registry["depth"] = str(path.relative_to(self.output_dir))

            # Also save depth as NumPy if extract_numpy is enabled
            if self.config.extract_numpy:
                depth_npy_path = self.output_dir / "depth_numpy" / f"{filename_base}.npy"
                np.save(depth_npy_path, frame.depth)
                registry["depth_numpy"] = str(depth_npy_path.relative_to(self.output_dir))

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
            # Also save full sensor data as JSON
            sensor_path = self._save_sensor_json(
                frame.imu,
                self.output_dir / "sensors" / "imu" / f"{filename_base}.json",
            )
            registry["sensor_json"] = str(sensor_path.relative_to(self.output_dir))
            registry["imu"] = str(path.relative_to(self.output_dir))

        return registry

    def _save_image(self, image: np.ndarray, path: Path) -> Path:
        """Save image to disk.

        Note: OpenCV uses BGR format internally, and cv2.imwrite expects BGR.
        If the input image is already in BGR (from ZED SDK), save directly.
        """
        # OpenCV imwrite expects BGR format - save directly without conversion
        # The ZED SDK typically provides images in BGR format already
        if path.suffix.lower() in [".jpg", ".jpeg"]:
            cv2.imwrite(
                str(path),
                image,
                [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality],
            )
        else:
            cv2.imwrite(
                str(path),
                image,
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

        elif self.config.point_cloud_format == "ply_binary":
            # Binary PLY format - much smaller than ASCII (~7-8x compression)
            path = path_base.with_suffix(".ply")
            self._write_ply_binary(point_cloud, path)

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
        """Write point cloud to PLY file with buffered I/O for performance."""
        # Reshape if needed (H x W x 4 -> N x 4)
        if len(point_cloud.shape) == 3:
            points = point_cloud.reshape(-1, point_cloud.shape[-1])
        else:
            points = point_cloud

        # Filter invalid points
        valid_mask = np.isfinite(points[:, :3]).all(axis=1)
        points = points[valid_mask]

        has_color = points.shape[1] >= 4

        # Build header
        header_lines = [
            "ply",
            "format ascii 1.0",
            f"element vertex {len(points)}",
            "property float x",
            "property float y",
            "property float z",
        ]
        if has_color:
            header_lines.extend([
                "property uchar red",
                "property uchar green",
                "property uchar blue",
            ])
        header_lines.append("end_header")
        header = "\n".join(header_lines) + "\n"

        # Use buffered writing for performance (batch of 10000 points)
        BATCH_SIZE = 10000

        with open(path, "w", buffering=1024 * 1024) as f:  # 1MB buffer
            f.write(header)

            if has_color:
                # Extract RGB from packed RGBA values (vectorized)
                rgba_values = points[:, 3].view(np.uint32)
                r_values = (rgba_values >> 0) & 0xFF
                g_values = (rgba_values >> 8) & 0xFF
                b_values = (rgba_values >> 16) & 0xFF

                # Write in batches
                for i in range(0, len(points), BATCH_SIZE):
                    batch_end = min(i + BATCH_SIZE, len(points))
                    batch_points = points[i:batch_end]
                    batch_r = r_values[i:batch_end]
                    batch_g = g_values[i:batch_end]
                    batch_b = b_values[i:batch_end]

                    lines = [
                        f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f} {r} {g} {b}\n"
                        for p, r, g, b in zip(batch_points, batch_r, batch_g, batch_b, strict=True)
                    ]
                    f.writelines(lines)
            else:
                # Write in batches (no color)
                for i in range(0, len(points), BATCH_SIZE):
                    batch_end = min(i + BATCH_SIZE, len(points))
                    batch_points = points[i:batch_end]

                    lines = [
                        f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n"
                        for p in batch_points
                    ]
                    f.writelines(lines)

    def _write_ply_binary(self, point_cloud: np.ndarray, path: Path) -> None:
        """
        Write point cloud to binary PLY file.

        Binary PLY is ~7-8x smaller than ASCII PLY:
        - ASCII: ~76 MB per frame
        - Binary: ~10 MB per frame

        Binary format uses little-endian floats for coordinates
        and bytes for RGB values.
        """
        import struct

        # Reshape if needed (H x W x 4 -> N x 4)
        if len(point_cloud.shape) == 3:
            points = point_cloud.reshape(-1, point_cloud.shape[-1])
        else:
            points = point_cloud

        # Filter invalid points
        valid_mask = np.isfinite(points[:, :3]).all(axis=1)
        points = points[valid_mask]

        has_color = points.shape[1] >= 4

        # Build header
        header_lines = [
            "ply",
            "format binary_little_endian 1.0",
            f"element vertex {len(points)}",
            "property float x",
            "property float y",
            "property float z",
        ]
        if has_color:
            header_lines.extend([
                "property uchar red",
                "property uchar green",
                "property uchar blue",
            ])
        header_lines.append("end_header")
        header = "\n".join(header_lines) + "\n"

        with open(path, "wb") as f:
            # Write ASCII header
            f.write(header.encode("ascii"))

            if has_color:
                # Extract RGB from packed RGBA values (vectorized)
                rgba_values = points[:, 3].view(np.uint32)
                r_values = ((rgba_values >> 0) & 0xFF).astype(np.uint8)
                g_values = ((rgba_values >> 8) & 0xFF).astype(np.uint8)
                b_values = ((rgba_values >> 16) & 0xFF).astype(np.uint8)

                # Create structured array for efficient binary write
                # Each vertex: 3 floats (12 bytes) + 3 bytes (RGB) = 15 bytes
                xyz = points[:, :3].astype(np.float32)

                # Write in batches for memory efficiency
                BATCH_SIZE = 50000
                for i in range(0, len(points), BATCH_SIZE):
                    batch_end = min(i + BATCH_SIZE, len(points))

                    # Pack xyz floats
                    xyz_batch = xyz[i:batch_end]
                    r_batch = r_values[i:batch_end]
                    g_batch = g_values[i:batch_end]
                    b_batch = b_values[i:batch_end]

                    # Write interleaved data
                    for j in range(len(xyz_batch)):
                        f.write(struct.pack("<fff", xyz_batch[j, 0], xyz_batch[j, 1], xyz_batch[j, 2]))
                        f.write(struct.pack("BBB", r_batch[j], g_batch[j], b_batch[j]))
            else:
                # No color - just write xyz floats
                xyz = points[:, :3].astype(np.float32)
                xyz.tofile(f)

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

    def _save_numpy_array(
        self,
        image: np.ndarray,
        path: Path,
        frame: FrameData,
        camera_side: str,
    ) -> tuple[Path, Path]:
        """
        Save RGB image as NumPy array with companion metadata.

        Args:
            image: RGB image as numpy array (BGR from OpenCV)
            path: Output path for .npy file
            frame: FrameData containing metadata
            camera_side: "left" or "right"

        Returns:
            Tuple of (numpy_path, metadata_path)
        """
        # Convert BGR to RGB for training (most ML frameworks expect RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Save the numpy array
        np.save(path, rgb_image)

        # Create companion metadata
        metadata = {
            "source_svo2": self.reader.file_path.name,
            "dataset_id": self.config.dataset_id,
            "frame_index": frame.frame_index,
            "timestamp_ns": frame.timestamp_ns,
            "camera_serial": self.reader.camera_serial,
            "camera_side": camera_side,
            "resolution": list(rgb_image.shape[:2][::-1]),  # [width, height]
            "dtype": str(rgb_image.dtype),
            "channels": rgb_image.shape[2] if len(rgb_image.shape) > 2 else 1,
            "color_space": "RGB",
        }

        # Save metadata alongside the numpy file
        meta_path = path.with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return path, meta_path

    def _save_sensor_json(self, imu, path: Path) -> Path:
        """Save full sensor data to JSON format."""
        sensor_data = imu.to_full_sensor_dict()

        # Add lineage context
        sensor_data["source_svo2"] = self.reader.file_path.name
        sensor_data["dataset_id"] = self.config.dataset_id
        sensor_data["camera_serial"] = self.reader.camera_serial

        with open(path, "w") as f:
            json.dump(sensor_data, f, indent=2)

        return path

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
            # Lineage context
            "lineage": {
                "dataset_id": self.config.dataset_id,
                "original_unix_timestamp": self.config.original_unix_timestamp,
                "camera_serial": self.reader.camera_serial,
                "use_enhanced_naming": self.config.use_enhanced_naming,
            },
            "frames": self._frame_registry,
        }

        with open(registry_file, "w") as f:
            json.dump(registry_data, f, indent=2)

        return registry_file
