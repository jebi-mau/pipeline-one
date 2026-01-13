"""Frame diversity analysis service using perceptual hashing and motion estimation."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import numpy as np
from PIL import Image
from scipy import ndimage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ProcessingJob
from backend.app.models.training_dataset import FrameDiversityCache
from backend.app.schemas.review import (
    DiversityAnalysisResponse,
    FrameCluster,
)
from backend.app.services.data_service import DataService

logger = logging.getLogger(__name__)


def compute_dhash(image: Image.Image, hash_size: int = 16) -> str:
    """
    Compute difference hash (dHash) for an image.

    dHash is fast and effective for detecting near-duplicates.
    It compares adjacent pixels to generate a hash.
    """
    # Resize to hash_size+1 x hash_size
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(resized)

    # Compute differences between adjacent pixels
    diff = pixels[:, 1:] > pixels[:, :-1]

    # Convert to hex string
    return "".join(format(byte, "02x") for byte in np.packbits(diff.flatten()))


def compute_hash_similarity(hash1: str, hash2: str) -> float:
    """
    Compute similarity between two hashes using Hamming distance.

    Returns value between 0 (completely different) and 1 (identical).
    """
    if len(hash1) != len(hash2):
        return 0.0

    # Convert hex to binary
    bits1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
    bits2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)

    # Count differing bits
    diff_count = sum(b1 != b2 for b1, b2 in zip(bits1, bits2))

    # Return similarity (1 - normalized distance)
    return 1.0 - (diff_count / len(bits1))


def compute_motion_score(prev_path: Path, curr_path: Path) -> float:
    """
    Compute motion score between two frames using frame differencing.

    Returns value between 0 (no motion) and 1 (maximum motion).
    """
    try:
        prev = np.array(Image.open(prev_path).convert("L"), dtype=np.float32)
        curr = np.array(Image.open(curr_path).convert("L"), dtype=np.float32)

        # Compute absolute difference
        diff = np.abs(prev - curr)

        # Apply Gaussian blur to reduce noise
        diff = ndimage.gaussian_filter(diff, sigma=2)

        # Normalize to 0-1
        motion_score = float(np.mean(diff) / 255.0)
        return motion_score
    except Exception as e:
        logger.warning(f"Error computing motion score: {e}")
        return 0.0


class DiversityService:
    """Service for frame diversity analysis."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_service = DataService(db)

    async def get_cached_analysis(self, job_id: UUID) -> FrameDiversityCache | None:
        """Get cached diversity data if available."""
        result = await self.db.execute(
            select(FrameDiversityCache).where(FrameDiversityCache.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def analyze_diversity(
        self,
        job_id: UUID,
        similarity_threshold: float = 0.85,
        motion_threshold: float = 0.02,
        camera: str = "left",
        use_cache: bool = True,
    ) -> DiversityAnalysisResponse:
        """
        Analyze frame diversity using perceptual hashing and motion estimation.

        Args:
            job_id: The processing job ID
            similarity_threshold: Frames with similarity > this are duplicates (0-1)
            motion_threshold: Frames with motion < this are low-motion (0-1)
            camera: Which camera to analyze ("left" or "right")
            use_cache: Whether to use cached hash/motion data

        Returns:
            DiversityAnalysisResponse with selected/excluded frames and clusters
        """
        # Get job to verify it exists and get output directory
        result = await self.db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Check for cached data
        cache = await self.get_cached_analysis(job_id) if use_cache else None
        perceptual_hashes: dict[str, str] = {}
        motion_scores: dict[str, float] = {}

        if cache and cache.status == "complete":
            perceptual_hashes = cache.perceptual_hashes
            motion_scores = cache.motion_scores
        else:
            # Need to compute from scratch
            perceptual_hashes, motion_scores = await self._compute_diversity_metrics(
                job_id, camera
            )

            # Save to cache
            await self._save_to_cache(
                job_id, camera, perceptual_hashes, motion_scores
            )

        # Get frame order
        frames_list = await self.data_service.list_frames(str(job_id), limit=10000)
        frame_ids = [f.frame_id for f in frames_list.frames]

        # Run selection algorithm
        selected, excluded, clusters = self._select_diverse_frames(
            frame_ids,
            perceptual_hashes,
            motion_scores,
            similarity_threshold,
            motion_threshold,
        )

        # Count low motion frames
        low_motion_count = sum(
            1
            for i, fid in enumerate(frame_ids)
            if i > 0 and motion_scores.get(fid, 1.0) < motion_threshold
        )

        reduction_pct = (
            (len(excluded) / len(frame_ids) * 100) if frame_ids else 0.0
        )

        return DiversityAnalysisResponse(
            job_id=str(job_id),
            status="complete",
            selected_frame_indices=selected,
            excluded_frame_indices=excluded,
            clusters=clusters,
            original_frame_count=len(frame_ids),
            selected_frame_count=len(selected),
            reduction_percent=round(reduction_pct, 1),
            duplicate_pairs_found=len(clusters),
            low_motion_frames=low_motion_count,
            perceptual_hashes={i: perceptual_hashes.get(fid, "") for i, fid in enumerate(frame_ids)},
            motion_scores={i: motion_scores.get(fid, 0.0) for i, fid in enumerate(frame_ids)},
        )

    async def _compute_diversity_metrics(
        self, job_id: UUID, camera: str
    ) -> tuple[dict[str, str], dict[str, float]]:
        """Compute perceptual hashes and motion scores for all frames."""
        frames_list = await self.data_service.list_frames(str(job_id), limit=10000)

        perceptual_hashes: dict[str, str] = {}
        motion_scores: dict[str, float] = {}

        prev_path: Path | None = None

        for frame in frames_list.frames:
            frame_id = frame.frame_id

            # Get image path
            image_path = await self.data_service.get_frame_file_path(
                str(job_id), frame_id, camera
            )
            if not image_path or not image_path.exists():
                continue

            # Compute perceptual hash
            try:
                img = Image.open(image_path)
                perceptual_hashes[frame_id] = compute_dhash(img)
            except Exception as e:
                logger.warning(f"Error hashing frame {frame_id}: {e}")

            # Compute motion score (relative to previous frame)
            if prev_path and prev_path.exists():
                motion_scores[frame_id] = compute_motion_score(prev_path, image_path)
            else:
                motion_scores[frame_id] = 1.0  # First frame has "full motion"

            prev_path = image_path

        return perceptual_hashes, motion_scores

    async def _save_to_cache(
        self,
        job_id: UUID,
        camera: str,
        perceptual_hashes: dict[str, str],
        motion_scores: dict[str, float],
    ) -> None:
        """Save computed metrics to database cache."""
        # Check if cache entry exists
        cache = await self.get_cached_analysis(job_id)

        if cache:
            # Update existing
            cache.camera = camera
            cache.perceptual_hashes = perceptual_hashes
            cache.motion_scores = motion_scores
            cache.status = "complete"
            cache.analyzed_frames = len(perceptual_hashes)
            cache.total_frames = len(perceptual_hashes)
            cache.completed_at = datetime.now(timezone.utc)
        else:
            # Create new
            cache = FrameDiversityCache(
                job_id=job_id,
                camera=camera,
                perceptual_hashes=perceptual_hashes,
                motion_scores=motion_scores,
                status="complete",
                analyzed_frames=len(perceptual_hashes),
                total_frames=len(perceptual_hashes),
                completed_at=datetime.now(timezone.utc),
            )
            self.db.add(cache)

        await self.db.commit()

    def _select_diverse_frames(
        self,
        frame_ids: list[str],
        hashes: dict[str, str],
        motion_scores: dict[str, float],
        similarity_threshold: float,
        motion_threshold: float,
    ) -> tuple[list[int], list[int], list[FrameCluster]]:
        """
        Select diverse frames using combined similarity and motion filtering.

        Returns:
            - List of selected frame indices
            - List of excluded frame indices
            - List of similarity clusters
        """
        selected: list[int] = []
        excluded: list[int] = []
        clusters: list[FrameCluster] = []

        # Track which frames belong to which cluster
        cluster_map: dict[int, list[int]] = {}  # representative_index -> member_indices

        for i, frame_id in enumerate(frame_ids):
            frame_hash = hashes.get(frame_id, "")
            frame_motion = motion_scores.get(frame_id, 1.0)

            # Skip low-motion frames (except first in sequence)
            if i > 0 and frame_motion < motion_threshold:
                excluded.append(i)
                continue

            # Check similarity against already selected frames
            is_duplicate = False
            similar_to: int | None = None

            for sel_idx in selected:
                sel_frame_id = frame_ids[sel_idx]
                sel_hash = hashes.get(sel_frame_id, "")

                if frame_hash and sel_hash:
                    similarity = compute_hash_similarity(frame_hash, sel_hash)
                    if similarity > similarity_threshold:
                        is_duplicate = True
                        similar_to = sel_idx
                        break

            if is_duplicate and similar_to is not None:
                excluded.append(i)
                # Add to cluster
                if similar_to not in cluster_map:
                    cluster_map[similar_to] = [similar_to]
                cluster_map[similar_to].append(i)
            else:
                selected.append(i)

        # Build cluster objects
        for rep_idx, member_indices in cluster_map.items():
            if len(member_indices) > 1:  # Only include actual clusters
                # Calculate average similarity within cluster
                rep_hash = hashes.get(frame_ids[rep_idx], "")
                similarities = []
                for mem_idx in member_indices:
                    if mem_idx != rep_idx:
                        mem_hash = hashes.get(frame_ids[mem_idx], "")
                        if rep_hash and mem_hash:
                            similarities.append(
                                compute_hash_similarity(rep_hash, mem_hash)
                            )

                avg_sim = sum(similarities) / len(similarities) if similarities else 0.0

                clusters.append(
                    FrameCluster(
                        representative_index=rep_idx,
                        member_indices=member_indices,
                        avg_similarity=round(avg_sim, 3),
                    )
                )

        return selected, excluded, clusters
