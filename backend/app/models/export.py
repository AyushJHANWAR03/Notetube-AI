import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Export(Base):
    """Export model for storing exported files."""

    __tablename__ = "exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    export_type = Column(String(32), nullable=False)  # PDF, MARKDOWN
    file_url = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="PENDING")  # PENDING, READY, FAILED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="exports")
    video = relationship("Video", back_populates="exports")

    def __repr__(self):
        return f"<Export {self.export_type} - {self.status}>"
