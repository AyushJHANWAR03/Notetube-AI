"""
Pydantic schemas for Chat API.
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ChatMessageBase(BaseModel):
    """Base schema for chat messages."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatMessageCreate(BaseModel):
    """Schema for creating a chat message request."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's message")
    history: List[ChatMessageBase] = Field(default=[], description="Previous chat messages for context")


class ChatMessageResponse(BaseModel):
    """Schema for a chat message response."""
    id: UUID
    video_id: UUID
    user_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response."""
    messages: List[ChatMessageResponse]
    total: int


class SuggestedPromptsResponse(BaseModel):
    """Schema for suggested prompts response."""
    prompts: List[str] = Field(default=[], description="List of suggested prompts")
