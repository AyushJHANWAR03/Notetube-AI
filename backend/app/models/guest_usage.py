"""
GuestUsage model for tracking anonymous user video usage.
Allows 1 free video analysis before requiring sign-in.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class GuestUsage(Base):
    """
    Tracks guest (anonymous) user video usage.

    Each guest gets 1 free video analysis identified by:
    - guest_token: UUID stored in browser cookie
    - ip_hash: SHA-256 hash of IP address (backup identifier)
    """

    __tablename__ = "guest_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_token = Column(String(64), unique=True, nullable=False, index=True)
    ip_hash = Column(String(64), nullable=True, index=True)
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True
    )
    youtube_id = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", backref="guest_usages")

    def __repr__(self):
        return f"<GuestUsage token={self.guest_token[:8]}... video={self.youtube_id}>"
