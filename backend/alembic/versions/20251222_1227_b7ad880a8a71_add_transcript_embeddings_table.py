"""add_transcript_embeddings_table

Revision ID: b7ad880a8a71
Revises: fd8b75234069
Create Date: 2025-12-22 12:27:29.921329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'b7ad880a8a71'
down_revision: Union[str, None] = 'fd8b75234069'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create transcript_embeddings table
    op.create_table('transcript_embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('transcript_id', sa.UUID(), nullable=False),
        sa.Column('segment_index', sa.Integer(), nullable=False),
        sa.Column('segment_text', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['transcript_id'], ['transcripts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_transcript_embeddings_transcript_id'),
        'transcript_embeddings',
        ['transcript_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_transcript_embeddings_transcript_id'), table_name='transcript_embeddings')
    op.drop_table('transcript_embeddings')
    # Note: We don't drop the vector extension as other tables might use it
