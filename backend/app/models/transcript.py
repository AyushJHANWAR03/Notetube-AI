import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Transcript(Base):
    """Transcript model for storing video transcripts."""

    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    language_code = Column(String(16), nullable=False, default="en")
    provider = Column(String(32), nullable=False)  # youtube_auto, whisper
    raw_text = Column(Text, nullable=False)
    segments = Column(JSONB, nullable=False)  # [{ "text": "...", "start": 0.5, "duration": 3.2 }, ...]
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="transcript")

    def __repr__(self):
        return f"<Transcript {self.language_code} - {self.provider}>"
