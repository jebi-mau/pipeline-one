"""Data lineage event model for audit trail."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.dataset import Dataset, DatasetFile
    from backend.app.models.frame import Frame
    from backend.app.models.job import ProcessingJob


class DataLineageEvent(Base, UUIDMixin):
    """Audit trail for data lineage events.

    Tracks operations like extraction, annotation import, and export
    to maintain full data provenance.
    """

    __tablename__ = "data_lineage_events"

    # Event type: 'extraction', 'annotation_import', 'export', 'scan', 'prepare'
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Optional links to related entities
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    dataset: Mapped["Dataset | None"] = relationship()

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job: Mapped["ProcessingJob | None"] = relationship()

    dataset_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    dataset_file: Mapped["DatasetFile | None"] = relationship()

    frame_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("frames.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    frame: Mapped["Frame | None"] = relationship()

    # Flexible details as JSON
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
