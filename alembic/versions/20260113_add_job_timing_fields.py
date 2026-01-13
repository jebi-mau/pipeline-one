"""Add job timing fields for ETA calculation.

Revision ID: add_job_timing_fields
Revises:
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_job_timing_fields'
down_revision: Union[str, None] = '3c4d5e6f7g8h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add stage_started_at column for tracking when current stage began
    op.add_column(
        'processing_jobs',
        sa.Column('stage_started_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add frames_per_second column for processing rate tracking
    op.add_column(
        'processing_jobs',
        sa.Column('frames_per_second', sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('processing_jobs', 'frames_per_second')
    op.drop_column('processing_jobs', 'stage_started_at')
