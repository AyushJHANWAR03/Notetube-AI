"""
Sample test to verify pytest is working correctly.
"""
import pytest


def test_sample():
    """Basic test to verify pytest setup."""
    assert 1 + 1 == 2


def test_sample_fixture(sample_user_data):
    """Test using a fixture."""
    assert sample_user_data["email"] == "test@example.com"
    assert "google_sub" in sample_user_data
