"""Add storage size tracking fields

Revision ID: 6f7g8h9i0j1k
Revises: 5e6f7g8h9i0j
Create Date: 2026-01-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f7g8h9i0j1k"
down_revision: str | None = "5e6f7g8h9i0j"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add storage_size_bytes to processing_jobs table
    op.add_column(
        "processing_jobs",
        sa.Column("storage_size_bytes", sa.BigInteger(), nullable=True),
    )

    # Add output_size_bytes to datasets table
    op.add_column(
        "datasets",
        sa.Column("output_size_bytes", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("datasets", "output_size_bytes")
    op.drop_column("processing_jobs", "storage_size_bytes")
