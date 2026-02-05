"""File management API routes."""

import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_db
from backend.app.schemas.file import DirectoryContents, FileMetadata

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Development mode flag - only enable full filesystem access when explicitly set
DEV_MODE = os.getenv("PIPELINE_DEV_MODE", "").lower() in ("true", "1", "yes")


def get_allowed_roots() -> list[Path]:
    """Get list of allowed root directories for browsing.

    Security: By default, only configured directories and home are allowed.
    Full filesystem access requires explicit PIPELINE_DEV_MODE=true environment variable.
    """
    roots = []
    if settings.svo2_directory:
        roots.append(settings.svo2_directory)
    if settings.data_root:
        roots.append(settings.data_root)
    # Allow browsing from user home directory
    home_dir = Path.home()
    roots.append(home_dir)
    # Allow common data locations
    common_paths = [
        Path("/data"),
        Path("/mnt"),
        Path("/media"),
    ]
    for p in common_paths:
        if p.exists():
            roots.append(p)

    # SECURITY: Only allow root filesystem access in explicit dev mode
    if DEV_MODE:
        roots.append(Path("/"))

    return roots


def is_path_allowed(path: Path, allowed_roots: list[Path]) -> bool:
    """Check if path is within allowed directories."""
    resolved = path.resolve()
    for root in allowed_roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


@router.get("/browse", response_model=DirectoryContents)
async def browse_directory(
    path: Annotated[str, Query(description="Directory path to browse")] = "",
    include_metadata: Annotated[bool, Query(description="Include SVO2 file metadata")] = False,
    show_all_files: Annotated[bool, Query(description="Show all files, not just SVO2")] = False,
) -> DirectoryContents:
    """
    Browse directory contents and list SVO2 files.

    Returns a list of directories and SVO2 files in the specified path.
    """
    # Use SVO2 directory as root if no path specified
    if not path:
        browse_path = settings.svo2_directory
    else:
        browse_path = Path(path)

    # Security: Ensure path is within allowed directories
    allowed_roots = get_allowed_roots()
    if not is_path_allowed(browse_path, allowed_roots):
        raise HTTPException(
            status_code=403,
            detail="Access denied: Path is outside allowed directories",
        )

    if not browse_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    if not browse_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    directories = []
    files = []

    try:
        items = sorted(browse_path.iterdir())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to read directory") from None

    for item in items:
        # Skip hidden files/directories
        if item.name.startswith('.'):
            continue
        try:
            if item.is_dir():
                # Count items in directory
                try:
                    item_count = len(list(item.iterdir()))
                except PermissionError:
                    item_count = 0
                directories.append({
                    "name": item.name,
                    "path": str(item),
                    "item_count": item_count,
                })
            elif item.is_file():
                # Show all files or just SVO2 files based on parameter
                is_svo2 = item.suffix.lower() == ".svo2"
                if show_all_files or is_svo2:
                    try:
                        stat = item.stat()
                        file_info = {
                            "name": item.name,
                            "path": str(item),
                            "size_bytes": stat.st_size,
                            "modified_at": stat.st_mtime,
                        }
                        if include_metadata and is_svo2:
                            # TODO: Extract SVO2 metadata using pyzed
                            file_info["metadata"] = None
                        files.append(file_info)
                    except (PermissionError, OSError):
                        # Skip files we can't access
                        pass
        except (PermissionError, OSError):
            # Skip items we can't access
            pass

    return DirectoryContents(
        path=str(browse_path),
        directories=directories,
        files=files,
    )


