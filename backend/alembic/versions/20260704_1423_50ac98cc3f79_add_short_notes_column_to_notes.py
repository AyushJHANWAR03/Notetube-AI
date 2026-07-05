"""add short_notes column to notes

Revision ID: 50ac98cc3f79
Revises: 9574feba1aed
Create Date: 2026-07-04 14:23:33.880139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50ac98cc3f79'
down_revision: Union[str, None] = '9574feba1aed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notes', sa.Column('short_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('notes', 'short_notes')
