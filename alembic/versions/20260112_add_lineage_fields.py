"""Add lineage tracking and sensor data fields

Revision ID: 2b3c4d5e6f7g
Revises: 9a4b3c2d1e0f
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2b3c4d5e6f7g'
down_revision: Union[str, None] = '9a4b3c2d1e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # FRAMES TABLE - Add lineage tracking fields
    # ==========================================================================
    op.add_column(
        'frames',
        sa.Column('original_svo2_filename', sa.String(255), nullable=True)
    )
    op.add_column(
        'frames',
        sa.Column('original_unix_timestamp', sa.BigInteger(), nullable=True)
    )

    # ==========================================================================
    # DATASET_FILES TABLE - Add video container metadata
    # ==========================================================================
    op.add_column(
        'dataset_files',
        sa.Column('video_codec', sa.String(50), nullable=True)
    )
    op.add_column(
        'dataset_files',
        sa.Column('pixel_format', sa.String(50), nullable=True)
    )
    op.add_column(
        'dataset_files',
        sa.Column('compression_mode', sa.String(50), nullable=True)
    )
    op.add_column(
        'dataset_files',
        sa.Column('bitrate_kbps', sa.Integer(), nullable=True)
    )

    # ==========================================================================
    # FRAME_METADATA TABLE - Add full sensor suite
    # ==========================================================================
    # Magnetometer
    op.add_column(
        'frame_metadata',
        sa.Column('mag_x', sa.Float(), nullable=True)
    )
    op.add_column(
        'frame_metadata',
        sa.Column('mag_y', sa.Float(), nullable=True)
    )
    op.add_column(
        'frame_metadata',
        sa.Column('mag_z', sa.Float(), nullable=True)
    )
    # Barometer
    op.add_column(
        'frame_metadata',
        sa.Column('pressure_hpa', sa.Float(), nullable=True)
    )
    op.add_column(
        'frame_metadata',
        sa.Column('altitude_m', sa.Float(), nullable=True)
    )
    # Temperature
    op.add_column(
        'frame_metadata',
        sa.Column('imu_temperature_c', sa.Float(), nullable=True)
    )
    op.add_column(
        'frame_metadata',
        sa.Column('barometer_temperature_c', sa.Float(), nullable=True)
    )

    # ==========================================================================
    # EXTERNAL_ANNOTATIONS TABLE - Add traceability fields
    # ==========================================================================
    op.add_column(
        'external_annotations',
        sa.Column(
            'source_dataset_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('datasets.id', ondelete='SET NULL'),
            nullable=True,
        )
    )
    op.create_index(
        'ix_external_annotations_source_dataset_id',
        'external_annotations',
        ['source_dataset_id'],
        if_not_exists=True
    )
    op.add_column(
        'external_annotations',
        sa.Column('match_strategy', sa.String(50), nullable=True)
    )
    op.add_column(
        'external_annotations',
        sa.Column('source_frame_index', sa.Integer(), nullable=True)
    )

    # ==========================================================================
    # PROCESSING_JOBS TABLE - Add depth computation settings
    # ==========================================================================
    op.add_column(
        'processing_jobs',
        sa.Column('depth_mode', sa.String(50), nullable=True)
    )
    op.add_column(
        'processing_jobs',
        sa.Column('depth_range_min_m', sa.Float(), nullable=True)
    )
    op.add_column(
        'processing_jobs',
        sa.Column('depth_range_max_m', sa.Float(), nullable=True)
    )

    # ==========================================================================
    # DATA_LINEAGE_EVENTS TABLE - Audit trail
    # ==========================================================================
    op.create_table(
        'data_lineage_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column(
            'dataset_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('datasets.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'job_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('processing_jobs.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'dataset_file_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('dataset_files.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'frame_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('frames.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    # Drop data_lineage_events table
    op.drop_table('data_lineage_events')

    # Remove processing_jobs columns
    op.drop_column('processing_jobs', 'depth_range_max_m')
    op.drop_column('processing_jobs', 'depth_range_min_m')
    op.drop_column('processing_jobs', 'depth_mode')

    # Remove external_annotations columns
    op.drop_column('external_annotations', 'source_frame_index')
    op.drop_column('external_annotations', 'match_strategy')
    op.drop_index('ix_external_annotations_source_dataset_id', 'external_annotations')
    op.drop_column('external_annotations', 'source_dataset_id')

    # Remove frame_metadata columns
    op.drop_column('frame_metadata', 'barometer_temperature_c')
    op.drop_column('frame_metadata', 'imu_temperature_c')
    op.drop_column('frame_metadata', 'altitude_m')
    op.drop_column('frame_metadata', 'pressure_hpa')
    op.drop_column('frame_metadata', 'mag_z')
    op.drop_column('frame_metadata', 'mag_y')
    op.drop_column('frame_metadata', 'mag_x')

    # Remove dataset_files columns
    op.drop_column('dataset_files', 'bitrate_kbps')
    op.drop_column('dataset_files', 'compression_mode')
    op.drop_column('dataset_files', 'pixel_format')
    op.drop_column('dataset_files', 'video_codec')

    # Remove frames columns
    op.drop_column('frames', 'original_unix_timestamp')
    op.drop_column('frames', 'original_svo2_filename')
