from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common attributes."""
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    google_sub: str


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class User(UserBase):
    """Complete user schema with all database fields."""
    id: UUID
    google_sub: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """User schema for API responses (excludes sensitive data)."""
    id: UUID
    email: EmailStr
    name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
