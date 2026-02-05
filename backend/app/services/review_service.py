"""Review service for annotation statistics and frame filtering."""

import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ProcessingJob
from backend.app.schemas.review import (
    AnnotationClassStats,
    AnnotationStatsResponse,
    FilterConfiguration,
    FrameBatchResponse,
    FrameThumbnail,
)
from backend.app.services.data_service import DataService

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for review mode operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_service = DataService(db)

    # Class colors (consistent with frontend)
    CLASS_COLORS = {
        "person": "#EF4444",
        "car": "#3B82F6",
        "truck": "#10B981",
        "bus": "#F59E0B",
        "motorcycle": "#8B5CF6",
        "bicycle": "#EC4899",
        "train": "#06B6D4",
        "boat": "#6366F1",
        "airplane": "#14B8A6",
        "default": "#6B7280",
    }

    def _get_class_color(self, class_name: str) -> str:
        """Get color for a class name."""
        return self.CLASS_COLORS.get(class_name.lower(), self.CLASS_COLORS["default"])

    async def get_annotation_stats(self, job_id: UUID) -> AnnotationStatsResponse:
        """Get aggregated annotation statistics by class for filtering UI."""
        # Get job to verify it exists
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Get data summary to find output directory
        summary = await self.data_service.get_data_summary(str(job_id))
        if not summary:
            return AnnotationStatsResponse(
                job_id=str(job_id),
                total_annotations=0,
                total_frames=0,
                classes=[],
            )

        # Aggregate annotations by class
        class_stats: dict[str, dict] = defaultdict(
            lambda: {
                "total_count": 0,
                "frame_ids": set(),
                "confidences": [],
                "annotation_ids": [],
            }
        )

        total_frames = 0
        total_annotations = 0

        # Iterate through all frames and annotations
        frames_list = await self.data_service.list_frames(str(job_id), limit=10000)
        for frame in frames_list.frames:
            total_frames += 1
            frame_detail = await self.data_service.get_frame_detail(
                str(job_id), frame.frame_id
            )
            if frame_detail and frame_detail.annotations:
                for ann in frame_detail.annotations:
                    class_name = ann.class_name
                    class_stats[class_name]["total_count"] += 1
                    class_stats[class_name]["frame_ids"].add(frame.frame_id)
                    class_stats[class_name]["confidences"].append(ann.confidence)
                    class_stats[class_name]["annotation_ids"].append(ann.id)
                    total_annotations += 1

        # Build response
        classes = []
        for class_name, stats in sorted(class_stats.items()):
            avg_confidence = (
                sum(stats["confidences"]) / len(stats["confidences"])
                if stats["confidences"]
                else 0.0
            )
            classes.append(
                AnnotationClassStats(
                    class_name=class_name,
                    class_color=self._get_class_color(class_name),
                    total_count=stats["total_count"],
                    frame_count=len(stats["frame_ids"]),
                    avg_confidence=round(avg_confidence, 3),
                    annotation_ids=stats["annotation_ids"],
                )
            )

        return AnnotationStatsResponse(
            job_id=str(job_id),
            total_annotations=total_annotations,
            total_frames=total_frames,
            classes=classes,
        )

    async def get_frame_batch(
        self, job_id: UUID, start_index: int, count: int
    ) -> FrameBatchResponse:
        """Get batch of frames for video playback."""
        frames_list = await self.data_service.list_frames(
            str(job_id), limit=count, offset=start_index
        )

        thumbnails = []
        for frame in frames_list.frames:
            thumbnails.append(
                FrameThumbnail(
                    frame_id=frame.frame_id,
                    sequence_index=frame.sequence_index,
                    svo2_frame_index=frame.svo2_frame_index,
                    thumbnail_url=f"/api/data/jobs/{job_id}/frames/{frame.frame_id}/left",
                    annotation_count=frame.detection_count,
                )
            )

        return FrameBatchResponse(
            job_id=str(job_id),
            frames=thumbnails,
            total_frames=frames_list.total,
            start_index=start_index,
            has_more=start_index + count < frames_list.total,
        )

    async def compute_selected_frames(
        self, job_id: UUID, filter_config: FilterConfiguration
    ) -> list[str]:
        """Compute which frame IDs pass all filters."""
        # Get all frames
        frames_list = await self.data_service.list_frames(str(job_id), limit=10000)

        selected_frame_ids = []
        excluded_indices = set(filter_config.excluded_frame_indices)

        for i, frame in enumerate(frames_list.frames):
            # Check if frame index is excluded (from diversity filtering)
            if i in excluded_indices:
                continue

            # If we need to check annotations, load frame detail
            if filter_config.excluded_classes or filter_config.excluded_annotation_ids:
                frame_detail = await self.data_service.get_frame_detail(
                    str(job_id), frame.frame_id
                )
                if frame_detail and frame_detail.annotations:
                    # Check if frame has any non-excluded annotations
                    has_valid_annotation = False
                    for ann in frame_detail.annotations:
                        # Skip if class is excluded
                        if ann.class_name in filter_config.excluded_classes:
                            continue
                        # Skip if individual annotation is excluded
                        if ann.id in filter_config.excluded_annotation_ids:
                            continue
                        has_valid_annotation = True
                        break

                    if not has_valid_annotation:
                        continue

            selected_frame_ids.append(frame.frame_id)

        return selected_frame_ids
