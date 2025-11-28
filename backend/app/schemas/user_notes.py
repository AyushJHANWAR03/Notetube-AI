"""
Pydantic schemas for user notes.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


# Supported rewrite styles
REWRITE_STYLES = Literal["simplify", "summarize", "formal", "bullet_points", "explain"]


class UserNoteCreate(BaseModel):
    """Schema for creating a new user note."""
    text: str = Field(..., min_length=1, max_length=5000, description="The note text")
    timestamp: float = Field(..., ge=0, description="Video timestamp in seconds")


class UserNoteResponse(BaseModel):
    """Schema for user note response."""
    id: str
    text: str
    timestamp: float
    created_at: str
    rewritten_text: Optional[str] = None

    class Config:
        from_attributes = True


class RewriteRequest(BaseModel):
    """Schema for AI rewrite request."""
    style: REWRITE_STYLES = Field(..., description="Rewrite style: simplify, summarize, formal, bullet_points, explain")


class RewriteResponse(BaseModel):
    """Schema for AI rewrite response."""
    id: str
    text: str
    timestamp: float
    created_at: str
    rewritten_text: str

    class Config:
        from_attributes = True
