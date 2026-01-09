"""File management API routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from backend.app.config import get_settings
from backend.app.schemas.file import DirectoryContents, FileMetadata

router = APIRouter()
settings = get_settings()


@router.get("/browse", response_model=DirectoryContents)
async def browse_directory(
    path: Annotated[str, Query(description="Directory path to browse")] = "",
    include_metadata: Annotated[bool, Query(description="Include SVO2 file metadata")] = False,
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
    allowed_roots = [settings.svo2_directory, settings.data_root]
    if not any(
        browse_path == root or root in browse_path.parents
        for root in allowed_roots
        if root is not None
    ):
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

    for item in sorted(browse_path.iterdir()):
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
        elif item.suffix.lower() == ".svo2":
            file_info = {
                "name": item.name,
                "path": str(item),
                "size_bytes": item.stat().st_size,
                "modified_at": item.stat().st_mtime,
            }
            if include_metadata:
                # TODO: Extract SVO2 metadata using pyzed
                file_info["metadata"] = None
            files.append(file_info)

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
    allowed_roots = [settings.svo2_directory, settings.data_root]
    if not any(
        path == root or root in path.parents
        for root in allowed_roots
        if root is not None
    ):
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
