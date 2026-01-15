"""Add curated dataset model

Revision ID: 4d5e6f7g8h9i
Revises: 3c4d5e6f7g8h
Create Date: 2026-01-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d5e6f7g8h9i"
down_revision: str | None = "3c4d5e6f7g8h"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create curated_datasets table
    op.create_table(
        "curated_datasets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("source_job_id", sa.UUID(), nullable=False),
        sa.Column("source_dataset_id", sa.UUID(), nullable=True),
        sa.Column("filter_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("original_frame_count", sa.Integer(), nullable=False, default=0),
        sa.Column("original_annotation_count", sa.Integer(), nullable=False, default=0),
        sa.Column("filtered_frame_count", sa.Integer(), nullable=False, default=0),
        sa.Column("filtered_annotation_count", sa.Integer(), nullable=False, default=0),
        sa.Column("excluded_frame_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("excluded_annotation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exclusion_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_job_id"],
            ["processing_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_dataset_id"],
            ["datasets.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_curated_datasets_name"),
        "curated_datasets",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_curated_datasets_source_job_id"),
        "curated_datasets",
        ["source_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_curated_datasets_source_dataset_id"),
        "curated_datasets",
        ["source_dataset_id"],
        unique=False,
    )

    # Add source_curated_dataset_id to training_datasets table
    op.add_column(
        "training_datasets",
        sa.Column("source_curated_dataset_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_training_datasets_curated_dataset",
        "training_datasets",
        "curated_datasets",
        ["source_curated_dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_training_datasets_source_curated_dataset_id"),
        "training_datasets",
        ["source_curated_dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    # Remove source_curated_dataset_id from training_datasets
    op.drop_index(
        op.f("ix_training_datasets_source_curated_dataset_id"),
        table_name="training_datasets",
    )
    op.drop_constraint(
        "fk_training_datasets_curated_dataset",
        "training_datasets",
        type_="foreignkey",
    )
    op.drop_column("training_datasets", "source_curated_dataset_id")

    # Drop curated_datasets table
    op.drop_index(op.f("ix_curated_datasets_source_dataset_id"), table_name="curated_datasets")
    op.drop_index(op.f("ix_curated_datasets_source_job_id"), table_name="curated_datasets")
    op.drop_index(op.f("ix_curated_datasets_name"), table_name="curated_datasets")
    op.drop_table("curated_datasets")
