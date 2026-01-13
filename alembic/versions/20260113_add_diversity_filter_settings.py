"""Add diversity filter settings to job_configs.

Revision ID: add_diversity_filter
Revises:
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_diversity_filter'
down_revision: Union[str, None] = 'add_job_timing_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add diversity filter settings to job_configs table
    op.add_column('job_configs', sa.Column('enable_diversity_filter', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('job_configs', sa.Column('diversity_similarity_threshold', sa.Float(), nullable=False, server_default='0.85'))
    op.add_column('job_configs', sa.Column('diversity_motion_threshold', sa.Float(), nullable=False, server_default='0.02'))


def downgrade() -> None:
    op.drop_column('job_configs', 'diversity_motion_threshold')
    op.drop_column('job_configs', 'diversity_similarity_threshold')
    op.drop_column('job_configs', 'enable_diversity_filter')
