"""Add stages_to_run column to processing_jobs

Revision ID: 8f3a2b1c4d5e
Revises: 267e42c5aefa
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f3a2b1c4d5e'
down_revision: Union[str, None] = '267e42c5aefa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add stages_to_run column to processing_jobs table
    op.add_column(
        'processing_jobs',
        sa.Column(
            'stages_to_run',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='["extraction", "segmentation", "reconstruction", "tracking"]'
        )
    )


def downgrade() -> None:
    op.drop_column('processing_jobs', 'stages_to_run')
