"""
Unit tests for VideoProcessingService.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.video_processing_service import VideoProcessingService, VideoProcessingServiceError
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.notes import Notes
from app.models.job import Job


class TestVideoProcessingServiceVideo:
    """Test video CRUD operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = VideoProcessingService()
        self.user_id = uuid.uuid4()
        self.video_id = uuid.uuid4()
        self.youtube_video_id = "dQw4w9WgXcQ"
        self.original_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    @pytest.mark.asyncio
    async def test_create_video_success(self):
        """Should create a new video record."""
        mock_db = AsyncMock()

        # Mock the video object that gets created
        mock_video = MagicMock(spec=Video)
        mock_video.id = self.video_id
        mock_video.user_id = self.user_id
        mock_video.youtube_video_id = self.youtube_video_id
        mock_video.status = "PENDING"

        # Mock db.refresh to set the mock_video attributes
        async def mock_refresh(obj):
            obj.id = self.video_id

        mock_db.refresh = mock_refresh

        result = await self.service.create_video(
            user_id=self.user_id,
            youtube_video_id=self.youtube_video_id,
            original_url=self.original_url,
            db=mock_db,
            title="Test Video",
            thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            duration_seconds=212
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.status == "PENDING"

    @pytest.mark.asyncio
    async def test_get_video_by_id_found(self):
        """Should return video when found."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.id = self.video_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.get_video_by_id(self.video_id, mock_db)

        assert result == mock_video
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_video_by_id_not_found(self):
        """Should return None when video not found."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await self.service.get_video_by_id(self.video_id, mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_video_by_youtube_id(self):
        """Should find video by YouTube ID for a user."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.youtube_video_id = self.youtube_video_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.get_video_by_youtube_id(
            self.user_id,
            self.youtube_video_id,
            mock_db
        )

        assert result == mock_video

    @pytest.mark.asyncio
    async def test_get_user_videos(self):
        """Should return list of videos for a user."""
        mock_db = AsyncMock()

        mock_videos = [MagicMock(spec=Video) for _ in range(3)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_videos

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await self.service.get_user_videos(self.user_id, mock_db)

        assert len(result) == 3
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_video_status_to_processing(self):
        """Should update video status to PROCESSING."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.id = self.video_id
        mock_video.status = "PENDING"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.update_video_status(
            self.video_id,
            "PROCESSING",
            mock_db
        )

        assert result.status == "PROCESSING"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_video_status_to_failed(self):
        """Should update video status to FAILED with reason."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.id = self.video_id
        mock_video.status = "PROCESSING"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.update_video_status(
            self.video_id,
            "FAILED",
            mock_db,
            failure_reason="Transcript not available"
        )

        assert result.status == "FAILED"
        assert result.failure_reason == "Transcript not available"

    @pytest.mark.asyncio
    async def test_update_video_status_to_ready(self):
        """Should update video status to READY and set processed_at."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.id = self.video_id
        mock_video.status = "PROCESSING"
        mock_video.processed_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.update_video_status(
            self.video_id,
            "READY",
            mock_db
        )

        assert result.status == "READY"
        assert result.processed_at is not None

    @pytest.mark.asyncio
    async def test_update_video_metadata(self):
        """Should update video metadata."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.id = self.video_id
        mock_video.title = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.update_video_metadata(
            self.video_id,
            mock_db,
            title="Updated Title",
            duration_seconds=300
        )

        assert result.title == "Updated Title"
        assert result.duration_seconds == 300

    @pytest.mark.asyncio
    async def test_delete_video(self):
        """Should delete video and return True."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.id = self.video_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.delete_video(self.video_id, mock_db)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_video)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_video_not_found(self):
        """Should return False when video not found."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await self.service.delete_video(self.video_id, mock_db)

        assert result is False
        mock_db.delete.assert_not_called()


class TestVideoProcessingServiceJob:
    """Test job operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = VideoProcessingService()
        self.video_id = uuid.uuid4()
        self.job_id = uuid.uuid4()

    @pytest.mark.asyncio
    async def test_create_job_success(self):
        """Should create a new job."""
        mock_db = AsyncMock()

        async def mock_refresh(obj):
            obj.id = self.job_id

        mock_db.refresh = mock_refresh

        result = await self.service.create_job(
            self.video_id,
            "VIDEO_PROCESS",
            mock_db
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.status == "PENDING"
        assert result.progress == 0

    @pytest.mark.asyncio
    async def test_update_job_status_to_fetching(self):
        """Should update job status and set started_at."""
        mock_db = AsyncMock()
        mock_job = MagicMock(spec=Job)
        mock_job.id = self.job_id
        mock_job.status = "PENDING"
        mock_job.started_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_result

        result = await self.service.update_job_status(
            self.job_id,
            "FETCHING_TRANSCRIPT",
            mock_db,
            progress=25
        )

        assert result.status == "FETCHING_TRANSCRIPT"
        assert result.progress == 25
        assert result.started_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_to_completed(self):
        """Should update job status and set completed_at."""
        mock_db = AsyncMock()
        mock_job = MagicMock(spec=Job)
        mock_job.id = self.job_id
        mock_job.status = "GENERATING_NOTES"
        mock_job.completed_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_result

        result = await self.service.update_job_status(
            self.job_id,
            "COMPLETED",
            mock_db,
            progress=100
        )

        assert result.status == "COMPLETED"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_to_failed(self):
        """Should update job with error message."""
        mock_db = AsyncMock()
        mock_job = MagicMock(spec=Job)
        mock_job.id = self.job_id
        mock_job.status = "FETCHING_TRANSCRIPT"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_result

        result = await self.service.update_job_status(
            self.job_id,
            "FAILED",
            mock_db,
            error_message="Transcript not available"
        )

        assert result.status == "FAILED"
        assert result.error_message == "Transcript not available"

    @pytest.mark.asyncio
    async def test_get_job_by_id(self):
        """Should return job when found."""
        mock_db = AsyncMock()
        mock_job = MagicMock(spec=Job)
        mock_job.id = self.job_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_result

        result = await self.service.get_job_by_id(self.job_id, mock_db)

        assert result == mock_job


class TestVideoProcessingServiceTranscript:
    """Test transcript operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = VideoProcessingService()
        self.video_id = uuid.uuid4()
        self.sample_segments = [
            {"text": "Hello world", "start": 0.0, "duration": 2.0},
            {"text": "This is a test", "start": 2.0, "duration": 3.0}
        ]

    @pytest.mark.asyncio
    async def test_save_transcript_success(self):
        """Should save transcript."""
        mock_db = AsyncMock()

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()

        mock_db.refresh = mock_refresh

        result = await self.service.save_transcript(
            video_id=self.video_id,
            language_code="en",
            provider="youtube_auto",
            raw_text="Hello world This is a test",
            segments=self.sample_segments,
            db=mock_db
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.language_code == "en"
        assert result.provider == "youtube_auto"

    @pytest.mark.asyncio
    async def test_get_transcript_by_video_id(self):
        """Should return transcript for video."""
        mock_db = AsyncMock()
        mock_transcript = MagicMock(spec=Transcript)
        mock_transcript.video_id = self.video_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_transcript
        mock_db.execute.return_value = mock_result

        result = await self.service.get_transcript_by_video_id(self.video_id, mock_db)

        assert result == mock_transcript


class TestVideoProcessingServiceNotes:
    """Test notes operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = VideoProcessingService()
        self.video_id = uuid.uuid4()

    @pytest.mark.asyncio
    async def test_save_notes_success(self):
        """Should save all notes data."""
        mock_db = AsyncMock()

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()

        mock_db.refresh = mock_refresh

        result = await self.service.save_notes(
            video_id=self.video_id,
            db=mock_db,
            summary="This is a test summary",
            bullets=["Point 1", "Point 2"],
            key_timestamps=[{"label": "Intro", "time": "00:00", "seconds": 0}],
            flashcards=[{"front": "Q?", "back": "A"}],
            action_items=["Do this", "Do that"],
            topics=["python", "testing"],
            difficulty_level="beginner",
            markdown_notes="# Test Notes\n\nContent here",
            chapters=[{"title": "Intro", "start_time": 0, "end_time": 60, "summary": "Intro"}],
            notes_model="gpt-4o-mini",
            notes_tokens=1000,
            chapters_tokens=500,
            was_truncated=False
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.summary == "This is a test summary"
        assert result.difficulty_level == "beginner"
        assert result.was_truncated == "N"

    @pytest.mark.asyncio
    async def test_save_notes_with_truncation(self):
        """Should save notes with truncation flag."""
        mock_db = AsyncMock()

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()

        mock_db.refresh = mock_refresh

        result = await self.service.save_notes(
            video_id=self.video_id,
            db=mock_db,
            summary="Summary",
            bullets=[],
            key_timestamps=[],
            flashcards=[],
            action_items=[],
            topics=[],
            difficulty_level="advanced",
            markdown_notes="# Notes",
            chapters=[],
            notes_model="gpt-4o-mini",
            notes_tokens=5000,
            chapters_tokens=2000,
            was_truncated=True
        )

        assert result.was_truncated == "Y"

    @pytest.mark.asyncio
    async def test_get_notes_by_video_id(self):
        """Should return notes for video."""
        mock_db = AsyncMock()
        mock_notes = MagicMock(spec=Notes)
        mock_notes.video_id = self.video_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_notes
        mock_db.execute.return_value = mock_result

        result = await self.service.get_notes_by_video_id(self.video_id, mock_db)

        assert result == mock_notes


class TestVideoProcessingServiceDuplicateCheck:
    """Test duplicate video check."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = VideoProcessingService()
        self.user_id = uuid.uuid4()
        self.youtube_video_id = "dQw4w9WgXcQ"

    @pytest.mark.asyncio
    async def test_check_duplicate_found(self):
        """Should return existing video if duplicate."""
        mock_db = AsyncMock()
        mock_video = MagicMock(spec=Video)
        mock_video.youtube_video_id = self.youtube_video_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_video
        mock_db.execute.return_value = mock_result

        result = await self.service.check_duplicate_video(
            self.user_id,
            self.youtube_video_id,
            mock_db
        )

        assert result == mock_video

    @pytest.mark.asyncio
    async def test_check_duplicate_not_found(self):
        """Should return None if no duplicate."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await self.service.check_duplicate_video(
            self.user_id,
            self.youtube_video_id,
            mock_db
        )

        assert result is None
