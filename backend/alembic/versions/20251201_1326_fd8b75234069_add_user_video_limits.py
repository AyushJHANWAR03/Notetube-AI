"""add_user_video_limits

Revision ID: fd8b75234069
Revises: 3cf876ed0b61
Create Date: 2025-12-01 13:26:02.998066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fd8b75234069'
down_revision: Union[str, None] = '3cf876ed0b61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add video limit fields to users table
    op.add_column('users', sa.Column('videos_analyzed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('video_limit', sa.Integer(), nullable=False, server_default='5'))


def downgrade() -> None:
    op.drop_column('users', 'video_limit')
    op.drop_column('users', 'videos_analyzed')
