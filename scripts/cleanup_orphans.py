#!/usr/bin/env python3
"""
Cleanup script to identify and remove orphaned job output directories.

Orphaned directories are those that exist on disk but have no corresponding
job record in the database (likely from jobs that were deleted without
cleaning up the filesystem).

Usage:
    python scripts/cleanup_orphans.py          # List orphans (dry run)
    python scripts/cleanup_orphans.py --delete # Actually delete orphans
"""

import argparse
import shutil
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text


def get_database_url() -> str:
    """Get database URL from environment or .env file."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "svo2_analyzer")
    password = os.getenv("POSTGRES_PASSWORD", "svo2_analyzer_dev")
    db = os.getenv("POSTGRES_DB", "svo2_analyzer")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_output_directory() -> Path:
    """Get output directory from environment or .env file."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    data_root = Path(os.getenv("DATA_ROOT", "/home/atlas/dev/pipe1/data"))
    return Path(os.getenv("OUTPUT_DIRECTORY", data_root / "output"))


def get_job_ids_from_database() -> set[str]:
    """Query database for all existing job IDs."""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM processing_jobs"))
        return {str(row[0]) for row in result}


def get_directories_on_disk(output_dir: Path) -> dict[str, int]:
    """
    Get all job directories on disk with their sizes.

    Returns:
        Dict mapping directory name (UUID) to size in bytes
    """
    directories = {}

    if not output_dir.exists():
        return directories

    for item in output_dir.iterdir():
        if item.is_dir():
            # Validate it looks like a UUID
            try:
                UUID(item.name)
                # Calculate directory size
                size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                directories[item.name] = size
            except ValueError:
                # Not a UUID, skip
                continue

    return directories


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def find_orphans(output_dir: Path) -> list[tuple[str, int]]:
    """
    Find orphaned directories (exist on disk but not in database).

    Returns:
        List of (directory_name, size_bytes) tuples
    """
    db_job_ids = get_job_ids_from_database()
    disk_dirs = get_directories_on_disk(output_dir)

    orphans = []
    for dir_name, size in disk_dirs.items():
        if dir_name not in db_job_ids:
            orphans.append((dir_name, size))

    # Sort by size descending
    orphans.sort(key=lambda x: x[1], reverse=True)
    return orphans


def main():
    parser = argparse.ArgumentParser(
        description="Find and optionally delete orphaned job output directories"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete orphaned directories (default is dry run)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override output directory path"
    )
    args = parser.parse_args()

    output_dir = args.output_dir or get_output_directory()

    print(f"Output directory: {output_dir}")
    print(f"Mode: {'DELETE' if args.delete else 'DRY RUN'}")
    print()

    # Get database job IDs
    print("Querying database for existing jobs...")
    db_job_ids = get_job_ids_from_database()
    print(f"Found {len(db_job_ids)} jobs in database")

    # Get disk directories
    print("Scanning output directory...")
    disk_dirs = get_directories_on_disk(output_dir)
    print(f"Found {len(disk_dirs)} directories on disk")
    print()

    # Find orphans
    orphans = find_orphans(output_dir)

    if not orphans:
        print("No orphaned directories found.")
        return 0

    total_size = sum(size for _, size in orphans)

    print(f"Found {len(orphans)} orphaned directories ({format_size(total_size)} total):")
    print("-" * 70)

    for dir_name, size in orphans:
        print(f"  {dir_name}  ({format_size(size)})")

    print("-" * 70)
    print(f"Total: {format_size(total_size)}")
    print()

    if args.delete:
        print("Deleting orphaned directories...")
        deleted_count = 0
        deleted_size = 0

        for dir_name, size in orphans:
            dir_path = output_dir / dir_name
            try:
                shutil.rmtree(dir_path)
                deleted_count += 1
                deleted_size += size
                print(f"  Deleted: {dir_name}")
            except Exception as e:
                print(f"  ERROR deleting {dir_name}: {e}")

        print()
        print(f"Deleted {deleted_count} directories, freed {format_size(deleted_size)}")
    else:
        print("Run with --delete to remove these directories.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
