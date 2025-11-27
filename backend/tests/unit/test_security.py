"""
Unit tests for security utilities (JWT and password hashing).
"""
import pytest
from datetime import timedelta
from uuid import uuid4

from app.core.security import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
)


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_access_token(self):
        """Test creating a JWT access token."""
        data = {"user_id": str(uuid4()), "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_uuid(self):
        """Test creating token with UUID (should convert to string)."""
        user_id = uuid4()
        data = {"user_id": user_id, "email": "test@example.com"}
        token = create_access_token(data)

        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == str(user_id)

    def test_create_access_token_with_custom_expiry(self):
        """Test creating token with custom expiration time."""
        data = {"user_id": str(uuid4())}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires_delta)

        assert token is not None
        payload = verify_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_verify_valid_token(self):
        """Test verifying a valid JWT token."""
        user_id = str(uuid4())
        email = "test@example.com"
        data = {"user_id": user_id, "email": email}

        token = create_access_token(data)
        payload = verify_token(token)

        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["email"] == email
        assert "exp" in payload

    def test_verify_invalid_token(self):
        """Test verifying an invalid JWT token."""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)

        assert payload is None

    def test_verify_expired_token(self):
        """Test verifying an expired JWT token."""
        data = {"user_id": str(uuid4())}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expires_delta)

        payload = verify_token(token)
        # Expired tokens should return None
        assert payload is None


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test hashing a password."""
        password = "supersecretpassword123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password  # Should be different from plain
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
