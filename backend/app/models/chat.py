"""
Chat model for storing chat messages with AI about videos.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatMessage(Base):
    """Model for storing chat messages between user and AI about a video."""

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    message_type = Column(String(20), nullable=False, default="chat")  # "chat", "teach_back", "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="chat_messages")
    user = relationship("User", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage {self.id} - {self.role}>"
