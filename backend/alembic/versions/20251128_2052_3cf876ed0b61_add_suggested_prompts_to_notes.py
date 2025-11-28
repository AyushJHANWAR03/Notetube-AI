"""add_suggested_prompts_to_notes

Revision ID: 3cf876ed0b61
Revises: f2ca9f0337cd
Create Date: 2025-11-28 20:52:57.431086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3cf876ed0b61'
down_revision: Union[str, None] = 'f2ca9f0337cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notes', sa.Column('suggested_prompts', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('notes', 'suggested_prompts')
