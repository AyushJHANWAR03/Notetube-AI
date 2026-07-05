"""add tldr column to notes

Revision ID: 9574feba1aed
Revises: 6b5ab252075f
Create Date: 2026-07-04 13:39:14.497255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9574feba1aed'
down_revision: Union[str, None] = '6b5ab252075f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notes', sa.Column('tldr', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('notes', 'tldr')
