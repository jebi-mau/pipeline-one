"""Merge curated dataset and diversity filter

Revision ID: bf9d894e327f
Revises: 4d5e6f7g8h9i, add_diversity_filter
Create Date: 2026-01-14 08:02:11.695148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf9d894e327f'
down_revision: Union[str, None] = ('4d5e6f7g8h9i', 'add_diversity_filter')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
