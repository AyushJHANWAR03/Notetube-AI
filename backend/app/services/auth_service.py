"""
Authentication service for Google OAuth and JWT token management.
"""
from typing import Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import GoogleUserInfo
from app.schemas.user import User, UserCreate
from app.services.user_service import UserService


class AuthService:
    """Service for authentication operations."""

    def __init__(self):
        self.user_service = UserService()

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from Google OAuth
            redirect_uri: Redirect URI used in OAuth flow

        Returns:
            Token response from Google

        Raises:
            Exception: If token exchange fails
        """
        token_url = "https://oauth2.googleapis.com/token"

        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Failed to exchange code for token: {error_data}")

            return response.json()

    async def get_google_user_info(self, access_token: str) -> GoogleUserInfo:
        """
        Get user information from Google.

        Args:
            access_token: Google OAuth access token

        Returns:
            Google user information

        Raises:
            Exception: If fetching user info fails
        """
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_url, headers=headers)

            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Failed to get user info: {error_data}")

            user_data = response.json()
            return GoogleUserInfo(**user_data)

    async def get_or_create_user(self, google_user: GoogleUserInfo, db: AsyncSession) -> User:
        """
        Get existing user or create new user from Google info.

        Args:
            google_user: Google user information
            db: Database session

        Returns:
            User object
        """
        # Try to find existing user by Google sub
        user = await self.user_service.get_user_by_google_sub(google_user.sub, db)

        if user:
            return user

        # Create new user
        user_data = UserCreate(
            email=google_user.email,
            name=google_user.name,
            avatar_url=google_user.picture,
            google_sub=google_user.sub
        )

        return await self.user_service.create_user(user_data, db)

    async def create_token_for_user(self, user: User) -> str:
        """
        Create JWT access token for user.

        Args:
            user: User object

        Returns:
            JWT access token string
        """
        token_data = {
            "user_id": str(user.id),
            "email": user.email
        }

        return create_access_token(token_data)

    async def authenticate_with_google(
        self,
        code: str,
        redirect_uri: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Complete Google OAuth flow and return JWT token.

        Args:
            code: Authorization code from Google
            redirect_uri: Redirect URI used in OAuth flow
            db: Database session

        Returns:
            Dictionary with access_token, token_type, and user
        """
        # Exchange code for Google access token
        token_response = await self.exchange_code_for_token(code, redirect_uri)
        google_access_token = token_response["access_token"]

        # Get user info from Google
        google_user = await self.get_google_user_info(google_access_token)

        # Get or create user in database
        user = await self.get_or_create_user(google_user, db)

        # Create JWT token
        jwt_token = await self.create_token_for_user(user)

        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": user
        }
