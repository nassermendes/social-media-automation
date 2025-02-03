"""Initial migration

Revision ID: initial
Create Date: 2024-02-03 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create enum types
    op.execute("CREATE TYPE post_status AS ENUM ('draft', 'queued', 'scheduled', 'uploading', 'completed', 'failed')")
    op.execute("CREATE TYPE platform_type AS ENUM ('youtube', 'instagram', 'tiktok')")
    
    # Create uploads table
    op.create_table(
        'uploads',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('video_path', sa.String(), nullable=True),
        sa.Column('analysis', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(), nullable=True),
        sa.Column('queue_position', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'queued', 'scheduled', 'uploading', 'completed', 'failed', name='post_status'), nullable=True),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create platform_statuses table
    op.create_table(
        'platform_statuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.String(), nullable=True),
        sa.Column('platform', sa.Enum('youtube', 'instagram', 'tiktok', name='platform_type'), nullable=True),
        sa.Column('account', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'queued', 'scheduled', 'uploading', 'completed', 'failed', name='post_status'), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['upload_id'], ['uploads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('platform_statuses')
    op.drop_table('uploads')
    op.execute('DROP TYPE platform_type')
    op.execute('DROP TYPE post_status')
