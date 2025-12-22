"""
TranscriptEmbedding model for storing vector embeddings of transcript segments.
Used for semantic search in videos.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Float, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class TranscriptEmbedding(Base):
    """
    Stores embeddings for individual transcript segments.

    Each segment from a transcript gets its own embedding vector,
    allowing for semantic search within a video.
    """

    __tablename__ = "transcript_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    segment_index = Column(Integer, nullable=False)
    segment_text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # text-embedding-3-small uses 1536 dimensions
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transcript = relationship("Transcript", backref="embeddings")

    def __repr__(self):
        return f"<TranscriptEmbedding segment={self.segment_index} start={self.start_time}s>"
