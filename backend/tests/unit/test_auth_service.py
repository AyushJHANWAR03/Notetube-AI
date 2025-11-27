"""
Unit tests for authentication service.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.services.auth_service import AuthService
from app.schemas.auth import GoogleUserInfo
from app.schemas.user import User


@pytest.fixture
def auth_service():
    """Create an AuthService instance for testing."""
    return AuthService()


@pytest.fixture
def mock_google_user_info():
    """Mock Google user info response."""
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


class TestGoogleOAuthFlow:
    """Tests for Google OAuth authentication flow."""

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, auth_service):
        """Test successful exchange of authorization code for access token."""
        code = "test_auth_code"
        redirect_uri = "http://localhost:8000/auth/google/callback"

        mock_response = {
            "access_token": "ya29.test_access_token",
            "token_type": "Bearer",
            "expires_in": 3599,
            "refresh_token": "1//test_refresh_token",
            "scope": "openid email profile"
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=mock_response)
            )

            result = await auth_service.exchange_code_for_token(code, redirect_uri)

            assert result["access_token"] == "ya29.test_access_token"
            assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_failure(self, auth_service):
        """Test failed code exchange (invalid code)."""
        code = "invalid_code"
        redirect_uri = "http://localhost:8000/auth/google/callback"

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=400,
                json=Mock(return_value={"error": "invalid_grant"})
            )

            with pytest.raises(Exception) as exc_info:
                await auth_service.exchange_code_for_token(code, redirect_uri)

            assert "invalid_grant" in str(exc_info.value).lower() or "400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_google_user_info_success(self, auth_service, mock_google_user_info):
        """Test successful retrieval of Google user info."""
        access_token = "ya29.test_access_token"

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "sub": mock_google_user_info.sub,
                    "email": mock_google_user_info.email,
                    "name": mock_google_user_info.name,
                    "picture": mock_google_user_info.picture,
                    "email_verified": mock_google_user_info.email_verified
                })
            )

            result = await auth_service.get_google_user_info(access_token)

            assert result.sub == mock_google_user_info.sub
            assert result.email == mock_google_user_info.email
            assert result.name == mock_google_user_info.name

    @pytest.mark.asyncio
    async def test_get_google_user_info_failure(self, auth_service):
        """Test failed retrieval of Google user info (invalid token)."""
        access_token = "invalid_token"

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=401,
                json=Mock(return_value={"error": "invalid_token"})
            )

            with pytest.raises(Exception) as exc_info:
                await auth_service.get_google_user_info(access_token)

            assert "401" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()


class TestUserManagement:
    """Tests for user creation and retrieval."""

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, auth_service, mock_google_user_info, mock_user):
        """Test retrieving existing user by Google sub."""
        mock_db = AsyncMock()
        auth_service.user_service.get_user_by_google_sub = AsyncMock(return_value=mock_user)

        result = await auth_service.get_or_create_user(mock_google_user_info, mock_db)

        assert result.id == mock_user.id
        assert result.email == mock_user.email
        auth_service.user_service.get_user_by_google_sub.assert_called_once_with(mock_google_user_info.sub, mock_db)

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, auth_service, mock_google_user_info):
        """Test creating new user when not found."""
        new_user_id = uuid4()
        new_user = User(
            id=new_user_id,
            email=mock_google_user_info.email,
            name=mock_google_user_info.name,
            avatar_url=mock_google_user_info.picture,
            google_sub=mock_google_user_info.sub,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )

        mock_db = AsyncMock()
        auth_service.user_service.get_user_by_google_sub = AsyncMock(return_value=None)
        auth_service.user_service.create_user = AsyncMock(return_value=new_user)

        result = await auth_service.get_or_create_user(mock_google_user_info, mock_db)

        assert result.id == new_user_id
        assert result.email == mock_google_user_info.email
        auth_service.user_service.get_user_by_google_sub.assert_called_once_with(mock_google_user_info.sub, mock_db)
        auth_service.user_service.create_user.assert_called_once()


class TestTokenGeneration:
    """Tests for JWT token generation after authentication."""

    @pytest.mark.asyncio
    async def test_create_token_for_user(self, auth_service, mock_user):
        """Test creating JWT token for authenticated user."""
        token = await auth_service.create_token_for_user(mock_user)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_authenticate_with_google_full_flow(self, auth_service, mock_google_user_info):
        """Test complete Google OAuth flow from code to JWT token."""
        code = "test_auth_code"
        redirect_uri = "http://localhost:8000/auth/google/callback"

        mock_token_response = {
            "access_token": "ya29.test_access_token",
            "token_type": "Bearer"
        }

        new_user = User(
            id=uuid4(),
            email=mock_google_user_info.email,
            name=mock_google_user_info.name,
            avatar_url=mock_google_user_info.picture,
            google_sub=mock_google_user_info.sub,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )

        with patch.object(auth_service, 'exchange_code_for_token', return_value=mock_token_response), \
             patch.object(auth_service, 'get_google_user_info', return_value=mock_google_user_info), \
             patch.object(auth_service, 'get_or_create_user', return_value=new_user), \
             patch.object(auth_service, 'create_token_for_user', return_value="jwt_token_here"):

            result = await auth_service.authenticate_with_google(code, redirect_uri, Mock())

            assert result["access_token"] == "jwt_token_here"
            assert result["token_type"] == "bearer"
            assert result["user"] == new_user
