"""Add dataset and external annotation models

Revision ID: 9a4b3c2d1e0f
Revises: 8f3a2b1c4d5e
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a4b3c2d1e0f'
down_revision: Union[str, None] = '8f3a2b1c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create datasets table
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('customer', sa.String(255), nullable=True, index=True),
        sa.Column('site', sa.String(255), nullable=True, index=True),
        sa.Column('equipment', sa.String(255), nullable=True),
        sa.Column('collection_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('object_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('source_folder', sa.Text(), nullable=False),
        sa.Column('output_directory', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='created', index=True),
        sa.Column('total_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('prepared_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create dataset_files table
    op.create_table(
        'dataset_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('original_path', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('relative_path', sa.Text(), nullable=False),
        sa.Column('renamed_path', sa.Text(), nullable=True),
        sa.Column('renamed_filename', sa.String(512), nullable=True),
        sa.Column('camera_id', sa.String(100), nullable=True, index=True),
        sa.Column('camera_model', sa.String(100), nullable=True),
        sa.Column('camera_serial', sa.String(100), nullable=True),
        sa.Column('firmware_version', sa.String(50), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True, index=True),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('frame_count', sa.Integer(), nullable=True),
        sa.Column('recording_start_ns', sa.BigInteger(), nullable=True),
        sa.Column('recording_duration_ms', sa.Float(), nullable=True),
        sa.Column('resolution_width', sa.Integer(), nullable=True),
        sa.Column('resolution_height', sa.Integer(), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='discovered', index=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('copied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create annotation_imports table
    op.create_table(
        'annotation_imports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('source_tool', sa.String(50), nullable=False),
        sa.Column('source_format', sa.String(50), nullable=False),
        sa.Column('source_path', sa.Text(), nullable=False),
        sa.Column('source_filename', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', index=True),
        sa.Column('total_images', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('matched_frames', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unmatched_images', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_annotations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('import_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create external_annotations table
    op.create_table(
        'external_annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('import_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('annotation_imports.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('frame_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('frames.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('source_image_name', sa.String(512), nullable=False, index=True),
        sa.Column('label', sa.String(255), nullable=False, index=True),
        sa.Column('annotation_type', sa.String(50), nullable=False),
        sa.Column('bbox_x', sa.Float(), nullable=True),
        sa.Column('bbox_y', sa.Float(), nullable=True),
        sa.Column('bbox_width', sa.Float(), nullable=True),
        sa.Column('bbox_height', sa.Float(), nullable=True),
        sa.Column('points', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('occurrence_id', sa.Integer(), nullable=True),
        sa.Column('z_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_matched', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Add dataset_id column to processing_jobs table
    op.add_column(
        'processing_jobs',
        sa.Column(
            'dataset_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('datasets.id', ondelete='SET NULL'),
            nullable=True,
        )
    )
    op.create_index('ix_processing_jobs_dataset_id', 'processing_jobs', ['dataset_id'], if_not_exists=True)

    # Add dataset_file_id and numpy_path columns to frames table
    op.add_column(
        'frames',
        sa.Column(
            'dataset_file_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('dataset_files.id', ondelete='SET NULL'),
            nullable=True,
        )
    )
    op.create_index('ix_frames_dataset_file_id', 'frames', ['dataset_file_id'], if_not_exists=True)

    op.add_column(
        'frames',
        sa.Column('numpy_path', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # Remove columns from frames
    op.drop_index('ix_frames_dataset_file_id', 'frames')
    op.drop_column('frames', 'numpy_path')
    op.drop_column('frames', 'dataset_file_id')

    # Remove column from processing_jobs
    op.drop_index('ix_processing_jobs_dataset_id', 'processing_jobs')
    op.drop_column('processing_jobs', 'dataset_id')

    # Drop tables in reverse order
    op.drop_table('external_annotations')
    op.drop_table('annotation_imports')
    op.drop_table('dataset_files')
    op.drop_table('datasets')
