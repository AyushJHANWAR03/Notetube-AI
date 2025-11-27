import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Notes(Base):
    """Notes model for storing AI-generated notes."""

    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Original fields - structured notes for UI
    summary = Column(Text, nullable=False)
    bullets = Column(JSONB, nullable=False)  # ["...", "..."]
    key_timestamps = Column(JSONB, nullable=False)  # [{ "label": "...", "time": "00:01:23", "seconds": 83 }, ...]
    flashcards = Column(JSONB, nullable=False)  # [{ "front": "...", "back": "..." }, ...]
    action_items = Column(JSONB, nullable=False)  # ["...", "..."]
    difficulty_level = Column(String(16), nullable=True)  # beginner, intermediate, advanced
    topics = Column(JSONB, nullable=True)  # ["caching", "load_balancing"]

    # New fields - full markdown notes and chapters
    markdown_notes = Column(Text, nullable=True)  # Full markdown notes from AI
    chapters = Column(JSONB, nullable=True)  # [{ "title": "...", "start_time": 0.0, "end_time": 10.0, "summary": "..." }, ...]

    # AI metadata
    raw_llm_output = Column(JSONB, nullable=True)
    notes_model = Column(String(32), nullable=True)  # gpt-4o-mini, etc.
    notes_tokens = Column(Integer, nullable=True)
    chapters_tokens = Column(Integer, nullable=True)
    was_truncated = Column(String(1), nullable=True, default="N")  # Y/N - if transcript was truncated

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="notes")

    def __repr__(self):
        return f"<Notes for Video {self.video_id}>"
