import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Job(Base):
    """Job model for tracking background processing jobs."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(32), nullable=False)  # VIDEO_PROCESS, PDF_EXPORT
    status = Column(String(32), nullable=False, default="PENDING", index=True)  # PENDING, FETCHING_TRANSCRIPT, GENERATING_NOTES, COMPLETED, FAILED
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    video = relationship("Video", back_populates="jobs")

    def __repr__(self):
        return f"<Job {self.type} - {self.status}>"
