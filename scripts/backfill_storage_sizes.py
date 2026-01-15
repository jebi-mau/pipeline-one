#!/usr/bin/env python3
"""
Backfill storage_size_bytes for existing jobs and datasets.

Usage:
    python scripts/backfill_storage_sizes.py          # Dry run
    python scripts/backfill_storage_sizes.py --apply  # Apply changes
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import get_settings
from backend.app.models.dataset import Dataset
from backend.app.models.job import ProcessingJob

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_bytes(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_directory_size(path: Path) -> int:
    """Calculate total size of a directory recursively."""
    if not path.exists():
        return 0
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except (OSError, PermissionError):
                pass
    return total


async def backfill_job_sizes(session: AsyncSession, dry_run: bool = True) -> dict:
    """Backfill storage_size_bytes for all jobs with output directories."""
    result = await session.execute(
        select(ProcessingJob).where(
            ProcessingJob.output_directory.isnot(None),
            ProcessingJob.storage_size_bytes.is_(None)
        )
    )
    jobs = result.scalars().all()

    updated = 0
    total_size = 0
    errors = []

    logger.info(f"Found {len(jobs)} jobs without storage size")

    for job in jobs:
        try:
            output_dir = Path(job.output_directory)
            if output_dir.exists():
                size = get_directory_size(output_dir)
                total_size += size

                if not dry_run:
                    job.storage_size_bytes = size
                    updated += 1

                logger.info(f"  Job {job.id}: {format_bytes(size)}")
            else:
                logger.warning(f"  Job {job.id}: Output directory not found: {output_dir}")
        except Exception as e:
            errors.append(f"Job {job.id}: {str(e)}")
            logger.error(f"  Error for job {job.id}: {e}")

    if not dry_run and updated > 0:
        await session.commit()

    return {
        "jobs_found": len(jobs),
        "jobs_updated": updated,
        "total_size_bytes": total_size,
        "errors": errors,
    }


async def backfill_dataset_sizes(session: AsyncSession, dry_run: bool = True) -> dict:
    """Backfill output_size_bytes for all datasets with output directories."""
    result = await session.execute(
        select(Dataset).where(
            Dataset.output_directory.isnot(None),
            Dataset.output_size_bytes.is_(None)
        )
    )
    datasets = result.scalars().all()

    updated = 0
    total_size = 0
    errors = []

    logger.info(f"Found {len(datasets)} datasets without output size")

    for dataset in datasets:
        try:
            output_dir = Path(dataset.output_directory)
            if output_dir.exists():
                size = get_directory_size(output_dir)
                total_size += size

                if not dry_run:
                    dataset.output_size_bytes = size
                    updated += 1

                logger.info(f"  Dataset {dataset.id}: {format_bytes(size)}")
            else:
                logger.warning(f"  Dataset {dataset.id}: Output directory not found: {output_dir}")
        except Exception as e:
            errors.append(f"Dataset {dataset.id}: {str(e)}")
            logger.error(f"  Error for dataset {dataset.id}: {e}")

    if not dry_run and updated > 0:
        await session.commit()

    return {
        "datasets_found": len(datasets),
        "datasets_updated": updated,
        "total_size_bytes": total_size,
        "errors": errors,
    }


async def main(dry_run: bool = True):
    """Run the backfill."""
    settings = get_settings()

    # Create async engine
    engine = create_async_engine(
        str(settings.database_url),
        echo=False,
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    mode = "DRY RUN" if dry_run else "APPLYING CHANGES"
    logger.info(f"=" * 60)
    logger.info(f"Storage Backfill - {mode}")
    logger.info(f"=" * 60)

    async with async_session() as session:
        # Backfill jobs
        logger.info("\n--- Jobs ---")
        job_result = await backfill_job_sizes(session, dry_run)

        # Backfill datasets
        logger.info("\n--- Datasets ---")
        dataset_result = await backfill_dataset_sizes(session, dry_run)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Jobs found:       {job_result['jobs_found']}")
    logger.info(f"Jobs updated:     {job_result['jobs_updated']}")
    logger.info(f"Jobs total size:  {format_bytes(job_result['total_size_bytes'])}")
    logger.info(f"Datasets found:   {dataset_result['datasets_found']}")
    logger.info(f"Datasets updated: {dataset_result['datasets_updated']}")
    logger.info(f"Datasets size:    {format_bytes(dataset_result['total_size_bytes'])}")

    total = job_result['total_size_bytes'] + dataset_result['total_size_bytes']
    logger.info(f"Total size:       {format_bytes(total)}")

    if job_result['errors'] or dataset_result['errors']:
        logger.info(f"\nErrors: {len(job_result['errors']) + len(dataset_result['errors'])}")
        for err in job_result['errors'] + dataset_result['errors']:
            logger.error(f"  {err}")

    if dry_run:
        logger.info("\n*** This was a DRY RUN. Run with --apply to make changes. ***")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill storage sizes for jobs and datasets")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes (default is dry run)"
    )
    args = parser.parse_args()

    asyncio.run(main(dry_run=not args.apply))
