from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data stored in JWT token."""
    user_id: Optional[UUID] = None
    email: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    """Schema for Google OAuth authentication request."""
    code: str
    redirect_uri: str


class GoogleUserInfo(BaseModel):
    """Schema for Google user information."""
    sub: str  # Google subject ID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None  # Avatar URL
    email_verified: bool = False
