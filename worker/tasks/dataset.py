"""Dataset preparation tasks."""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from worker.celery_app import app
from worker.db import get_db_engine

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    name="worker.tasks.dataset.prepare_dataset_files",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(IOError, OSError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def prepare_dataset_files(self, dataset_id: str) -> dict:
    """
    Prepare (copy and rename) all files in a dataset.

    Args:
        dataset_id: Dataset UUID

    Returns:
        Result with statistics
    """
    from backend.app.models.dataset import Dataset, DatasetFile

    logger.info(f"Preparing dataset files: {dataset_id}")

    engine = get_db_engine()

    with engine.connect() as conn:
        # Get dataset
        result = conn.execute(
            select(Dataset).where(Dataset.id == UUID(dataset_id))
        )
        dataset_row = result.first()
        if dataset_row is None:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get dataset as dict-like object
        _dataset_name = dataset_row.name  # Reserved for future use
        output_directory = dataset_row.output_directory
        status = dataset_row.status

        if status not in ("scanned", "preparing", "ready"):
            raise ValueError(f"Dataset not ready for preparation. Status: {status}")

        # Get files to prepare
        files_result = conn.execute(
            select(DatasetFile)
            .where(DatasetFile.dataset_id == UUID(dataset_id))
            .where(DatasetFile.status == "discovered")
        )
        files = files_result.fetchall()

    total_files = len(files)
    prepared = 0
    failed = 0
    errors = []

    logger.info(f"Found {total_files} files to prepare")

    for idx, file_row in enumerate(files):
        file_id = file_row.id
        original_path = file_row.original_path
        original_filename = file_row.original_filename
        camera_id = file_row.camera_id or "unknown"

        try:
            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": idx + 1,
                    "total": total_files,
                    "file": original_filename,
                    "message": f"Copying {original_filename}",
                },
            )

            # Generate new filename
            timestamp = int(datetime.now(timezone.utc).timestamp())
            job_id_str = dataset_id[:8]
            new_filename = f"{job_id_str}_{timestamp}_{camera_id}_{original_filename}"

            # Create camera-specific subdirectory
            output_dir = Path(output_directory) / camera_id
            output_dir.mkdir(parents=True, exist_ok=True)

            dest_path = output_dir / new_filename

            # Copy file
            source = Path(original_path)
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")

            shutil.copy2(source, dest_path)

            # Update file record in database
            with engine.connect() as conn:
                conn.execute(
                    DatasetFile.__table__.update()
                    .where(DatasetFile.id == file_id)
                    .values(
                        renamed_path=str(dest_path),
                        renamed_filename=new_filename,
                        status="copied",
                        copied_at=datetime.now(timezone.utc),
                    )
                )
                conn.commit()

            prepared += 1
            logger.info(f"Copied {original_filename} -> {new_filename}")

        except Exception as e:
            failed += 1
            error_msg = f"Failed to copy {original_filename}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

            # Update file status to failed
            with engine.connect() as conn:
                conn.execute(
                    DatasetFile.__table__.update()
                    .where(DatasetFile.id == file_id)
                    .values(
                        status="failed",
                        error_message=str(e),
                    )
                )
                conn.commit()

    # Update dataset status
    final_status = "ready" if failed == 0 else "ready"  # Still ready even with some failures
    with engine.connect() as conn:
        conn.execute(
            Dataset.__table__.update()
            .where(Dataset.id == UUID(dataset_id))
            .values(
                status=final_status,
                prepared_files=prepared,
            )
        )
        conn.commit()

    result = {
        "dataset_id": dataset_id,
        "total_files": total_files,
        "prepared": prepared,
        "failed": failed,
        "errors": errors,
        "status": final_status,
    }

    logger.info(f"Dataset preparation complete: {prepared}/{total_files} files prepared")
    return result


