"""KITTI format dataset writer."""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class KITTIExportConfig:
    """Configuration for KITTI export."""

    include_images: bool = True
    include_depth: bool = True
    include_velodyne: bool = True
    include_calib: bool = True
    include_oxts: bool = True
    include_labels: bool = True

    # Compression
    create_zip: bool = True
    compress_level: int = 6


class KITTIWriter:
    """
    Exports data in KITTI format.

    KITTI Dataset Structure:
    ├── image_2/        # Left camera images
    ├── image_3/        # Right camera images
    ├── depth/          # Depth maps (non-standard extension)
    ├── velodyne/       # Point clouds in binary format
    ├── label_2/        # Object annotations
    ├── calib/          # Camera calibration
    └── oxts/           # GPS/IMU data
    """

    def __init__(
        self,
        output_dir: str | Path,
        config: KITTIExportConfig | None = None,
    ):
        """
        Initialize KITTI writer.

        Args:
            output_dir: Base output directory
            config: Export configuration
        """
        self.output_dir = Path(output_dir)
        self.config = config or KITTIExportConfig()

        self._setup_directories()

    def _setup_directories(self) -> None:
        """Create KITTI directory structure."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.config.include_images:
            (self.output_dir / "image_2").mkdir(exist_ok=True)
            (self.output_dir / "image_3").mkdir(exist_ok=True)

        if self.config.include_depth:
            (self.output_dir / "depth").mkdir(exist_ok=True)

        if self.config.include_velodyne:
            (self.output_dir / "velodyne").mkdir(exist_ok=True)

        if self.config.include_labels:
            (self.output_dir / "label_2").mkdir(exist_ok=True)

        if self.config.include_calib:
            (self.output_dir / "calib").mkdir(exist_ok=True)

        if self.config.include_oxts:
            (self.output_dir / "oxts").mkdir(exist_ok=True)

    def export_from_job(
        self,
        job_output_dir: str | Path,
        progress_callback=None,
    ) -> Path:
        """
        Export a processed job to KITTI format.

        Args:
            job_output_dir: Directory containing processed job data
            progress_callback: Optional progress callback

        Returns:
            Path to exported dataset (or zip file)
        """
        job_dir = Path(job_output_dir)

        # Find all sequence directories
        sequences = [d for d in job_dir.iterdir() if d.is_dir()]

        total_frames = 0
        frame_index = 0

        for seq_dir in sequences:
            # Load frame registry
            registry_file = seq_dir / "frame_registry.json"
            if not registry_file.exists():
                continue

            with open(registry_file) as f:
                registry = json.load(f)

            frames = registry.get("frames", [])

            for frame in frames:
                if progress_callback:
                    progress_callback(frame_index, len(frames), f"Frame {frame_index}")

                # Copy/convert files
                filename = f"{frame_index:06d}"

                # Images
                if self.config.include_images:
                    self._copy_image(
                        seq_dir / frame.get("image_left", ""),
                        self.output_dir / "image_2" / f"{filename}.png",
                    )
                    self._copy_image(
                        seq_dir / frame.get("image_right", ""),
                        self.output_dir / "image_3" / f"{filename}.png",
                    )

                # Depth
                if self.config.include_depth:
                    self._copy_file(
                        seq_dir / frame.get("depth", ""),
                        self.output_dir / "depth" / f"{filename}.png",
                    )

                # Point cloud
                if self.config.include_velodyne:
                    pc_path = seq_dir / frame.get("point_cloud", "")
                    if pc_path.exists():
                        self._convert_pointcloud_to_bin(
                            pc_path,
                            self.output_dir / "velodyne" / f"{filename}.bin",
                        )

                # IMU/OXTS
                if self.config.include_oxts:
                    self._copy_file(
                        seq_dir / frame.get("imu", ""),
                        self.output_dir / "oxts" / f"{filename}.txt",
                    )

                # Labels
                if self.config.include_labels:
                    label_src = seq_dir / "label_2" / f"{frame['sequence_index']:06d}.txt"
                    if label_src.exists():
                        self._copy_file(
                            label_src,
                            self.output_dir / "label_2" / f"{filename}.txt",
                        )

                frame_index += 1
                total_frames += 1

            # Calibration (once per sequence)
            if self.config.include_calib:
                calib_src = seq_dir / "calib" / "calib.txt"
                if calib_src.exists():
                    # KITTI uses one calib file per frame
                    for i in range(frame_index - len(frames), frame_index):
                        self._copy_file(
                            calib_src,
                            self.output_dir / "calib" / f"{i:06d}.txt",
                        )

        # Write metadata
        self._write_metadata(total_frames)

        # Create zip if requested
        if self.config.create_zip:
            return self._create_zip()

        return self.output_dir

    def _copy_file(self, src: Path, dst: Path) -> None:
        """Copy file if it exists."""
        if src.exists():
            shutil.copy2(src, dst)

    def _copy_image(self, src: Path, dst: Path) -> None:
        """Copy image file, converting format if needed."""
        if not src.exists():
            return

        if src.suffix.lower() == dst.suffix.lower():
            shutil.copy2(src, dst)
        else:
            import cv2
            img = cv2.imread(str(src))
            if img is not None:
                cv2.imwrite(str(dst), img)

    def _convert_pointcloud_to_bin(self, src: Path, dst: Path) -> None:
        """Convert point cloud to KITTI binary format."""
        import numpy as np

        if src.suffix.lower() == ".bin":
            shutil.copy2(src, dst)
            return

        elif src.suffix.lower() == ".ply":
            # Read PLY and convert to binary
            points = self._read_ply(src)
            if points is not None:
                points.astype(np.float32).tofile(dst)

        elif src.suffix.lower() == ".npy":
            points = np.load(src)
            # Reshape if needed (H x W x 4 -> N x 4)
            if len(points.shape) == 3:
                points = points.reshape(-1, points.shape[-1])
            # Keep only x, y, z, intensity
            if points.shape[1] >= 4:
                points = points[:, :4]
            points.astype(np.float32).tofile(dst)

    def _read_ply(self, path: Path):
        """Read PLY file to numpy array."""
        import numpy as np

        points = []
        header_ended = False

        with open(path) as f:
            for line in f:
                if not header_ended:
                    if line.strip() == "end_header":
                        header_ended = True
                    continue

                parts = line.strip().split()
                if len(parts) >= 3:
                    # x, y, z, (intensity)
                    x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                    intensity = 1.0
                    if len(parts) >= 6:
                        # Use RGB to compute intensity
                        r, g, b = int(parts[3]), int(parts[4]), int(parts[5])
                        intensity = (r + g + b) / (3 * 255.0)
                    points.append([x, y, z, intensity])

        if not points:
            return None

        return np.array(points, dtype=np.float32)

    def _write_metadata(self, total_frames: int) -> None:
        """Write dataset metadata."""
        metadata = {
            "format": "KITTI",
            "total_frames": total_frames,
            "directories": {
                "image_2": "Left camera images (PNG)",
                "image_3": "Right camera images (PNG)",
                "depth": "Depth maps (16-bit PNG, millimeters)",
                "velodyne": "Point clouds (binary float32)",
                "label_2": "Object annotations",
                "calib": "Camera calibration",
                "oxts": "IMU data",
            },
        }

        with open(self.output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def _create_zip(self) -> Path:
        """Create ZIP archive of the dataset."""
        zip_path = self.output_dir.with_suffix(".zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=self.config.compress_level) as zf:
            for file_path in self.output_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.output_dir)
                    zf.write(file_path, arcname)

        logger.info(f"Created KITTI archive: {zip_path}")
        return zip_path
