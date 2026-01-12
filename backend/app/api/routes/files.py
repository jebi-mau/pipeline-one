"""File management API routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from backend.app.config import get_settings
from backend.app.schemas.file import DirectoryContents, FileMetadata

router = APIRouter()
settings = get_settings()


def get_allowed_roots() -> list[Path]:
    """Get list of allowed root directories for browsing."""
    roots = []
    if settings.svo2_directory:
        roots.append(settings.svo2_directory)
    if settings.data_root:
        roots.append(settings.data_root)
    # Allow browsing from user home directory
    home_dir = Path.home()
    roots.append(home_dir)
    # Allow common data locations
    roots.append(Path("/"))  # Allow root for full filesystem access in dev mode
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
        raise HTTPException(status_code=403, detail="Permission denied to read directory")

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
