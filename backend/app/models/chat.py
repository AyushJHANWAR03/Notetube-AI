import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatMessage(Base):
    """Chat message model for storing chat interactions."""

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user, assistant
    message_type = Column(String(32), nullable=False, default="chat")  # chat, teach_back, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB, nullable=True)  # e.g., { "related_timestamp_seconds": 432 }
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_messages")
    video = relationship("Video", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage {self.role} - {self.message_type}>"
