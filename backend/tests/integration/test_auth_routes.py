"""
Integration tests for authentication API routes.
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from httpx import AsyncClient

from app.main import app
from app.schemas.user import User
from app.schemas.auth import GoogleUserInfo


@pytest.fixture
def mock_google_user_info():
    """Mock Google user info."""
    return GoogleUserInfo(
        sub="google_123456",
        email="test@example.com",
        name="Test User",
        picture="https://example.com/photo.jpg",
        email_verified=True
    )


@pytest.fixture
def mock_user():
    """Mock user from database."""
    return User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/photo.jpg",
        google_sub="google_123456",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00"
    )


class TestGoogleOAuthRoutes:
    """Tests for Google OAuth routes."""

    @pytest.mark.asyncio
    async def test_google_login_redirect(self):
        """Test that /auth/google/login redirects to Google OAuth."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/auth/google/login", follow_redirects=False)

            assert response.status_code in [302, 307]  # Redirect status codes
            assert "google" in response.headers["location"].lower()
            assert "oauth2" in response.headers["location"].lower()

    @pytest.mark.asyncio
    async def test_google_callback_success(self, mock_google_user_info, mock_user):
        """Test successful Google OAuth callback."""
        code = "test_auth_code"

        mock_token_response = {
            "access_token": "ya29.test_token",
            "token_type": "Bearer"
        }

        mock_auth_result = {
            "access_token": "jwt_token_here",
            "token_type": "bearer",
            "user": mock_user
        }

        with patch('app.api.routes.auth.AuthService') as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service.authenticate_with_google = AsyncMock(return_value=mock_auth_result)
            mock_auth_service_class.return_value = mock_auth_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/auth/google/callback?code={code}")

                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"
                assert "user" in data

    @pytest.mark.asyncio
    async def test_google_callback_missing_code(self):
        """Test Google OAuth callback without code parameter."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/auth/google/callback")

            assert response.status_code in [400, 422]  # Bad request or validation error

    @pytest.mark.asyncio
    async def test_google_callback_invalid_code(self):
        """Test Google OAuth callback with invalid code."""
        code = "invalid_code"

        with patch('app.api.routes.auth.AuthService') as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service.authenticate_with_google = AsyncMock(
                side_effect=Exception("Invalid authorization code")
            )
            mock_auth_service_class.return_value = mock_auth_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/auth/google/callback?code={code}")

                assert response.status_code in [400, 401, 500]


class TestProtectedRoutes:
    """Tests for protected routes requiring authentication."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_user):
        """Test getting current user with valid token."""
        token = "valid_jwt_token"

        with patch('app.api.dependencies.auth.verify_token') as mock_verify_token, \
             patch('app.api.dependencies.auth.UserService') as mock_user_service_class:

            # Mock token verification
            mock_verify_token.return_value = {
                "user_id": str(mock_user.id),
                "email": mock_user.email
            }

            # Mock user service
            mock_user_service = AsyncMock()
            mock_user_service.get_user_by_id = AsyncMock(return_value=mock_user)
            mock_user_service_class.return_value = mock_user_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/me",
                    headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["email"] == mock_user.email
                assert data["name"] == mock_user.name

    @pytest.mark.asyncio
    async def test_get_current_user_missing_token(self):
        """Test accessing protected route without token."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/me")

            assert response.status_code in [401, 403]  # Unauthorized or Forbidden

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test accessing protected route with invalid token."""
        token = "invalid_token"

        with patch('app.api.dependencies.auth.verify_token') as mock_verify_token:
            mock_verify_token.return_value = None  # Invalid token

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/me",
                    headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        """Test accessing protected route with expired token."""
        token = "expired_token"

        with patch('app.api.dependencies.auth.verify_token') as mock_verify_token:
            mock_verify_token.return_value = None  # Expired token returns None

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/me",
                    headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self):
        """Test accessing protected route when user doesn't exist."""
        token = "valid_jwt_token"
        user_id = str(uuid4())

        with patch('app.api.dependencies.auth.verify_token') as mock_verify_token, \
             patch('app.api.dependencies.auth.UserService') as mock_user_service_class:

            mock_verify_token.return_value = {
                "user_id": user_id,
                "email": "test@example.com"
            }

            mock_user_service = AsyncMock()
            mock_user_service.get_user_by_id = AsyncMock(return_value=None)
            mock_user_service_class.return_value = mock_user_service

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/me",
                    headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 404  # Not found