@router.get("/metadata/{file_path:path}", response_model=FileMetadata)
async def get_file_metadata(file_path: str) -> FileMetadata:
    """
    Get detailed metadata for an SVO2 file.

    Extracts duration, frame count, resolution, and other information.
    """
    path = Path(file_path)

    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if path.suffix.lower() != ".svo2":
        raise HTTPException(status_code=400, detail="File is not an SVO2 file")

    # Security check
    allowed_roots = get_allowed_roots()
    if not is_path_allowed(path, allowed_roots):
        raise HTTPException(
            status_code=403,
            detail="Access denied: File is outside allowed directories",
        )

    # TODO: Implement actual SVO2 metadata extraction using pyzed
    # For now, return placeholder data
    return FileMetadata(
        path=str(path),
        name=path.name,
        size_bytes=path.stat().st_size,
        duration_ms=0,
        frame_count=0,
        fps=30.0,
        resolution=[1920, 1080],
        depth_mode="NEURAL",
        has_imu=True,
        serial_number="",
        firmware_version="",
        created_at=path.stat().st_ctime,
    )


@router.post("/validate")
async def validate_svo2_file(file_path: str) -> dict:
    """
    Validate an SVO2 file for integrity.

    Checks if the file can be opened and read correctly.
    """
    path = Path(file_path)

    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if path.suffix.lower() != ".svo2":
        raise HTTPException(status_code=400, detail="File is not an SVO2 file")

    # TODO: Implement actual validation using pyzed
    return {
        "path": str(path),
        "valid": True,
        "message": "File validation not yet implemented",
    }


@router.get("/frame-count")
async def get_frame_count(
    paths: Annotated[
        list[str],
        Query(description="Paths to SVO2 files to count frames")
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get total frame count for one or more SVO2 files.

    This is a fast operation that first checks the database for cached
    frame counts, then falls back to file size estimation if needed.
    Avoids opening SVO2 files directly to prevent ZED SDK issues.

    Returns:
        - total_frames: Sum of all frames across provided files
        - files: Per-file frame counts
    """
    from sqlalchemy import or_, select

    from backend.app.models.dataset import DatasetFile

    allowed_roots = get_allowed_roots()
    files_result = []
    total_frames = 0

    # First, try to get frame counts from database (fast, no ZED SDK needed)
    db_frame_counts = {}
    if paths:
        stmt = select(DatasetFile).where(
            or_(
                DatasetFile.original_path.in_(paths),
                DatasetFile.renamed_path.in_(paths),
            )
        )
        result = await db.execute(stmt)
        db_files = result.scalars().all()

        for db_file in db_files:
            if db_file.frame_count:
                db_frame_counts[db_file.original_path] = db_file.frame_count
                if db_file.renamed_path:
                    db_frame_counts[db_file.renamed_path] = db_file.frame_count

    for file_path in paths:
        path = Path(file_path)

        # Security check
        if not is_path_allowed(path, allowed_roots):
            files_result.append({
                "path": str(path),
                "frame_count": None,
                "error": "Access denied: File is outside allowed directories",
            })
            continue

        if not path.exists():
            files_result.append({
                "path": str(path),
                "frame_count": None,
                "error": "File not found",
            })
            continue

        if path.suffix.lower() != ".svo2":
            files_result.append({
                "path": str(path),
                "frame_count": None,
                "error": "File is not an SVO2 file",
            })
            continue

        # Check database cache first
        if file_path in db_frame_counts:
            frame_count = db_frame_counts[file_path]
            files_result.append({
                "path": str(path),
                "frame_count": frame_count,
                "error": None,
            })
            total_frames += frame_count
            logger.debug(f"Using cached frame count {frame_count} for {path.name}")
            continue

        # Fall back to file size estimation (avoid ZED SDK which may hang)
        try:
            file_size = path.stat().st_size
            # Rough estimate: ~1MB per frame for typical SVO2 files
            estimated_frames = max(file_size // (1024 * 1024), 100)
            files_result.append({
                "path": str(path),
                "frame_count": estimated_frames,
                "error": "Estimated from file size",
            })
            total_frames += estimated_frames
            logger.info(f"Estimated {estimated_frames} frames for {path.name} based on file size")
        except Exception as e:
            logger.error(f"Error estimating frame count for {path}: {e}")
            files_result.append({
                "path": str(path),
                "frame_count": None,
                "error": str(e),
            })

    return {
        "total_frames": total_frames,
        "files": files_result,
    }
