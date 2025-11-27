"""
Authentication API routes for Google OAuth.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlencode

from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import Token, GoogleAuthRequest
from app.schemas.user import UserResponse, User
from app.services.auth_service import AuthService
from app.api.dependencies.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/google/login")
async def google_login():
    """
    Redirect to Google OAuth login page.

    Returns:
        Redirect response to Google OAuth
    """
    # Build Google OAuth URL - redirect to frontend callback
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/auth/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }

    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return RedirectResponse(url=google_auth_url, status_code=307)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle Google OAuth callback and create user session.

    Args:
        code: Authorization code from Google
        db: Database session

    Returns:
        JWT token and user information

    Raises:
        HTTPException: If authentication fails
    """
    try:
        auth_service = AuthService()
        redirect_uri = f"{settings.FRONTEND_URL}/auth/callback"

        # Complete OAuth flow and get JWT token
        result = await auth_service.authenticate_with_google(code, redirect_uri, db)

        return {
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "user": UserResponse.model_validate(result["user"])
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


# Create a separate router for user routes
user_router = APIRouter(prefix="/api", tags=["users"])


@user_router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        Current user information
    """
    return UserResponse.model_validate(current_user)
