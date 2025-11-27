"""
Unit tests for video processor worker.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch, AsyncMock
from concurrent.futures import Future

from app.workers.video_processor import (
    _generate_ai_content_parallel,
    process_video_task,
    enqueue_video_processing,
    get_job_status
)


class TestGenerateAIContentParallel:
    """Test parallel AI content generation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.transcript = "Test transcript content for AI processing."
        self.segments = [
            {"text": "Test transcript", "start": 0.0, "duration": 2.0},
            {"text": "content for AI", "start": 2.0, "duration": 2.0},
            {"text": "processing.", "start": 4.0, "duration": 2.0}
        ]
        self.video_title = "Test Video"
        self.video_duration = 300.0

    @pytest.mark.asyncio
    @patch('app.workers.video_processor.AINotesService')
    async def test_parallel_generation_success(self, mock_ai_service_class):
        """Should run all 3 AI tasks in parallel."""
        mock_service = MagicMock()
        mock_ai_service_class.return_value = mock_service

        # Mock responses
        mock_service.generate_notes.return_value = {
            "markdown_notes": "# Notes",
            "model_used": "gpt-4o-mini",
            "tokens_used": 1000,
            "was_truncated": False
        }
        mock_service.generate_chapters.return_value = {
            "chapters": [{"title": "Intro", "start_time": 0, "end_time": 60}],
            "model_used": "gpt-4o-mini",
            "tokens_used": 500
        }
        mock_service.generate_structured_notes.return_value = {
            "summary": "Test summary",
            "bullets": ["Point 1"],
            "key_timestamps": [],
            "flashcards": [],
            "action_items": [],
            "topics": ["test"],
            "difficulty_level": "beginner",
            "model_used": "gpt-4o-mini",
            "tokens_used": 800
        }

        results = await _generate_ai_content_parallel(
            self.transcript,
            self.segments,
            self.video_title,
            self.video_duration
        )

        assert "notes" in results
        assert "chapters" in results
        assert "structured" in results
        assert results["notes"]["markdown_notes"] == "# Notes"
        assert len(results["chapters"]["chapters"]) == 1
        assert results["structured"]["summary"] == "Test summary"

        # Verify all 3 methods were called
        mock_service.generate_notes.assert_called_once()
        mock_service.generate_chapters.assert_called_once()
        mock_service.generate_structured_notes.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.workers.video_processor.AINotesService')
    async def test_parallel_generation_handles_error(self, mock_ai_service_class):
        """Should raise error if any task fails."""
        mock_service = MagicMock()
        mock_ai_service_class.return_value = mock_service

        # One task fails
        mock_service.generate_notes.side_effect = Exception("AI API Error")
        mock_service.generate_chapters.return_value = {"chapters": [], "model_used": "test", "tokens_used": 0}
        mock_service.generate_structured_notes.return_value = {"summary": "", "bullets": [], "key_timestamps": [], "flashcards": [], "action_items": [], "topics": [], "difficulty_level": "beginner", "model_used": "test", "tokens_used": 0}

        from app.services.ai_notes_service import AINotesServiceError

        with pytest.raises(AINotesServiceError, match="Failed to generate notes"):
            await _generate_ai_content_parallel(
                self.transcript,
                self.segments,
                self.video_title,
                self.video_duration
            )


class TestEnqueueVideoProcessing:
    """Test video processing queue operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.video_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    @patch('app.workers.video_processor.video_queue')
    def test_enqueue_video_processing(self, mock_queue):
        """Should enqueue video for processing."""
        mock_job = MagicMock()
        mock_job.id = "test-job-123"
        mock_queue.enqueue.return_value = mock_job

        result = enqueue_video_processing(
            self.video_id,
            self.user_id,
            self.youtube_url
        )

        assert result == "test-job-123"
        mock_queue.enqueue.assert_called_once()

        # Verify arguments
        call_args = mock_queue.enqueue.call_args
        assert call_args[0][0] == process_video_task
        assert call_args[0][1] == str(self.video_id)
        assert call_args[0][2] == str(self.user_id)
        assert call_args[0][3] == self.youtube_url
        assert call_args[1]["job_timeout"] == 600


class TestGetJobStatus:
    """Test job status retrieval."""

    @patch('app.workers.video_processor.redis_conn')
    def test_get_job_status_found(self, mock_redis):
        """Should return job status when found."""
        from datetime import datetime

        with patch('rq.job.Job.fetch') as mock_fetch:
            mock_job = MagicMock()
            mock_job.get_status.return_value = "finished"
            mock_job.result = {"success": True}
            mock_job.enqueued_at = datetime(2024, 1, 1, 12, 0, 0)
            mock_job.started_at = datetime(2024, 1, 1, 12, 0, 1)
            mock_job.ended_at = datetime(2024, 1, 1, 12, 0, 30)
            mock_job.exc_info = None
            mock_fetch.return_value = mock_job

            result = get_job_status("test-job-123")

            assert result is not None
            assert result["status"] == "finished"
            assert result["result"] == {"success": True}

    @patch('app.workers.video_processor.redis_conn')
    def test_get_job_status_not_found(self, mock_redis):
        """Should return None when job not found."""
        with patch('rq.job.Job.fetch') as mock_fetch:
            mock_fetch.side_effect = Exception("Job not found")

            result = get_job_status("nonexistent-job")

            assert result is None


class TestProcessVideoTask:
    """Test the main video processing task."""

    def setup_method(self):
        """Setup test fixtures."""
        self.video_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    @patch('app.workers.video_processor._process_video_async')
    @patch('app.workers.video_processor.asyncio')
    def test_process_video_task_runs_async(self, mock_asyncio, mock_process_async):
        """Should run async processing in new event loop."""
        mock_loop = MagicMock()
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = {"success": True, "video_id": str(self.video_id)}

        result = process_video_task(
            str(self.video_id),
            str(self.user_id),
            self.youtube_url
        )

        mock_asyncio.new_event_loop.assert_called_once()
        mock_asyncio.set_event_loop.assert_called_once_with(mock_loop)
        mock_loop.close.assert_called_once()
        assert result["success"] is True
