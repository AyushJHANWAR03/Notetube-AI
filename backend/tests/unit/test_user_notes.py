"""
Unit tests for user notes API routes (TDD - written before implementation).
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def mock_current_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    return user


@pytest.fixture
def mock_video_with_notes():
    """Mock video object with notes."""
    video = MagicMock()
    video.id = uuid.uuid4()
    video.user_id = uuid.uuid4()
    video.youtube_video_id = "dQw4w9WgXcQ"
    video.status = "READY"

    # Mock notes object with user_notes
    notes = MagicMock()
    notes.id = uuid.uuid4()
    notes.video_id = video.id
    notes.user_notes = []
    video.notes = notes

    return video


@pytest.fixture
def sample_user_note():
    """Sample user note data."""
    return {
        "id": str(uuid.uuid4()),
        "text": "This is an important concept about caching",
        "timestamp": 45.5,
        "created_at": datetime.utcnow().isoformat(),
        "rewritten_text": None
    }


class TestUserNotesEndpoints:
    """Tests for user notes CRUD endpoints."""

    def test_save_user_note_requires_auth(self):
        """Should require authentication to save a note."""
        client = TestClient(app)
        video_id = str(uuid.uuid4())
        response = client.post(
            f"/api/videos/{video_id}/user-notes",
            json={"text": "Test note", "timestamp": 10.0}
        )
        assert response.status_code in [401, 403]

    def test_get_user_notes_requires_auth(self):
        """Should require authentication to get notes."""
        client = TestClient(app)
        video_id = str(uuid.uuid4())
        response = client.get(f"/api/videos/{video_id}/user-notes")
        assert response.status_code in [401, 403]

    def test_delete_user_note_requires_auth(self):
        """Should require authentication to delete a note."""
        client = TestClient(app)
        video_id = str(uuid.uuid4())
        note_id = str(uuid.uuid4())
        response = client.delete(f"/api/videos/{video_id}/user-notes/{note_id}")
        assert response.status_code in [401, 403]

    def test_rewrite_user_note_requires_auth(self):
        """Should require authentication to rewrite a note."""
        client = TestClient(app)
        video_id = str(uuid.uuid4())
        note_id = str(uuid.uuid4())
        response = client.post(
            f"/api/videos/{video_id}/user-notes/{note_id}/rewrite",
            json={"style": "simplify"}
        )
        assert response.status_code in [401, 403]


class TestSaveUserNote:
    """Test POST /api/videos/{video_id}/user-notes endpoint."""

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_save_user_note_success(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user,
        mock_video_with_notes
    ):
        """Should save a new user note and return it."""
        mock_get_user.return_value = mock_current_user
        mock_video_with_notes.user_id = mock_current_user.id

        saved_note = {
            "id": str(uuid.uuid4()),
            "text": "This is important",
            "timestamp": 45.5,
            "created_at": datetime.utcnow().isoformat(),
            "rewritten_text": None
        }

        mock_service = AsyncMock()
        mock_service.save_note.return_value = saved_note
        mock_service_class.return_value = mock_service

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.post(
                f"/api/videos/{mock_video_with_notes.id}/user-notes",
                json={"text": "This is important", "timestamp": 45.5},
                headers={"Authorization": "Bearer test-token"}
            )

        # This will fail until we implement the endpoint
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["text"] == "This is important"
        assert data["timestamp"] == 45.5

    @patch('app.api.dependencies.auth.get_current_user')
    def test_save_user_note_missing_text(self, mock_get_user, mock_current_user):
        """Should return 422 if text is missing."""
        mock_get_user.return_value = mock_current_user

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.post(
                f"/api/videos/{uuid.uuid4()}/user-notes",
                json={"timestamp": 45.5},  # Missing text
                headers={"Authorization": "Bearer test-token"}
            )

        assert response.status_code == 422


class TestGetUserNotes:
    """Test GET /api/videos/{video_id}/user-notes endpoint."""

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_get_user_notes_success(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user,
        mock_video_with_notes
    ):
        """Should return list of user notes."""
        mock_get_user.return_value = mock_current_user
        mock_video_with_notes.user_id = mock_current_user.id

        notes = [
            {
                "id": str(uuid.uuid4()),
                "text": "First note",
                "timestamp": 10.0,
                "created_at": datetime.utcnow().isoformat(),
                "rewritten_text": None
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Second note",
                "timestamp": 30.0,
                "created_at": datetime.utcnow().isoformat(),
                "rewritten_text": "AI rewritten version"
            }
        ]

        mock_service = AsyncMock()
        mock_service.get_notes.return_value = notes
        mock_service_class.return_value = mock_service

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.get(
                f"/api/videos/{mock_video_with_notes.id}/user-notes",
                headers={"Authorization": "Bearer test-token"}
            )

        # This will fail until we implement the endpoint
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_get_user_notes_empty(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user,
        mock_video_with_notes
    ):
        """Should return empty list if no notes."""
        mock_get_user.return_value = mock_current_user
        mock_video_with_notes.user_id = mock_current_user.id

        mock_service = AsyncMock()
        mock_service.get_notes.return_value = []
        mock_service_class.return_value = mock_service

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.get(
                f"/api/videos/{mock_video_with_notes.id}/user-notes",
                headers={"Authorization": "Bearer test-token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestDeleteUserNote:
    """Test DELETE /api/videos/{video_id}/user-notes/{note_id} endpoint."""

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_delete_user_note_success(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user,
        mock_video_with_notes
    ):
        """Should delete a user note and return 204."""
        mock_get_user.return_value = mock_current_user
        mock_video_with_notes.user_id = mock_current_user.id
        note_id = str(uuid.uuid4())

        mock_service = AsyncMock()
        mock_service.delete_note.return_value = True
        mock_service_class.return_value = mock_service

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.delete(
                f"/api/videos/{mock_video_with_notes.id}/user-notes/{note_id}",
                headers={"Authorization": "Bearer test-token"}
            )

        # This will fail until we implement the endpoint
        assert response.status_code == 204

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_delete_user_note_not_found(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user,
        mock_video_with_notes
    ):
        """Should return 404 if note doesn't exist."""
        mock_get_user.return_value = mock_current_user
        mock_video_with_notes.user_id = mock_current_user.id
        note_id = str(uuid.uuid4())

        mock_service = AsyncMock()
        mock_service.delete_note.return_value = False
        mock_service_class.return_value = mock_service

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.delete(
                f"/api/videos/{mock_video_with_notes.id}/user-notes/{note_id}",
                headers={"Authorization": "Bearer test-token"}
            )

        assert response.status_code == 404


