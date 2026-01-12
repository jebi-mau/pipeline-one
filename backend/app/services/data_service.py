"""Data service for reading extracted frame data."""

import json
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.job import ProcessingJob, JobConfig
from backend.app.schemas.data import (
    AnnotationSummary,
    BBox2D,
    BBox3D,
    CorrelationEntry,
    CorrelationTableResponse,
    DataSummary,
    FrameDetail,
    FrameListResponse,
    FrameMetadataSummary,
    FrameSummary,
    SVO2FileSummary,
)

logger = logging.getLogger(__name__)

# Base output directory
OUTPUT_BASE = Path("data/output")


class DataService:
    """Service for accessing extracted frame data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_data_summary(self, job_id: UUID) -> DataSummary | None:
        """Get summary of extracted data for a job."""
        # Get job from database
        result = await self.db.execute(
            select(ProcessingJob, JobConfig)
            .join(JobConfig)
            .where(ProcessingJob.id == job_id)
        )
        row = result.first()
        if row is None:
            return None

        job, config = row[0], row[1]

        # Find output directory
        output_dir = OUTPUT_BASE / str(job_id)
        if not output_dir.exists():
            # Return empty summary if no output yet
            return DataSummary(
                job_id=str(job_id),
                job_name=job.name,
                status=job.status,
                frame_skip=config.frame_skip,
                created_at=job.created_at,
                completed_at=job.completed_at,
            )

        # Aggregate data from all sequences
        total_frames = 0
        frames_with_left = 0
        frames_with_right = 0
        frames_with_depth = 0
        frames_with_pc = 0
        total_detections = 0
        detections_by_class: dict[str, int] = {}
        svo2_files: list[SVO2FileSummary] = []

        # Find all sequence directories
        for seq_dir in output_dir.iterdir():
            if not seq_dir.is_dir():
                continue

            registry_file = seq_dir / "frame_registry.json"
            if not registry_file.exists():
                continue

            try:
                with open(registry_file) as f:
                    registry = json.load(f)

                frames = registry.get("frames", [])
                total_frames += len(frames)

                # Count files
                for frame in frames:
                    if frame.get("image_left"):
                        frames_with_left += 1
                    if frame.get("image_right"):
                        frames_with_right += 1
                    if frame.get("depth"):
                        frames_with_depth += 1
                    if frame.get("point_cloud"):
                        frames_with_pc += 1
                    total_detections += frame.get("detection_count", 0)

                # Get SVO2 file info
                svo2_file = registry.get("svo2_file", seq_dir.name)
                svo2_files.append(SVO2FileSummary(
                    filename=svo2_file,
                    path=str(seq_dir),
                    total_frames_original=registry.get("total_frames"),
                    frames_extracted=len(frames),
                    frame_skip=registry.get("config", {}).get("frame_skip", 1),
                ))

                # Load detections to count by class
                detections_file = seq_dir / "detections" / "detections.json"
                if detections_file.exists():
                    with open(detections_file) as f:
                        detections_data = json.load(f)
                    for frame_data in detections_data.get("frames", {}).values():
                        for det in frame_data.get("detections", []):
                            cls = det.get("class_name", "unknown")
                            detections_by_class[cls] = detections_by_class.get(cls, 0) + 1

            except Exception as e:
                logger.error(f"Error reading registry {registry_file}: {e}")
                continue

        return DataSummary(
            job_id=str(job_id),
            job_name=job.name,
            status=job.status,
            total_frames=total_frames,
            frames_with_left_image=frames_with_left,
            frames_with_right_image=frames_with_right,
            frames_with_depth=frames_with_depth,
            frames_with_pointcloud=frames_with_pc,
            total_detections=total_detections,
            detections_by_class=detections_by_class,
            total_tracks=0,  # TODO: Count from tracks.json
            svo2_files=svo2_files,
            output_directory=str(output_dir) if output_dir.exists() else None,
            frame_skip=config.frame_skip,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )

    async def list_frames(
        self,
        job_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> FrameListResponse:
        """List frames for a job."""
        output_dir = OUTPUT_BASE / str(job_id)
        all_frames: list[FrameSummary] = []

        if output_dir.exists():
            # Find all sequence directories
            for seq_dir in sorted(output_dir.iterdir()):
                if not seq_dir.is_dir():
                    continue

                registry_file = seq_dir / "frame_registry.json"
                if not registry_file.exists():
                    continue

                try:
                    with open(registry_file) as f:
                        registry = json.load(f)

                    svo2_file = registry.get("svo2_file", seq_dir.name)

                    for frame in registry.get("frames", []):
                        frame_id = frame.get("frame_id", "")
                        seq_idx = frame.get("sequence_index", 0)

                        all_frames.append(FrameSummary(
                            id=frame_id,
                            frame_id=frame_id,
                            sequence_index=seq_idx,
                            svo2_frame_index=frame.get("svo2_frame_index", seq_idx),
                            svo2_file=svo2_file,
                            timestamp_ns=frame.get("timestamp_ns"),
                            has_left_image=bool(frame.get("image_left")),
                            has_right_image=bool(frame.get("image_right")),
                            has_depth=bool(frame.get("depth")),
                            has_pointcloud=bool(frame.get("point_cloud")),
                            detection_count=frame.get("detection_count", 0),
                            thumbnail_url=f"/api/data/jobs/{job_id}/frames/{frame_id}/image/left" if frame.get("image_left") else None,
                        ))

                except Exception as e:
                    logger.error(f"Error reading registry {registry_file}: {e}")
                    continue

        # Sort by sequence index
        all_frames.sort(key=lambda f: f.sequence_index)

        # Apply pagination
        total = len(all_frames)
        paginated = all_frames[offset:offset + limit]

        return FrameListResponse(
            frames=paginated,
            total=total,
            limit=limit,
            offset=offset,
            job_id=str(job_id),
        )

    async def get_frame_detail(
        self,
        job_id: UUID,
        frame_id: str,
    ) -> FrameDetail | None:
        """Get detailed frame information."""
        output_dir = OUTPUT_BASE / str(job_id)
        if not output_dir.exists():
            return None

        # Search for the frame in all sequences
        for seq_dir in output_dir.iterdir():
            if not seq_dir.is_dir():
                continue

            registry_file = seq_dir / "frame_registry.json"
            if not registry_file.exists():
                continue

            try:
                with open(registry_file) as f:
                    registry = json.load(f)

                svo2_file = registry.get("svo2_file", seq_dir.name)

                for frame in registry.get("frames", []):
                    if frame.get("frame_id") == frame_id:
                        # Found the frame
                        seq_idx = frame.get("sequence_index", 0)
                        base_url = f"/api/data/jobs/{job_id}/frames/{frame_id}"

                        # Load annotations
                        annotations = self._load_frame_annotations(
                            seq_dir, frame_id, str(job_id)
                        )

                        return FrameDetail(
                            id=frame_id,
                            frame_id=frame_id,
                            sequence_index=seq_idx,
                            svo2_frame_index=frame.get("svo2_frame_index", seq_idx),
                            svo2_file=svo2_file,
                            timestamp_ns=frame.get("timestamp_ns"),
                            image_left_url=f"{base_url}/image/left" if frame.get("image_left") else None,
                            image_right_url=f"{base_url}/image/right" if frame.get("image_right") else None,
                            depth_url=f"{base_url}/image/depth" if frame.get("depth") else None,
                            pointcloud_url=f"{base_url}/pointcloud" if frame.get("point_cloud") else None,
                            segmentation_complete=frame.get("segmentation_complete", False),
                            reconstruction_complete=frame.get("reconstruction_complete", False),
                            tracking_complete=frame.get("tracking_complete", False),
                            annotations=annotations,
                            metadata=self._load_frame_metadata(seq_dir, frame),
                        )

            except Exception as e:
                logger.error(f"Error reading registry {registry_file}: {e}")
                continue

        return None

    def _load_frame_annotations(
        self,
        seq_dir: Path,
        frame_id: str,
        job_id: str,
    ) -> list[AnnotationSummary]:
        """Load annotations for a frame."""
        annotations: list[AnnotationSummary] = []

        detections_file = seq_dir / "detections" / "detections.json"
        if not detections_file.exists():
            return annotations

        # Check if masks directory exists
        masks_dir = seq_dir / "detections" / "masks"
        masks_available = masks_dir.exists()

        try:
            with open(detections_file) as f:
                detections_data = json.load(f)

            frame_detections = detections_data.get("frames", {}).get(frame_id, {})
            for i, det in enumerate(frame_detections.get("detections", [])):
                bbox = det.get("bbox", [0, 0, 0, 0])

                # Check if mask file exists for this detection
                mask_url = None
                if masks_available:
                    mask_file = masks_dir / f"{frame_id}_{i:03d}.png"
                    if mask_file.exists():
                        mask_url = f"/api/data/jobs/{job_id}/annotations/{frame_id}_{i}/mask"

                annotations.append(AnnotationSummary(
                    id=f"{frame_id}_{i}",
                    class_name=det.get("class_name", "unknown"),
                    class_color=self._get_class_color(det.get("class_name", "")),
                    confidence=det.get("confidence", 0.0),
                    bbox_2d=BBox2D(
                        x=bbox[0] if len(bbox) > 0 else 0,
                        y=bbox[1] if len(bbox) > 1 else 0,
                        width=bbox[2] if len(bbox) > 2 else 0,
                        height=bbox[3] if len(bbox) > 3 else 0,
                    ),
                    bbox_3d=None,  # 3D boxes computed separately in reconstruction
                    mask_url=mask_url,
                ))

        except Exception as e:
            logger.error(f"Error loading annotations: {e}")

        return annotations

    def _load_frame_metadata(
        self,
        seq_dir: Path,
        frame: dict,
    ) -> FrameMetadataSummary | None:
        """Load frame metadata including IMU data."""
        import math

        imu_path = frame.get("imu")
        if not imu_path:
            return None

        imu_file = seq_dir / imu_path
        if not imu_file.exists():
            return None

        try:
            with open(imu_file) as f:
                values = f.read().strip().split()
                if len(values) >= 20:
                    # KITTI oxts format indices:
                    # 3, 4, 5 = roll, pitch, yaw (radians)
                    # 11, 12, 13 = ax, ay, az (m/s²)
                    # 17, 18, 19 = wx, wy, wz (rad/s)
                    roll_rad = float(values[3])
                    pitch_rad = float(values[4])
                    yaw_rad = float(values[5])

                    return FrameMetadataSummary(
                        accel_x=float(values[11]),
                        accel_y=float(values[12]),
                        accel_z=float(values[13]),
                        gyro_x=float(values[17]),
                        gyro_y=float(values[18]),
                        gyro_z=float(values[19]),
                        # Convert orientation from radians to degrees
                        orientation_roll=math.degrees(roll_rad),
                        orientation_pitch=math.degrees(pitch_rad),
                        orientation_yaw=math.degrees(yaw_rad),
                    )
        except Exception as e:
            logger.error(f"Error loading IMU data: {e}")

        return None

    def _get_class_color(self, class_name: str) -> str:
        """Get color for a class name."""
        # Default colors for common classes
        colors = {
            "person": "#ef4444",
            "pedestrian": "#ef4444",
            "car": "#3b82f6",
            "truck": "#8b5cf6",
            "van": "#6366f1",
            "cyclist": "#22c55e",
            "motorcycle": "#f59e0b",
            "traffic light": "#eab308",
            "traffic sign": "#f97316",
        }
        return colors.get(class_name.lower(), "#6b7280")

    def get_frame_file_path(
        self,
        job_id: UUID,
        frame_id: str,
        file_type: str,
    ) -> Path | None:
        """Get the file path for a frame file."""
        output_dir = OUTPUT_BASE / str(job_id)
        if not output_dir.exists():
            return None

        # Search for the frame in all sequences
        for seq_dir in output_dir.iterdir():
            if not seq_dir.is_dir():
                continue

            registry_file = seq_dir / "frame_registry.json"
            if not registry_file.exists():
                continue

            try:
                with open(registry_file) as f:
                    registry = json.load(f)

                for frame in registry.get("frames", []):
                    if frame.get("frame_id") == frame_id:
                        # Found the frame - get the requested file
                        path_key = {
                            "left": "image_left",
                            "right": "image_right",
                            "depth": "depth",
                            "pointcloud": "point_cloud",
                        }.get(file_type)

                        if path_key and frame.get(path_key):
                            return seq_dir / frame[path_key]

            except Exception as e:
                logger.error(f"Error reading registry: {e}")
                continue

        return None

    def get_mask_file_path(
        self,
        job_id: UUID,
        annotation_id: str,
    ) -> Path | None:
        """
        Get the file path for an annotation mask.

        Args:
            job_id: The job UUID
            annotation_id: Format is '{frame_id}_{detection_index}'
        """
        output_dir = OUTPUT_BASE / str(job_id)
        if not output_dir.exists():
            return None

        # Parse annotation_id to get frame_id and detection index
        # Format: {frame_id}_{detection_index} where frame_id is like "abc123_000000"
        # So annotation_id is like "abc123_000000_0" or "abc123_000000_12"
        parts = annotation_id.rsplit("_", 1)
        if len(parts) != 2:
            return None

        frame_id = parts[0]
        try:
            det_idx = int(parts[1])
        except ValueError:
            return None

        # Search for the mask in all sequence directories
        for seq_dir in output_dir.iterdir():
            if not seq_dir.is_dir():
                continue

            # Mask files are stored as: detections/masks/{frame_id}_{idx:03d}.png
            mask_file = seq_dir / "detections" / "masks" / f"{frame_id}_{det_idx:03d}.png"
            if mask_file.exists():
                return mask_file

        return None

    async def get_correlation_table(
        self,
        job_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> CorrelationTableResponse | None:
        """Get correlation table for a job."""
        output_dir = OUTPUT_BASE / str(job_id)
        if not output_dir.exists():
            return None

        entries: list[CorrelationEntry] = []
        svo2_file = ""
        frame_skip = 1

        for seq_dir in output_dir.iterdir():
            if not seq_dir.is_dir():
                continue

            registry_file = seq_dir / "frame_registry.json"
            if not registry_file.exists():
                continue

            try:
                with open(registry_file) as f:
                    registry = json.load(f)

                svo2_file = registry.get("svo2_file", seq_dir.name)
                frame_skip = registry.get("config", {}).get("frame_skip", 1)

                for frame in registry.get("frames", []):
                    entries.append(CorrelationEntry(
                        sequence_index=frame.get("sequence_index", 0),
                        svo2_frame_index=frame.get("svo2_frame_index", 0),
                        frame_id=frame.get("frame_id", ""),
                        has_left_image=bool(frame.get("image_left")),
                        has_right_image=bool(frame.get("image_right")),
                        has_depth=bool(frame.get("depth")),
                        has_pointcloud=bool(frame.get("point_cloud")),
                        has_imu=bool(frame.get("imu")),
                        detection_count=frame.get("detection_count", 0),
                    ))

            except Exception as e:
                logger.error(f"Error reading registry: {e}")
                continue

        # Sort and paginate
        entries.sort(key=lambda e: e.sequence_index)
        total = len(entries)
        entries = entries[offset:offset + limit]

        return CorrelationTableResponse(
            entries=entries,
            total=total,
            svo2_file=svo2_file,
            frame_skip=frame_skip,
        )
