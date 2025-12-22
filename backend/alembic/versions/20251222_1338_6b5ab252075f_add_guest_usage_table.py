"""add_guest_usage_table

Revision ID: 6b5ab252075f
Revises: b7ad880a8a71
Create Date: 2025-12-22 13:38:55.257361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6b5ab252075f'
down_revision: Union[str, None] = 'b7ad880a8a71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make videos.user_id nullable for guest users
    op.alter_column('videos', 'user_id',
                    existing_type=postgresql.UUID(),
                    nullable=True)

    # Create guest_usage table for tracking anonymous user video usage
    op.create_table(
        'guest_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guest_token', sa.String(64), nullable=False, unique=True),
        sa.Column('ip_hash', sa.String(64), nullable=True),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('videos.id', ondelete='SET NULL'), nullable=True),
        sa.Column('youtube_id', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for faster lookups
    op.create_index('ix_guest_usage_guest_token', 'guest_usage', ['guest_token'])
    op.create_index('ix_guest_usage_ip_hash', 'guest_usage', ['ip_hash'])


def downgrade() -> None:
    op.drop_index('ix_guest_usage_ip_hash', table_name='guest_usage')
    op.drop_index('ix_guest_usage_guest_token', table_name='guest_usage')
    op.drop_table('guest_usage')

    # Revert videos.user_id to non-nullable
    op.alter_column('videos', 'user_id',
                    existing_type=postgresql.UUID(),
                    nullable=False)
