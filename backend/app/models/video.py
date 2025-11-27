import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Video(Base):
    """Video model for storing processed YouTube videos."""

    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    youtube_video_id = Column(String(32), nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="PENDING", index=True)  # PENDING, PROCESSING, READY, FAILED
    failure_reason = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="videos")
    jobs = relationship("Job", back_populates="video", cascade="all, delete-orphan")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    notes = relationship("Notes", back_populates="video", uselist=False, cascade="all, delete-orphan")
    quiz_questions = relationship("QuizQuestion", back_populates="video", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="video", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="video", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video {self.youtube_video_id} - {self.status}>"