@app.task(
    bind=True,
    name="worker.tasks.dataset.scan_dataset_folder",
    max_retries=3,
    default_retry_delay=60,
)
def scan_dataset_folder(
    self,
    dataset_id: str,
    recursive: bool = True,
    extract_metadata: bool = True,
) -> dict:
    """
    Scan a dataset's source folder for SVO2 files.

    This is an async version of the scan that runs as a background task
    for large folder scans.

    Args:
        dataset_id: Dataset UUID
        recursive: Whether to scan recursively
        extract_metadata: Whether to extract SVO2 metadata

    Returns:
        Scan result statistics
    """
    import hashlib

    from backend.app.models.dataset import Dataset, DatasetFile

    logger.info(f"Scanning dataset folder: {dataset_id}")

    engine = get_db_engine()

    with engine.connect() as conn:
        result = conn.execute(
            select(Dataset).where(Dataset.id == UUID(dataset_id))
        )
        dataset_row = result.first()
        if dataset_row is None:
            raise ValueError(f"Dataset {dataset_id} not found")

        source_folder = dataset_row.source_folder

        # Update status to scanning
        conn.execute(
            Dataset.__table__.update()
            .where(Dataset.id == UUID(dataset_id))
            .values(status="scanning")
        )
        conn.commit()

    source_path = Path(source_folder)
    if not source_path.exists():
        # Update status to failed
        with engine.connect() as conn:
            conn.execute(
                Dataset.__table__.update()
                .where(Dataset.id == UUID(dataset_id))
                .values(
                    status="failed",
                    error_message=f"Source folder not found: {source_folder}",
                )
            )
            conn.commit()
        raise ValueError(f"Source folder not found: {source_folder}")

    # Find SVO2 files
    pattern = "**/*.svo2" if recursive else "*.svo2"
    svo2_files = list(source_path.glob(pattern))

    total_found = len(svo2_files)
    added = 0
    skipped = 0
    total_size = 0
    errors = []

    for idx, svo2_path in enumerate(svo2_files):
        try:
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": idx + 1,
                    "total": total_found,
                    "file": svo2_path.name,
                    "message": f"Processing {svo2_path.name}",
                },
            )

            # Check for duplicates
            with engine.connect() as conn:
                existing = conn.execute(
                    select(DatasetFile)
                    .where(DatasetFile.dataset_id == UUID(dataset_id))
                    .where(DatasetFile.original_path == str(svo2_path))
                ).first()
                if existing:
                    skipped += 1
                    continue

            # Get file info
            file_stat = svo2_path.stat()
            file_size = file_stat.st_size
            total_size += file_size

            relative_path = str(svo2_path.relative_to(source_path))

            # Calculate file hash
            hasher = hashlib.sha256()
            with open(svo2_path, "rb") as f:
                hasher.update(f.read(65536))
            file_hash = hasher.hexdigest()[:16]

            # Extract metadata if requested
            camera_id = file_hash[:8]
            camera_model = None
            camera_serial = None
            frame_count = None
            fps = None
            res_width = None
            res_height = None
            metadata = None

            if extract_metadata:
                try:
                    from processing.svo2.reader import SVO2Reader

                    with SVO2Reader(svo2_path) as reader:
                        meta = reader.get_metadata()
                        camera_id = str(meta.get("serial_number", file_hash[:8]))
                        camera_model = meta.get("camera_model")
                        camera_serial = str(meta.get("serial_number", ""))
                        frame_count = meta.get("frame_count")
                        fps = meta.get("fps")
                        res = meta.get("resolution", {})
                        res_width = res.get("width")
                        res_height = res.get("height")
                        metadata = meta
                except ImportError:
                    logger.warning("ZED SDK not available - using basic metadata")
                except Exception as e:
                    logger.warning(f"Failed to extract metadata from {svo2_path}: {e}")

            # Insert file record
            with engine.connect() as conn:
                conn.execute(
                    DatasetFile.__table__.insert().values(
                        dataset_id=UUID(dataset_id),
                        original_path=str(svo2_path),
                        original_filename=svo2_path.name,
                        relative_path=relative_path,
                        camera_id=camera_id,
                        camera_model=camera_model,
                        camera_serial=camera_serial,
                        file_hash=file_hash,
                        file_size=file_size,
                        frame_count=frame_count,
                        fps=fps,
                        resolution_width=res_width,
                        resolution_height=res_height,
                        status="discovered",
                        discovered_at=datetime.now(timezone.utc),
                        metadata=metadata,
                    )
                )
                conn.commit()

            added += 1

        except Exception as e:
            error_msg = f"Error processing {svo2_path}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

    # Update dataset statistics
    with engine.connect() as conn:
        conn.execute(
            Dataset.__table__.update()
            .where(Dataset.id == UUID(dataset_id))
            .values(
                status="scanned",
                total_files=added,
                total_size_bytes=total_size,
            )
        )
        conn.commit()

    result = {
        "dataset_id": dataset_id,
        "files_found": total_found,
        "files_added": added,
        "duplicates_skipped": skipped,
        "total_size_bytes": total_size,
        "errors": errors,
    }

    logger.info(f"Scan complete: found {total_found}, added {added}, skipped {skipped}")
    return result
