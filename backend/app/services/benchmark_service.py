"""Service for managing job performance benchmarks and pre-job time estimation."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.job import JobPerformanceBenchmark, ProcessingJob

logger = logging.getLogger(__name__)


# Default FPS benchmarks by stage and model variant
# These are used when no historical data exists
DEFAULT_BENCHMARKS = {
    "sam3_hiera_tiny": {
        "extraction_fps": 30.0,
        "segmentation_fps": 2.5,
        "reconstruction_fps": 50.0,
        "tracking_fps": 100.0,
    },
    "sam3_hiera_small": {
        "extraction_fps": 30.0,
        "segmentation_fps": 1.5,
        "reconstruction_fps": 50.0,
        "tracking_fps": 100.0,
    },
    "sam3_hiera_large": {
        "extraction_fps": 30.0,
        "segmentation_fps": 0.5,
        "reconstruction_fps": 50.0,
        "tracking_fps": 100.0,
    },
}

# Fallback defaults if model not found
DEFAULT_FPS = {
    "extraction_fps": 30.0,
    "segmentation_fps": 1.0,
    "reconstruction_fps": 50.0,
    "tracking_fps": 100.0,
}


class PerformanceBenchmark:
    """Performance benchmark data structure."""

    def __init__(
        self,
        model_variant: str,
        extraction_fps: float,
        segmentation_fps: float,
        reconstruction_fps: float,
        tracking_fps: float,
        sample_count: int = 0,
        is_default: bool = False,
    ):
        self.model_variant = model_variant
        self.extraction_fps = extraction_fps
        self.segmentation_fps = segmentation_fps
        self.reconstruction_fps = reconstruction_fps
        self.tracking_fps = tracking_fps
        self.sample_count = sample_count
        self.is_default = is_default

    def get_stage_fps(self, stage: str) -> float:
        """Get FPS for a specific stage."""
        fps_map = {
            "extraction": self.extraction_fps,
            "segmentation": self.segmentation_fps,
            "reconstruction": self.reconstruction_fps,
            "tracking": self.tracking_fps,
        }
        return fps_map.get(stage, 1.0)


class JobDurationEstimate:
    """Estimated job duration."""

    def __init__(
        self,
        total_frames: int,
        estimated_duration_seconds: int,
        breakdown: dict[str, dict],
        confidence: str,
        based_on_jobs: int,
    ):
        self.total_frames = total_frames
        self.estimated_duration_seconds = estimated_duration_seconds
        self.breakdown = breakdown
        self.confidence = confidence
        self.based_on_jobs = based_on_jobs

    @property
    def estimated_duration_formatted(self) -> str:
        """Format duration as human-readable string."""
        seconds = self.estimated_duration_seconds
        if seconds < 60:
            return "< 1 min"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        if hours > 0:
            return f"~{hours}h {minutes}m"
        return f"~{minutes}m"

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "estimated_total_frames": self.total_frames,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "estimated_duration_formatted": self.estimated_duration_formatted,
            "breakdown": self.breakdown,
            "confidence": self.confidence,
            "based_on_jobs": self.based_on_jobs,
        }


class BenchmarkService:
    """Service for managing performance benchmarks and estimating job durations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_benchmark(self, model_variant: str) -> PerformanceBenchmark:
        """
        Get performance benchmark for a model variant.

        First tries to fetch from database, falls back to defaults if not found.
        """
        # Try to get from database
        query = select(JobPerformanceBenchmark).where(
            JobPerformanceBenchmark.sam3_model_variant == model_variant
        )
        result = await self.db.execute(query)
        benchmark = result.scalar_one_or_none()

        if benchmark and benchmark.sample_count > 0:
            return PerformanceBenchmark(
                model_variant=model_variant,
                extraction_fps=benchmark.avg_extraction_fps or DEFAULT_FPS["extraction_fps"],
                segmentation_fps=benchmark.avg_segmentation_fps or DEFAULT_FPS["segmentation_fps"],
                reconstruction_fps=benchmark.avg_reconstruction_fps or DEFAULT_FPS["reconstruction_fps"],
                tracking_fps=benchmark.avg_tracking_fps or DEFAULT_FPS["tracking_fps"],
                sample_count=benchmark.sample_count,
                is_default=False,
            )

        # Fall back to defaults
        defaults = DEFAULT_BENCHMARKS.get(model_variant, DEFAULT_FPS)
        return PerformanceBenchmark(
            model_variant=model_variant,
            extraction_fps=defaults.get("extraction_fps", DEFAULT_FPS["extraction_fps"]),
            segmentation_fps=defaults.get("segmentation_fps", DEFAULT_FPS["segmentation_fps"]),
            reconstruction_fps=defaults.get("reconstruction_fps", DEFAULT_FPS["reconstruction_fps"]),
            tracking_fps=defaults.get("tracking_fps", DEFAULT_FPS["tracking_fps"]),
            sample_count=0,
            is_default=True,
        )

    async def update_benchmark_from_job(self, job: ProcessingJob) -> None:
        """
        Update benchmarks when a job completes.

        Uses exponential moving average to update FPS values.
        """
        if job.status != "completed":
            return

        model_variant = job.config.sam3_model_variant if job.config else "sam3_hiera_large"

        # Get existing benchmark or create new
        query = select(JobPerformanceBenchmark).where(
            JobPerformanceBenchmark.sam3_model_variant == model_variant
        )
        result = await self.db.execute(query)
        benchmark = result.scalar_one_or_none()

        if not benchmark:
            benchmark = JobPerformanceBenchmark(
                sam3_model_variant=model_variant,
                sample_count=0,
            )
            self.db.add(benchmark)

        # Calculate FPS values from job
        extraction_fps = None
        segmentation_fps = None

        if job.extraction_duration_seconds and job.extraction_duration_seconds > 0:
            frames = job.total_frames or 0
            extraction_fps = frames / job.extraction_duration_seconds

        if job.segmentation_duration_seconds and job.segmentation_duration_seconds > 0:
            frames = job.total_frames or 0
            segmentation_fps = frames / job.segmentation_duration_seconds

        # Update using exponential moving average
        # Alpha controls how much weight to give new data (0.3 = 30% new, 70% old)
        alpha = 0.3
        count = benchmark.sample_count

        if extraction_fps is not None:
            if benchmark.avg_extraction_fps is None or count == 0:
                benchmark.avg_extraction_fps = extraction_fps
            else:
                benchmark.avg_extraction_fps = (
                    alpha * extraction_fps + (1 - alpha) * benchmark.avg_extraction_fps
                )

        if segmentation_fps is not None:
            if benchmark.avg_segmentation_fps is None or count == 0:
                benchmark.avg_segmentation_fps = segmentation_fps
            else:
                benchmark.avg_segmentation_fps = (
                    alpha * segmentation_fps + (1 - alpha) * benchmark.avg_segmentation_fps
                )

        # Also use job-level FPS if available
        if job.extraction_fps and (benchmark.avg_extraction_fps is None or count == 0):
            benchmark.avg_extraction_fps = job.extraction_fps
        if job.segmentation_fps and (benchmark.avg_segmentation_fps is None or count == 0):
            benchmark.avg_segmentation_fps = job.segmentation_fps

        benchmark.sample_count = count + 1

        await self.db.commit()
        logger.info(
            f"Updated benchmark for {model_variant}: "
            f"extraction={benchmark.avg_extraction_fps:.2f} fps, "
            f"segmentation={benchmark.avg_segmentation_fps:.2f} fps, "
            f"samples={benchmark.sample_count}"
        )

    async def estimate_job_duration(
        self,
        total_frames: int,
        frame_skip: int,
        model_variant: str,
        stages: list[str],
    ) -> JobDurationEstimate:
        """
        Estimate job duration before it starts.

        Args:
            total_frames: Total frames in source SVO2 files (before frame_skip)
            frame_skip: Frame skip setting
            model_variant: SAM3 model variant
            stages: List of stages to run

        Returns:
            JobDurationEstimate with breakdown by stage
        """
        # Calculate actual frames to process after frame_skip
        frames_to_process = total_frames // frame_skip if frame_skip > 0 else total_frames

        # Get benchmark for this model
        benchmark = await self.get_benchmark(model_variant)

        # Calculate time for each stage
        breakdown = {}
        total_seconds = 0

        for stage in stages:
            fps = benchmark.get_stage_fps(stage)
            if fps > 0:
                stage_seconds = int(frames_to_process / fps)
            else:
                stage_seconds = 0

            breakdown[stage] = {
                "frames": frames_to_process,
                "estimated_seconds": stage_seconds,
                "fps": round(fps, 2),
            }
            total_seconds += stage_seconds

        # Determine confidence level
        if benchmark.is_default:
            confidence = "low"  # Using default benchmarks
        elif benchmark.sample_count < 3:
            confidence = "medium"  # Few samples
        else:
            confidence = "high"  # Based on historical data

        return JobDurationEstimate(
            total_frames=frames_to_process,
            estimated_duration_seconds=total_seconds,
            breakdown=breakdown,
            confidence=confidence,
            based_on_jobs=benchmark.sample_count,
        )

    async def get_all_benchmarks(self) -> list[dict]:
        """Get all stored benchmarks."""
        query = select(JobPerformanceBenchmark).order_by(
            JobPerformanceBenchmark.sam3_model_variant
        )
        result = await self.db.execute(query)
        benchmarks = result.scalars().all()

        return [
            {
                "model_variant": b.sam3_model_variant,
                "avg_extraction_fps": b.avg_extraction_fps,
                "avg_segmentation_fps": b.avg_segmentation_fps,
                "avg_reconstruction_fps": b.avg_reconstruction_fps,
                "avg_tracking_fps": b.avg_tracking_fps,
                "sample_count": b.sample_count,
                "updated_at": b.updated_at.isoformat() if b.updated_at else None,
            }
            for b in benchmarks
        ]
