"""
Pydantic schemas for video-related API endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# Request schemas
class VideoCreateRequest(BaseModel):
    """Request body for creating a new video."""
    url: str = Field(..., description="YouTube video URL")


# Response schemas
class VideoBase(BaseModel):
    """Base video schema."""
    id: UUID
    youtube_video_id: str
    original_url: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: str
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListItem(VideoBase):
    """Video item for list endpoints."""
    pass


class VideoListResponse(BaseModel):
    """Response for video list endpoint."""
    videos: List[VideoListItem]
    total: int


class ChapterSchema(BaseModel):
    """Schema for a video chapter."""
    title: str
    start_time: float
    end_time: float
    summary: Optional[str] = None


class KeyTimestampSchema(BaseModel):
    """Schema for a key timestamp."""
    label: str
    time: str
    seconds: int


class FlashcardSchema(BaseModel):
    """Schema for a flashcard."""
    front: str
    back: str


class NotesSchema(BaseModel):
    """Schema for AI-generated notes."""
    summary: str
    bullets: List[str]
    key_timestamps: List[KeyTimestampSchema]
    flashcards: List[FlashcardSchema]
    action_items: List[str]
    topics: List[str]
    difficulty_level: str
    markdown_notes: Optional[str] = None
    chapters: Optional[List[ChapterSchema]] = None

    model_config = {"from_attributes": True}


class TranscriptSegmentSchema(BaseModel):
    """Schema for a transcript segment."""
    text: str
    start: float
    duration: float


class TranscriptSchema(BaseModel):
    """Schema for transcript data."""
    language_code: str
    provider: str
    raw_text: str
    segments: List[TranscriptSegmentSchema]

    model_config = {"from_attributes": True}


class VideoDetailResponse(VideoBase):
    """Detailed video response with notes and transcript."""
    notes: Optional[NotesSchema] = None
    transcript: Optional[TranscriptSchema] = None
    processed_at: Optional[datetime] = None


class JobStatusSchema(BaseModel):
    """Schema for job status."""
    id: UUID
    type: str
    status: str
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VideoCreateResponse(BaseModel):
    """Response after creating a video."""
    video: VideoBase
    job_id: str
    message: str


class VideoStatusResponse(BaseModel):
    """Response for video status check."""
    video: VideoBase
    jobs: List[JobStatusSchema]


# Seek / "Take Me There" schemas
class SeekRequest(BaseModel):
    """Request body for seeking to a topic in video."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query (any language)")


class SeekResponse(BaseModel):
    """Response for seek request."""
    timestamp: Optional[float] = Field(None, description="Timestamp in seconds, null if not found")
    confidence: str = Field(..., description="Confidence level: high, medium, low, or none")
    matched_text: str = Field("", description="Relevant excerpt from transcript")
