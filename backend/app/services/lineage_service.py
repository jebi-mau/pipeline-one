"""Lineage service for data traceability queries."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.dataset import Dataset, DatasetFile
from backend.app.models.external_annotation import AnnotationImport, ExternalAnnotation
from backend.app.models.frame import Frame, FrameMetadata
from backend.app.models.job import ProcessingJob
from backend.app.models.lineage import DataLineageEvent

if TYPE_CHECKING:
    pass


class LineageService:
    """Service for querying data lineage and traceability."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def get_frame_lineage(self, frame_id: uuid.UUID) -> dict | None:
        """
        Get complete lineage for a frame.

        Returns:
            Dictionary containing frame details with full lineage to
            dataset file, dataset, job, annotations, and exports.
        """
        # Query frame with all relationships
        query = (
            select(Frame)
            .options(
                selectinload(Frame.job).selectinload(ProcessingJob.dataset),
                selectinload(Frame.dataset_file).selectinload(DatasetFile.dataset),
                selectinload(Frame.frame_metadata),
                selectinload(Frame.annotations),
            )
            .where(Frame.id == frame_id)
        )
        result = await self.db.execute(query)
        frame = result.scalar_one_or_none()

        if not frame:
            return None

        # Build lineage response
        lineage = {
            "frame": {
                "id": str(frame.id),
                "svo2_file_path": frame.svo2_file_path,
                "svo2_frame_index": frame.svo2_frame_index,
                "original_svo2_filename": frame.original_svo2_filename,
                "original_unix_timestamp": frame.original_unix_timestamp,
                "timestamp_ns": frame.timestamp_ns,
                "sequence_index": frame.sequence_index,
                "image_left_path": frame.image_left_path,
                "image_right_path": frame.image_right_path,
                "depth_path": frame.depth_path,
                "numpy_path": frame.numpy_path,
                "extraction_status": frame.extraction_status,
                "created_at": frame.created_at.isoformat() if frame.created_at else None,
            },
            "dataset_file": None,
            "dataset": None,
            "job": None,
            "annotations": [],
            "sensor_data": None,
        }

        # Add dataset file info
        if frame.dataset_file:
            df = frame.dataset_file
            lineage["dataset_file"] = {
                "id": str(df.id),
                "original_filename": df.original_filename,
                "camera_serial": df.camera_serial,
                "camera_model": df.camera_model,
                "frame_count": df.frame_count,
                "recording_start_ns": df.recording_start_ns,
                "video_codec": df.video_codec,
                "compression_mode": df.compression_mode,
                "status": df.status,
            }
            # Include dataset from file if available
            if df.dataset:
                lineage["dataset"] = {
                    "id": str(df.dataset.id),
                    "name": df.dataset.name,
                    "customer": df.dataset.customer,
                    "site": df.dataset.site,
                    "equipment": df.dataset.equipment,
                }

        # Add job info
        if frame.job:
            job = frame.job
            lineage["job"] = {
                "id": str(job.id),
                "name": job.name,
                "status": job.status,
                "current_stage": job.current_stage,
                "depth_mode": job.depth_mode,
                "started_at": job.started_at.isoformat() if job.started_at else None,
            }
            # Override dataset if job has direct link
            if job.dataset and not lineage["dataset"]:
                lineage["dataset"] = {
                    "id": str(job.dataset.id),
                    "name": job.dataset.name,
                    "customer": job.dataset.customer,
                    "site": job.dataset.site,
                    "equipment": job.dataset.equipment,
                }

        # Add sensor data from metadata
        if frame.frame_metadata:
            meta = frame.frame_metadata
            lineage["sensor_data"] = {
                "imu": {
                    "accel": {"x": meta.accel_x, "y": meta.accel_y, "z": meta.accel_z},
                    "gyro": {"x": meta.gyro_x, "y": meta.gyro_y, "z": meta.gyro_z},
                    "orientation": {
                        "w": meta.orientation_w,
                        "x": meta.orientation_x,
                        "y": meta.orientation_y,
                        "z": meta.orientation_z,
                    },
                },
                "magnetometer": {
                    "x": meta.mag_x,
                    "y": meta.mag_y,
                    "z": meta.mag_z,
                } if meta.mag_x is not None else None,
                "barometer": {
                    "pressure_hpa": meta.pressure_hpa,
                    "altitude_m": meta.altitude_m,
                } if meta.pressure_hpa is not None else None,
                "temperature": {
                    "imu_c": meta.imu_temperature_c,
                    "barometer_c": meta.barometer_temperature_c,
                },
            }

        # Get external annotations for this frame
        annotation_query = (
            select(ExternalAnnotation)
            .where(ExternalAnnotation.frame_id == frame_id)
        )
        annotation_result = await self.db.execute(annotation_query)
        annotations = annotation_result.scalars().all()

        lineage["annotations"] = [
            {
                "id": str(ann.id),
                "label": ann.label,
                "annotation_type": ann.annotation_type,
                "bbox": ann.bbox,
                "match_strategy": ann.match_strategy,
                "source_image_name": ann.source_image_name,
            }
            for ann in annotations
        ]

        return lineage

    async def get_svo2_lineage(self, dataset_file_id: uuid.UUID) -> dict | None:
        """
        Get lineage for an SVO2 file (DatasetFile).

        Returns:
            Dictionary containing SVO2 file details with parent dataset,
            all extracted frames, and annotation statistics.
        """
        # Query dataset file with relationships
        query = (
            select(DatasetFile)
            .options(selectinload(DatasetFile.dataset))
            .where(DatasetFile.id == dataset_file_id)
        )
        result = await self.db.execute(query)
        dataset_file = result.scalar_one_or_none()

        if not dataset_file:
            return None

        # Build response
        lineage = {
            "dataset_file": {
                "id": str(dataset_file.id),
                "original_filename": dataset_file.original_filename,
                "original_path": dataset_file.original_path,
                "renamed_filename": dataset_file.renamed_filename,
                "camera_serial": dataset_file.camera_serial,
                "camera_model": dataset_file.camera_model,
                "file_size": dataset_file.file_size,
                "frame_count": dataset_file.frame_count,
                "fps": dataset_file.fps,
                "recording_start_ns": dataset_file.recording_start_ns,
                "recording_duration_ms": dataset_file.recording_duration_ms,
                "resolution": {
                    "width": dataset_file.resolution_width,
                    "height": dataset_file.resolution_height,
                } if dataset_file.resolution_width else None,
                "video_codec": dataset_file.video_codec,
                "compression_mode": dataset_file.compression_mode,
                "bitrate_kbps": dataset_file.bitrate_kbps,
                "status": dataset_file.status,
            },
            "dataset": None,
            "frames": [],
            "annotation_stats": {
                "total_annotations": 0,
                "matched": 0,
                "unmatched": 0,
            },
        }

        # Add dataset info
        if dataset_file.dataset:
            ds = dataset_file.dataset
            lineage["dataset"] = {
                "id": str(ds.id),
                "name": ds.name,
                "description": ds.description,
                "customer": ds.customer,
                "site": ds.site,
                "equipment": ds.equipment,
                "status": ds.status,
            }

        # Get frames from this SVO2 file
        frames_query = (
            select(Frame)
            .where(Frame.dataset_file_id == dataset_file_id)
            .order_by(Frame.sequence_index)
        )
        frames_result = await self.db.execute(frames_query)
        frames = frames_result.scalars().all()

        lineage["frames"] = [
            {
                "id": str(f.id),
                "sequence_index": f.sequence_index,
                "svo2_frame_index": f.svo2_frame_index,
                "timestamp_ns": f.timestamp_ns,
                "extraction_status": f.extraction_status,
            }
            for f in frames
        ]

        # Get annotation statistics
        frame_ids = [f.id for f in frames]
        if frame_ids:
            # Count matched annotations
            matched_count = await self.db.execute(
                select(func.count(ExternalAnnotation.id))
                .where(ExternalAnnotation.frame_id.in_(frame_ids))
            )
            lineage["annotation_stats"]["matched"] = matched_count.scalar() or 0
            lineage["annotation_stats"]["total_annotations"] = lineage["annotation_stats"]["matched"]

        return lineage

    async def get_annotation_lineage(self, annotation_id: uuid.UUID) -> dict | None:
        """
        Get lineage for an external annotation.

        Returns:
            Dictionary containing annotation details with lineage
            back to frame, SVO2 file, and dataset.
        """
        # Query annotation with relationships
        query = (
            select(ExternalAnnotation)
            .options(
                selectinload(ExternalAnnotation.frame)
                .selectinload(Frame.dataset_file)
                .selectinload(DatasetFile.dataset),
                selectinload(ExternalAnnotation.import_record),
                selectinload(ExternalAnnotation.source_dataset),
            )
            .where(ExternalAnnotation.id == annotation_id)
        )
        result = await self.db.execute(query)
        annotation = result.scalar_one_or_none()

        if not annotation:
            return None

        lineage = {
            "annotation": {
                "id": str(annotation.id),
                "label": annotation.label,
                "annotation_type": annotation.annotation_type,
                "bbox": annotation.bbox,
                "points": annotation.points,
                "source_image_name": annotation.source_image_name,
                "match_strategy": annotation.match_strategy,
                "source_frame_index": annotation.source_frame_index,
                "is_matched": annotation.is_matched,
                "match_confidence": annotation.match_confidence,
                "created_at": annotation.created_at.isoformat() if annotation.created_at else None,
            },
            "import_record": None,
            "frame": None,
            "svo2_file": None,
            "dataset": None,
        }

        # Add import record info
        if annotation.import_record:
            imp = annotation.import_record
            lineage["import_record"] = {
                "id": str(imp.id),
                "source_tool": imp.source_tool,
                "source_format": imp.source_format,
                "source_filename": imp.source_filename,
                "status": imp.status,
                "imported_at": imp.imported_at.isoformat() if imp.imported_at else None,
            }

        # Add frame info
        if annotation.frame:
            frame = annotation.frame
            lineage["frame"] = {
                "id": str(frame.id),
                "svo2_frame_index": frame.svo2_frame_index,
                "sequence_index": frame.sequence_index,
                "timestamp_ns": frame.timestamp_ns,
                "original_svo2_filename": frame.original_svo2_filename,
            }

            # Add SVO2 file info
            if frame.dataset_file:
                df = frame.dataset_file
                lineage["svo2_file"] = {
                    "id": str(df.id),
                    "original_filename": df.original_filename,
                    "camera_serial": df.camera_serial,
                }

                # Add dataset from file
                if df.dataset:
                    lineage["dataset"] = {
                        "id": str(df.dataset.id),
                        "name": df.dataset.name,
                        "customer": df.dataset.customer,
                        "site": df.dataset.site,
                    }

        # Override dataset if annotation has direct link
        if annotation.source_dataset:
            lineage["dataset"] = {
                "id": str(annotation.source_dataset.id),
                "name": annotation.source_dataset.name,
                "customer": annotation.source_dataset.customer,
                "site": annotation.source_dataset.site,
            }

        return lineage

    async def get_dataset_summary(self, dataset_id: uuid.UUID) -> dict | None:
        """
        Get aggregated summary statistics for a dataset.

        Returns:
            Dictionary containing dataset info with file counts,
            frame counts, annotation stats, and processing status.
        """
        # Query dataset
        query = (
            select(Dataset)
            .options(selectinload(Dataset.files), selectinload(Dataset.jobs))
            .where(Dataset.id == dataset_id)
        )
        result = await self.db.execute(query)
        dataset = result.scalar_one_or_none()

        if not dataset:
            return None

        # Build summary
        summary = {
            "dataset": {
                "id": str(dataset.id),
                "name": dataset.name,
                "description": dataset.description,
                "customer": dataset.customer,
                "site": dataset.site,
                "equipment": dataset.equipment,
                "status": dataset.status,
                "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
            },
            "files": {
                "total": len(dataset.files),
                "by_status": {},
                "total_size_bytes": 0,
                "cameras": set(),
            },
            "frames": {
                "total": 0,
                "extracted": 0,
            },
            "annotations": {
                "total_imports": 0,
                "total_annotations": 0,
                "matched": 0,
                "unmatched": 0,
            },
            "jobs": {
                "total": len(dataset.jobs),
                "by_status": {},
            },
        }

        # Aggregate file stats
        for f in dataset.files:
            summary["files"]["total_size_bytes"] += f.file_size or 0
            status = f.status or "unknown"
            summary["files"]["by_status"][status] = summary["files"]["by_status"].get(status, 0) + 1
            if f.camera_serial:
                summary["files"]["cameras"].add(f.camera_serial)

        summary["files"]["cameras"] = list(summary["files"]["cameras"])

        # Count frames
        file_ids = [f.id for f in dataset.files]
        if file_ids:
            frame_count_result = await self.db.execute(
                select(func.count(Frame.id))
                .where(Frame.dataset_file_id.in_(file_ids))
            )
            summary["frames"]["total"] = frame_count_result.scalar() or 0

            extracted_count_result = await self.db.execute(
                select(func.count(Frame.id))
                .where(Frame.dataset_file_id.in_(file_ids))
                .where(Frame.extraction_status == "completed")
            )
            summary["frames"]["extracted"] = extracted_count_result.scalar() or 0

        # Count annotations
        import_count_result = await self.db.execute(
            select(func.count(AnnotationImport.id))
            .where(AnnotationImport.dataset_id == dataset_id)
        )
        summary["annotations"]["total_imports"] = import_count_result.scalar() or 0

        # Get annotation stats from imports
        import_stats = await self.db.execute(
            select(
                func.sum(AnnotationImport.total_annotations),
                func.sum(AnnotationImport.matched_frames),
                func.sum(AnnotationImport.unmatched_images),
            )
            .where(AnnotationImport.dataset_id == dataset_id)
        )
        stats_row = import_stats.first()
        if stats_row:
            summary["annotations"]["total_annotations"] = stats_row[0] or 0
            summary["annotations"]["matched"] = stats_row[1] or 0
            summary["annotations"]["unmatched"] = stats_row[2] or 0

        # Aggregate job stats
        for job in dataset.jobs:
            status = job.status or "unknown"
            summary["jobs"]["by_status"][status] = summary["jobs"]["by_status"].get(status, 0) + 1

        return summary

    async def log_lineage_event(
        self,
        event_type: str,
        dataset_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        dataset_file_id: uuid.UUID | None = None,
        frame_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> DataLineageEvent:
        """
        Log a data lineage event for audit trail.

        Args:
            event_type: Type of event (extraction, annotation_import, export, scan, prepare)
            dataset_id: Optional related dataset ID
            job_id: Optional related job ID
            dataset_file_id: Optional related file ID
            frame_id: Optional related frame ID
            details: Optional JSON details

        Returns:
            Created DataLineageEvent
        """
        event = DataLineageEvent(
            event_type=event_type,
            dataset_id=dataset_id,
            job_id=job_id,
            dataset_file_id=dataset_file_id,
            frame_id=frame_id,
            details=details,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_lineage_events(
        self,
        dataset_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get lineage events with optional filtering.

        Args:
            dataset_id: Filter by dataset
            job_id: Filter by job
            event_type: Filter by event type
            limit: Maximum number of events to return

        Returns:
            List of lineage event dictionaries
        """
        query = select(DataLineageEvent).order_by(DataLineageEvent.created_at.desc())

        if dataset_id:
            query = query.where(DataLineageEvent.dataset_id == dataset_id)
        if job_id:
            query = query.where(DataLineageEvent.job_id == job_id)
        if event_type:
            query = query.where(DataLineageEvent.event_type == event_type)

        query = query.limit(limit)

        result = await self.db.execute(query)
        events = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "dataset_id": str(e.dataset_id) if e.dataset_id else None,
                "job_id": str(e.job_id) if e.job_id else None,
                "dataset_file_id": str(e.dataset_file_id) if e.dataset_file_id else None,
                "frame_id": str(e.frame_id) if e.frame_id else None,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
