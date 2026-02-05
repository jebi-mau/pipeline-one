"""SVO2 file reader using ZED SDK (pyzed)."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

# Check for ZED SDK availability
try:
    import pyzed.sl as sl
    PYZED_AVAILABLE = True
except ImportError:
    PYZED_AVAILABLE = False
    sl = None

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class CameraCalibration:
    """Camera calibration parameters from ZED camera."""

    # Left camera intrinsics
    fx_left: float
    fy_left: float
    cx_left: float
    cy_left: float

    # Right camera intrinsics
    fx_right: float
    fy_right: float
    cx_right: float
    cy_right: float

    # Stereo baseline (meters)
    baseline: float

    # Image resolution
    width: int
    height: int

    # Distortion coefficients (k1, k2, p1, p2, k3)
    distortion_left: list[float] = field(default_factory=list)
    distortion_right: list[float] = field(default_factory=list)

    def to_kitti_format(self) -> dict[str, str]:
        """Convert calibration to KITTI calib format."""
        # P0: left camera projection matrix (3x4)
        p0 = f"{self.fx_left} 0 {self.cx_left} 0 0 {self.fy_left} {self.cy_left} 0 0 0 1 0"

        # P1: right camera projection matrix (3x4)
        # Tx = -fx * baseline
        tx = -self.fx_right * self.baseline
        p1 = f"{self.fx_right} 0 {self.cx_right} {tx} 0 {self.fy_right} {self.cy_right} 0 0 0 1 0"

        # R0_rect: rectification matrix (identity for rectified images)
        r0 = "1 0 0 0 1 0 0 0 1"

        # Tr_velo_to_cam: transformation from velodyne to camera (identity placeholder)
        tr_velo = "1 0 0 0 0 1 0 0 0 0 1 0"

        return {
            "P0": p0,
            "P1": p1,
            "P2": p0,  # Same as P0 for monocular
            "P3": p1,  # Same as P1 for stereo
            "R0_rect": r0,
            "Tr_velo_to_cam": tr_velo,
            "Tr_imu_to_velo": tr_velo,
        }


@dataclass
class IMUData:
    """IMU sensor data from ZED camera."""

    timestamp_ns: int

    # Accelerometer (m/s^2)
    accel_x: float
    accel_y: float
    accel_z: float

    # Gyroscope (rad/s)
    gyro_x: float
    gyro_y: float
    gyro_z: float

    # Orientation quaternion (w, x, y, z)
    orientation_w: float
    orientation_x: float
    orientation_y: float
    orientation_z: float

    # Magnetometer (µT) - from get_magnetometer_data()
    mag_x: float | None = None
    mag_y: float | None = None
    mag_z: float | None = None

    # Barometer data - from get_barometer_data()
    pressure_hpa: float | None = None  # Atmospheric pressure (hPa)
    altitude_m: float | None = None    # Estimated altitude (m)

    # Temperature data
    imu_temperature_c: float | None = None       # IMU sensor temperature
    barometer_temperature_c: float | None = None # Barometer temperature

    def to_oxts_format(self) -> dict[str, float]:
        """Convert IMU data to KITTI oxts format."""
        return {
            "ax": self.accel_x,
            "ay": self.accel_y,
            "az": self.accel_z,
            "wx": self.gyro_x,
            "wy": self.gyro_y,
            "wz": self.gyro_z,
            "qw": self.orientation_w,
            "qx": self.orientation_x,
            "qy": self.orientation_y,
            "qz": self.orientation_z,
        }

    def to_full_sensor_dict(self) -> dict:
        """Convert all sensor data to dictionary for JSON serialization."""
        return {
            "timestamp_ns": self.timestamp_ns,
            "imu": {
                "accel": {"x": self.accel_x, "y": self.accel_y, "z": self.accel_z},
                "gyro": {"x": self.gyro_x, "y": self.gyro_y, "z": self.gyro_z},
                "orientation": {
                    "w": self.orientation_w,
                    "x": self.orientation_x,
                    "y": self.orientation_y,
                    "z": self.orientation_z,
                },
                "temperature_c": self.imu_temperature_c,
            },
            "magnetometer": {
                "x": self.mag_x,
                "y": self.mag_y,
                "z": self.mag_z,
            } if self.mag_x is not None else None,
            "barometer": {
                "pressure_hpa": self.pressure_hpa,
                "altitude_m": self.altitude_m,
                "temperature_c": self.barometer_temperature_c,
            } if self.pressure_hpa is not None else None,
        }


@dataclass
class FrameData:
    """Single frame extracted from SVO2 file."""

    frame_index: int
    timestamp_ns: int

    # Images (BGR format, uint8)
    image_left: NDArray[np.uint8] | None = None
    image_right: NDArray[np.uint8] | None = None

    # Depth map (float32, meters)
    depth: NDArray[np.float32] | None = None

    # Point cloud (Nx4 XYZRGBA, float32)
    point_cloud: NDArray[np.float32] | None = None

    # IMU data
    imu: IMUData | None = None

    @property
    def has_valid_depth(self) -> bool:
        """Check if depth data is valid."""
        if self.depth is None:
            return False
        valid_count = np.isfinite(self.depth).sum()
        return valid_count > 0


class SVO2Reader:
    """
    Reader for ZED SVO2 files using the ZED SDK.

    SVO2 is an MCAP-based format used by Stereolabs ZED cameras
    containing stereo video, depth, point clouds, and IMU data.
    """

    def __init__(
        self,
        file_path: str | Path,
        depth_mode: str = "NEURAL",
        coordinate_system: str = "IMAGE",
    ):
        """
        Initialize SVO2 reader.

        Args:
            file_path: Path to the SVO2 file
            depth_mode: Depth computation mode (NEURAL, ULTRA, QUALITY, PERFORMANCE)
            coordinate_system: Coordinate system for point cloud (IMAGE, RIGHT_HANDED_Y_UP)
        """
        self.file_path = Path(file_path)
        self.depth_mode = depth_mode
        self.coordinate_system = coordinate_system

        if not self.file_path.exists():
            raise FileNotFoundError(f"SVO2 file not found: {self.file_path}")

        if not PYZED_AVAILABLE:
            logger.warning("ZED SDK (pyzed) not available - using stub mode")
            self._camera = None
            self._runtime_params = None
            self._is_open = False
        else:
            self._camera = sl.Camera()
            self._runtime_params = None
            self._is_open = False

        # Cached data
        self._calibration: CameraCalibration | None = None
        self._file_hash: str | None = None
        self._frame_count: int | None = None

    def __enter__(self) -> SVO2Reader:
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    @property
    def file_hash(self) -> str:
        """Get SHA256 hash of the SVO2 file (first 64KB for speed)."""
        if self._file_hash is None:
            hasher = hashlib.sha256()
            with open(self.file_path, "rb") as f:
                # Hash first 64KB for unique identification
                hasher.update(f.read(65536))
            self._file_hash = hasher.hexdigest()[:16]
        return self._file_hash

    @property
    def is_open(self) -> bool:
        """Check if the SVO2 file is open."""
        return self._is_open

    @property
    def frame_count(self) -> int:
        """Get total number of frames in the SVO2 file."""
        if self._frame_count is None:
            if not self._is_open:
                raise RuntimeError("SVO2 file is not open")
            if not PYZED_AVAILABLE:
                self._frame_count = 0
            else:
                self._frame_count = self._camera.get_svo_number_of_frames()
        return self._frame_count

    @property
    def calibration(self) -> CameraCalibration:
        """Get camera calibration parameters."""
        if self._calibration is None:
            if not self._is_open:
                raise RuntimeError("SVO2 file is not open")
            self._calibration = self._extract_calibration()
        return self._calibration

    @property
    def camera_serial(self) -> str | None:
        """Get camera serial number."""
        if not self._is_open:
            return None
        if not PYZED_AVAILABLE or self._camera is None:
            return None
        cam_info = self._camera.get_camera_information()
        return str(cam_info.serial_number)

    def open(self) -> None:
        """Open the SVO2 file for reading."""
        if self._is_open:
            return

        if not PYZED_AVAILABLE:
            logger.warning("Cannot open SVO2 file - ZED SDK not available")
            self._is_open = True  # Stub mode
            return

        # Initialize parameters
        init_params = sl.InitParameters()
        init_params.set_from_svo_file(str(self.file_path))
        init_params.svo_real_time_mode = False
        init_params.coordinate_units = sl.UNIT.METER

        # Set coordinate system
        if self.coordinate_system == "RIGHT_HANDED_Y_UP":
            init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
        else:
            init_params.coordinate_system = sl.COORDINATE_SYSTEM.IMAGE

        # Set depth mode
        depth_modes = {
            "NEURAL": sl.DEPTH_MODE.NEURAL,
            "NEURAL_PLUS": getattr(sl.DEPTH_MODE, "NEURAL_PLUS", sl.DEPTH_MODE.NEURAL),
            "ULTRA": sl.DEPTH_MODE.ULTRA,
            "QUALITY": sl.DEPTH_MODE.QUALITY,
            "PERFORMANCE": sl.DEPTH_MODE.PERFORMANCE,
        }
        init_params.depth_mode = depth_modes.get(self.depth_mode, sl.DEPTH_MODE.NEURAL)
        init_params.depth_minimum_distance = 0.3  # 30cm minimum
        init_params.depth_maximum_distance = 100.0  # 100m maximum

        # Open camera
        status = self._camera.open(init_params)
        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"Failed to open SVO2 file: {status}")

        # Setup runtime parameters
        self._runtime_params = sl.RuntimeParameters()
        self._runtime_params.enable_fill_mode = False

        self._is_open = True
        logger.info(f"Opened SVO2 file: {self.file_path.name} ({self.frame_count} frames)")

    def close(self) -> None:
        """Close the SVO2 file."""
        if not self._is_open:
            return

        if PYZED_AVAILABLE and self._camera is not None:
            self._camera.close()

        self._is_open = False
        logger.info(f"Closed SVO2 file: {self.file_path.name}")

    def _extract_calibration(self) -> CameraCalibration:
        """Extract camera calibration from the SVO2 file."""
        if not PYZED_AVAILABLE:
            # Return dummy calibration for stub mode
            return CameraCalibration(
                fx_left=1000.0, fy_left=1000.0,
                cx_left=640.0, cy_left=360.0,
                fx_right=1000.0, fy_right=1000.0,
                cx_right=640.0, cy_right=360.0,
                baseline=0.12,
                width=1280, height=720,
            )

        cam_info = self._camera.get_camera_information()
        calib = cam_info.camera_configuration.calibration_parameters

        left = calib.left_cam
        right = calib.right_cam

        return CameraCalibration(
            fx_left=left.fx,
            fy_left=left.fy,
            cx_left=left.cx,
            cy_left=left.cy,
            fx_right=right.fx,
            fy_right=right.fy,
            cx_right=right.cx,
            cy_right=right.cy,
            baseline=calib.get_camera_baseline() / 1000.0,  # mm to meters
            width=int(left.image_size.width),
            height=int(left.image_size.height),
            distortion_left=list(left.disto),
            distortion_right=list(right.disto),
        )

    def seek(self, frame_index: int) -> bool:
        """
        Seek to a specific frame.

        Args:
            frame_index: Zero-based frame index

        Returns:
            True if seek was successful
        """
        if not self._is_open:
            raise RuntimeError("SVO2 file is not open")

        if not PYZED_AVAILABLE:
            return False

        if frame_index < 0 or frame_index >= self.frame_count:
            return False

        self._camera.set_svo_position(frame_index)
        return True

    def read_frame(
        self,
        extract_left: bool = True,
        extract_right: bool = True,
        extract_depth: bool = True,
        extract_point_cloud: bool = True,
        extract_imu: bool = True,
    ) -> FrameData | None:
        """
        Read the next frame from the SVO2 file.

        Args:
            extract_left: Extract left RGB image
            extract_right: Extract right RGB image
            extract_depth: Extract depth map
            extract_point_cloud: Extract point cloud
            extract_imu: Extract IMU data

        Returns:
            FrameData object or None if no more frames
        """
        if not self._is_open:
            raise RuntimeError("SVO2 file is not open")

        if not PYZED_AVAILABLE:
            return None

        # Grab frame
        status = self._camera.grab(self._runtime_params)
        if status != sl.ERROR_CODE.SUCCESS:
            if status == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
                return None
            logger.warning(f"Failed to grab frame: {status}")
            return None

        frame_index = self._camera.get_svo_position()
        timestamp = self._camera.get_timestamp(sl.TIME_REFERENCE.IMAGE)

        frame_data = FrameData(
            frame_index=frame_index,
            timestamp_ns=timestamp.get_nanoseconds(),
        )

        # Extract left image
        if extract_left:
            image_left = sl.Mat()
            self._camera.retrieve_image(image_left, sl.VIEW.LEFT)
            frame_data.image_left = image_left.get_data()[:, :, :3].copy()  # Remove alpha

        # Extract right image
        if extract_right:
            image_right = sl.Mat()
            self._camera.retrieve_image(image_right, sl.VIEW.RIGHT)
            frame_data.image_right = image_right.get_data()[:, :, :3].copy()

        # Extract depth
        if extract_depth:
            depth_map = sl.Mat()
            self._camera.retrieve_measure(depth_map, sl.MEASURE.DEPTH)
            frame_data.depth = depth_map.get_data().copy()

        # Extract point cloud
        if extract_point_cloud:
            point_cloud = sl.Mat()
            self._camera.retrieve_measure(point_cloud, sl.MEASURE.XYZRGBA)
            frame_data.point_cloud = point_cloud.get_data().copy()

        # Extract IMU data
        if extract_imu:
            sensors_data = sl.SensorsData()
            if self._camera.get_sensors_data(sensors_data, sl.TIME_REFERENCE.IMAGE) == sl.ERROR_CODE.SUCCESS:
                imu_data = sensors_data.get_imu_data()

                accel = imu_data.get_linear_acceleration()
                gyro = imu_data.get_angular_velocity()
                orient = imu_data.get_pose().get_orientation()

                # Initialize IMU data with basic accelerometer, gyroscope, orientation
                frame_data.imu = IMUData(
                    timestamp_ns=timestamp.get_nanoseconds(),
                    accel_x=accel[0],
                    accel_y=accel[1],
                    accel_z=accel[2],
                    gyro_x=gyro[0],
                    gyro_y=gyro[1],
                    gyro_z=gyro[2],
                    orientation_w=orient.get()[0],
                    orientation_x=orient.get()[1],
                    orientation_y=orient.get()[2],
                    orientation_z=orient.get()[3],
                )

                # Extract magnetometer data if available
                try:
                    mag_data = sensors_data.get_magnetometer_data()
                    if mag_data.is_available:
                        mag_field = mag_data.get_magnetic_field_calibrated()
                        frame_data.imu.mag_x = mag_field[0]
                        frame_data.imu.mag_y = mag_field[1]
                        frame_data.imu.mag_z = mag_field[2]
                except (AttributeError, RuntimeError):
                    pass  # Magnetometer not available on this device

                # Extract barometer data if available
                try:
                    baro_data = sensors_data.get_barometer_data()
                    if baro_data.is_available:
                        frame_data.imu.pressure_hpa = baro_data.pressure
                        frame_data.imu.altitude_m = baro_data.relative_altitude
                        # Barometer temperature if available
                        if hasattr(baro_data, 'effective_rate'):
                            pass  # Some SDK versions expose different attrs
                except (AttributeError, RuntimeError):
                    pass  # Barometer not available on this device

                # Extract temperature data if available
                try:
                    temp_data = sensors_data.get_temperature_data()
                    # IMU temperature
                    if hasattr(temp_data, 'get'):
                        imu_temp = temp_data.get(sl.SENSOR_LOCATION.IMU)
                        if imu_temp != -1:  # -1 indicates not available
                            frame_data.imu.imu_temperature_c = imu_temp
                        baro_temp = temp_data.get(sl.SENSOR_LOCATION.BAROMETER)
                        if baro_temp != -1:
                            frame_data.imu.barometer_temperature_c = baro_temp
                    elif hasattr(temp_data, 'temperature_map'):
                        # Alternative SDK version
                        temp_map = temp_data.temperature_map
                        if sl.SENSOR_LOCATION.IMU in temp_map:
                            frame_data.imu.imu_temperature_c = temp_map[sl.SENSOR_LOCATION.IMU]
                        if sl.SENSOR_LOCATION.BAROMETER in temp_map:
                            frame_data.imu.barometer_temperature_c = temp_map[sl.SENSOR_LOCATION.BAROMETER]
                except (AttributeError, RuntimeError, KeyError):
                    pass  # Temperature data not available

        return frame_data

    def iter_frames(
        self,
        start: int = 0,
        end: int | None = None,
        step: int = 1,
        **extract_options,
    ) -> Iterator[FrameData]:
        """
        Iterate over frames in the SVO2 file.

        Args:
            start: Starting frame index
            end: Ending frame index (exclusive), None for all frames
            step: Frame step (1 = every frame, 2 = every other frame, etc.)
            **extract_options: Options passed to read_frame()

        Yields:
            FrameData objects
        """
        if not self._is_open:
            raise RuntimeError("SVO2 file is not open")

        if end is None:
            end = self.frame_count

        for frame_idx in range(start, min(end, self.frame_count), step):
            if not self.seek(frame_idx):
                continue

            frame_data = self.read_frame(**extract_options)
            if frame_data is not None:
                yield frame_data

    def get_metadata(self) -> dict:
        """Get SVO2 file metadata."""
        metadata = {
            "file_path": str(self.file_path),
            "file_name": self.file_path.name,
            "file_hash": self.file_hash,
            "file_size_mb": self.file_path.stat().st_size / (1024 * 1024),
        }

        if self._is_open:
            metadata.update({
                "frame_count": self.frame_count,
                "depth_mode": self.depth_mode,
            })

            if PYZED_AVAILABLE and self._camera is not None:
                cam_info = self._camera.get_camera_information()
                cam_config = cam_info.camera_configuration
                metadata.update({
                    "serial_number": cam_info.serial_number,
                    "camera_model": str(cam_info.camera_model),
                    "firmware_version": cam_config.firmware_version,
                    "resolution": {
                        "width": self.calibration.width,
                        "height": self.calibration.height,
                    },
                    "fps": cam_config.fps,
                })

                # Video container metadata (SVO2 format info)
                video_metadata = self._get_video_metadata()
                if video_metadata:
                    metadata["video"] = video_metadata

                # Sensor availability
                sensors = self._get_sensor_availability()
                if sensors:
                    metadata["sensors"] = sensors

        return metadata

    def _get_video_metadata(self) -> dict | None:
        """Get video encoding metadata from SVO2 file."""
        if not PYZED_AVAILABLE or self._camera is None:
            return None

        try:
            rec_params = self._camera.get_recording_parameters()
            video_meta = {}

            # Compression mode
            if hasattr(rec_params, 'compression_mode'):
                comp_mode = rec_params.compression_mode
                if hasattr(sl, 'SVO_COMPRESSION_MODE'):
                    if comp_mode == sl.SVO_COMPRESSION_MODE.LOSSLESS:
                        video_meta["compression_mode"] = "LOSSLESS"
                    elif comp_mode == sl.SVO_COMPRESSION_MODE.H264:
                        video_meta["compression_mode"] = "H264"
                        video_meta["video_codec"] = "H264"
                    elif comp_mode == sl.SVO_COMPRESSION_MODE.H265:
                        video_meta["compression_mode"] = "H265"
                        video_meta["video_codec"] = "H265/HEVC"
                    elif hasattr(sl.SVO_COMPRESSION_MODE, 'H264_LOSSLESS') and comp_mode == sl.SVO_COMPRESSION_MODE.H264_LOSSLESS:
                        video_meta["compression_mode"] = "H264_LOSSLESS"
                        video_meta["video_codec"] = "H264"
                    elif hasattr(sl.SVO_COMPRESSION_MODE, 'H265_LOSSLESS') and comp_mode == sl.SVO_COMPRESSION_MODE.H265_LOSSLESS:
                        video_meta["compression_mode"] = "H265_LOSSLESS"
                        video_meta["video_codec"] = "H265/HEVC"

            # Bitrate if available
            if hasattr(rec_params, 'bitrate'):
                video_meta["bitrate_kbps"] = rec_params.bitrate

            # Target framerate
            if hasattr(rec_params, 'target_framerate'):
                video_meta["target_framerate"] = rec_params.target_framerate

            return video_meta if video_meta else None
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Could not get video metadata: {e}")
            return None

    def _get_sensor_availability(self) -> dict | None:
        """Check which sensors are available on this camera."""
        if not PYZED_AVAILABLE or self._camera is not None:
            return None

        try:
            sensors_config = self._camera.get_camera_information().sensors_configuration
            availability = {
                "imu": sensors_config.imu.is_available if hasattr(sensors_config, 'imu') else False,
                "magnetometer": sensors_config.magnetometer.is_available if hasattr(sensors_config, 'magnetometer') else False,
                "barometer": sensors_config.barometer.is_available if hasattr(sensors_config, 'barometer') else False,
            }
            return availability
        except (AttributeError, RuntimeError):
            return None