class TestRewriteUserNote:
    """Test POST /api/videos/{video_id}/user-notes/{note_id}/rewrite endpoint."""

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_rewrite_note_success(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user,
        mock_video_with_notes
    ):
        """Should rewrite note with AI and return updated note."""
        mock_get_user.return_value = mock_current_user
        mock_video_with_notes.user_id = mock_current_user.id
        note_id = str(uuid.uuid4())

        rewritten_note = {
            "id": note_id,
            "text": "Original technical jargon about API caching strategies",
            "timestamp": 45.5,
            "created_at": datetime.utcnow().isoformat(),
            "rewritten_text": "A simple explanation about storing data to make apps faster"
        }

        mock_service = AsyncMock()
        mock_service.rewrite_note.return_value = rewritten_note
        mock_service_class.return_value = mock_service

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.post(
                f"/api/videos/{mock_video_with_notes.id}/user-notes/{note_id}/rewrite",
                json={"style": "simplify"},
                headers={"Authorization": "Bearer test-token"}
            )

        # This will fail until we implement the endpoint
        assert response.status_code == 200
        data = response.json()
        assert data["rewritten_text"] is not None

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_rewrite_note_invalid_style(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user
    ):
        """Should return 422 for invalid rewrite style."""
        mock_get_user.return_value = mock_current_user

        with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
            client = TestClient(app)
            response = client.post(
                f"/api/videos/{uuid.uuid4()}/user-notes/{uuid.uuid4()}/rewrite",
                json={"style": "invalid_style"},
                headers={"Authorization": "Bearer test-token"}
            )

        assert response.status_code == 422

    @patch('app.api.routes.user_notes.UserNotesService')
    @patch('app.api.dependencies.auth.get_current_user')
    def test_rewrite_all_styles(
        self,
        mock_get_user,
        mock_service_class,
        mock_current_user,
        mock_video_with_notes
    ):
        """Test all supported rewrite styles work."""
        mock_get_user.return_value = mock_current_user
        mock_video_with_notes.user_id = mock_current_user.id
        note_id = str(uuid.uuid4())

        # All supported styles
        styles = ["simplify", "summarize", "formal", "bullet_points", "explain"]

        for style in styles:
            rewritten_note = {
                "id": note_id,
                "text": "Original text",
                "timestamp": 45.5,
                "created_at": datetime.utcnow().isoformat(),
                "rewritten_text": f"Rewritten with {style}"
            }

            mock_service = AsyncMock()
            mock_service.rewrite_note.return_value = rewritten_note
            mock_service_class.return_value = mock_service

            with patch('app.api.dependencies.auth.get_current_user', return_value=mock_current_user):
                client = TestClient(app)
                response = client.post(
                    f"/api/videos/{mock_video_with_notes.id}/user-notes/{note_id}/rewrite",
                    json={"style": style},
                    headers={"Authorization": "Bearer test-token"}
                )

            assert response.status_code == 200, f"Style {style} should return 200"


class TestUserNotesSchemas:
    """Test user notes schema validation."""

    def test_user_note_create_schema(self):
        """Should validate UserNoteCreate schema."""
        from app.schemas.user_notes import UserNoteCreate

        note = UserNoteCreate(text="Test note", timestamp=45.5)
        assert note.text == "Test note"
        assert note.timestamp == 45.5

    def test_user_note_response_schema(self):
        """Should validate UserNoteResponse schema."""
        from app.schemas.user_notes import UserNoteResponse

        note = UserNoteResponse(
            id=str(uuid.uuid4()),
            text="Test note",
            timestamp=45.5,
            created_at=datetime.utcnow().isoformat(),
            rewritten_text=None
        )
        assert note.text == "Test note"
        assert note.rewritten_text is None

    def test_rewrite_request_schema(self):
        """Should validate RewriteRequest schema."""
        from app.schemas.user_notes import RewriteRequest

        request = RewriteRequest(style="simplify")
        assert request.style == "simplify"

    def test_rewrite_request_invalid_style(self):
        """Should reject invalid rewrite style."""
        from app.schemas.user_notes import RewriteRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RewriteRequest(style="invalid_style")
