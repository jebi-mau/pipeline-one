"""Add job performance stats for ETA estimation

Revision ID: 5e6f7g8h9i0j
Revises: bf9d894e327f
Create Date: 2026-01-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e6f7g8h9i0j"
down_revision: str | None = "bf9d894e327f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add per-stage duration fields to processing_jobs table
    op.add_column(
        "processing_jobs",
        sa.Column("extraction_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("segmentation_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("reconstruction_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("tracking_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("extraction_fps", sa.Float(), nullable=True),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("segmentation_fps", sa.Float(), nullable=True),
    )

    # Create job_performance_benchmarks table
    op.create_table(
        "job_performance_benchmarks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("sam3_model_variant", sa.String(length=50), nullable=False),
        sa.Column("avg_extraction_fps", sa.Float(), nullable=True),
        sa.Column("avg_segmentation_fps", sa.Float(), nullable=True),
        sa.Column("avg_reconstruction_fps", sa.Float(), nullable=True),
        sa.Column("avg_tracking_fps", sa.Float(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sam3_model_variant"),
    )
    op.create_index(
        op.f("ix_job_performance_benchmarks_sam3_model_variant"),
        "job_performance_benchmarks",
        ["sam3_model_variant"],
        unique=True,
    )


def downgrade() -> None:
    # Drop job_performance_benchmarks table
    op.drop_index(
        op.f("ix_job_performance_benchmarks_sam3_model_variant"),
        table_name="job_performance_benchmarks",
    )
    op.drop_table("job_performance_benchmarks")

    # Remove per-stage duration fields from processing_jobs table
    op.drop_column("processing_jobs", "segmentation_fps")
    op.drop_column("processing_jobs", "extraction_fps")
    op.drop_column("processing_jobs", "tracking_duration_seconds")
    op.drop_column("processing_jobs", "reconstruction_duration_seconds")
    op.drop_column("processing_jobs", "segmentation_duration_seconds")
    op.drop_column("processing_jobs", "extraction_duration_seconds")
