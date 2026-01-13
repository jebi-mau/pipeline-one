"""Add training dataset and frame diversity models

Revision ID: 3c4d5e6f7g8h
Revises: 2b3c4d5e6f7g
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3c4d5e6f7g8h'
down_revision: Union[str, None] = '2b3c4d5e6f7g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # TRAINING_DATASETS TABLE
    # ==========================================================================
    op.create_table(
        'training_datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'source_job_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('processing_jobs.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'source_dataset_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('datasets.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'filter_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column('format', sa.String(20), nullable=False, server_default='both'),
        sa.Column('train_ratio', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('val_ratio', sa.Float(), nullable=False, server_default='0.2'),
        sa.Column('test_ratio', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('shuffle_seed', sa.Integer(), nullable=True),
        sa.Column('total_frames', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_annotations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('train_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('val_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('test_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_directory', sa.Text(), nullable=True),
        sa.Column('kitti_path', sa.Text(), nullable=True),
        sa.Column('coco_path', sa.Text(), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', index=True),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ==========================================================================
    # TRAINING_DATASET_FRAMES TABLE
    # ==========================================================================
    op.create_table(
        'training_dataset_frames',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'training_dataset_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('training_datasets.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('source_frame_id', sa.String(100), nullable=False),
        sa.Column('source_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('split', sa.String(10), nullable=False, index=True),
        sa.Column('output_index', sa.Integer(), nullable=False),
        sa.Column('annotation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'included_annotation_ids',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
    )

    # ==========================================================================
    # FRAME_DIVERSITY_CACHE TABLE
    # ==========================================================================
    op.create_table(
        'frame_diversity_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'job_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('processing_jobs.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),
        sa.Column('camera', sa.String(10), nullable=False, server_default='left'),
        sa.Column(
            'perceptual_hashes',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column(
            'motion_scores',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('analyzed_frames', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_frames', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_frame_diversity_cache_job_id', 'frame_diversity_cache', ['job_id'])


def downgrade() -> None:
    op.drop_index('ix_frame_diversity_cache_job_id', 'frame_diversity_cache')
    op.drop_table('frame_diversity_cache')
    op.drop_table('training_dataset_frames')
    op.drop_table('training_datasets')
