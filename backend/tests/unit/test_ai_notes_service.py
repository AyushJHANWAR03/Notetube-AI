"""
Unit tests for AINotesService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.ai_notes_service import AINotesService, AINotesServiceError


class TestAINotesServiceNotes:
    """Test AI notes generation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sample_transcript = "In this tutorial, we'll learn about Python. First, we cover variables. Then we discuss functions. Finally, we explore classes and objects."
        self.sample_segments = [
            {"text": "In this tutorial, we'll learn about Python.", "start": 0.0, "duration": 3.0},
            {"text": "First, we cover variables.", "start": 3.0, "duration": 2.5},
            {"text": "Then we discuss functions.", "start": 5.5, "duration": 2.5},
            {"text": "Finally, we explore classes and objects.", "start": 8.0, "duration": 3.0}
        ]

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_notes_success(self, mock_openai_class):
        """Should generate formatted notes from transcript."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="# Python Tutorial\n\n## Variables\n- Variables store data\n\n## Functions\n- Functions are reusable code blocks"))
        ]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_notes(self.sample_transcript, video_title="Python Tutorial")

        assert "markdown_notes" in result
        assert "# Python Tutorial" in result["markdown_notes"]
        assert "## Variables" in result["markdown_notes"]
        assert "## Functions" in result["markdown_notes"]
        assert result["model_used"] == "gpt-4o-mini"
        assert "tokens_used" in result

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_notes_with_custom_model(self, mock_openai_class):
        """Should use custom model when specified."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="# Notes"))]
        mock_response.usage = MagicMock(total_tokens=150)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_notes(
            self.sample_transcript,
            video_title="Test",
            model="gpt-4"
        )

        assert result["model_used"] == "gpt-4"
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4"

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_notes_empty_transcript(self, mock_openai_class):
        """Should raise error for empty transcript."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        with pytest.raises(AINotesServiceError, match="Transcript cannot be empty"):
            service.generate_notes("")

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_notes_api_error(self, mock_openai_class):
        """Should handle OpenAI API errors gracefully."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(AINotesServiceError, match="Failed to generate notes"):
            service.generate_notes(self.sample_transcript)

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_notes_truncates_long_transcript(self, mock_openai_class):
        """Should truncate very long transcripts to fit token limit."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="# Notes"))]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        # Create very long transcript (simulating 2+ hour video)
        long_transcript = "This is a test. " * 50000  # ~100k words

        result = service.generate_notes(long_transcript)

        # Should successfully generate notes despite length
        assert "markdown_notes" in result
        assert result["was_truncated"] is True


class TestAINotesServiceChapters:
    """Test AI chapter generation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sample_transcript = "Welcome to the tutorial. First, we'll cover variables. Variables store data. Next, we discuss functions. Functions are reusable. Finally, we explore classes."
        self.sample_segments = [
            {"text": "Welcome to the tutorial.", "start": 0.0, "duration": 2.0},
            {"text": "First, we'll cover variables.", "start": 2.0, "duration": 2.5},
            {"text": "Variables store data.", "start": 4.5, "duration": 2.0},
            {"text": "Next, we discuss functions.", "start": 6.5, "duration": 2.5},
            {"text": "Functions are reusable.", "start": 9.0, "duration": 2.0},
            {"text": "Finally, we explore classes.", "start": 11.0, "duration": 2.5}
        ]

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_chapters_success(self, mock_openai_class):
        """Should generate chapters with timestamps from transcript."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='[{"title": "Introduction", "start_time": 0.0, "summary": "Welcome"}, {"title": "Variables", "start_time": 2.0, "summary": "Learn about variables"}, {"title": "Functions", "start_time": 6.5, "summary": "Understanding functions"}]'))
        ]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_chapters(self.sample_transcript, self.sample_segments)

        assert "chapters" in result
        assert len(result["chapters"]) == 3
        assert result["chapters"][0]["title"] == "Introduction"
        assert result["chapters"][0]["start_time"] == 0.0
        assert result["chapters"][1]["title"] == "Variables"
        assert result["chapters"][2]["title"] == "Functions"

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_chapters_calculates_end_times(self, mock_openai_class):
        """Should calculate end times for chapters."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='[{"title": "Intro", "start_time": 0.0, "summary": "Start"}, {"title": "Content", "start_time": 100.0, "summary": "Main content"}]'))
        ]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        video_duration = 200.0
        result = service.generate_chapters(
            self.sample_transcript,
            self.sample_segments,
            video_duration=video_duration
        )

        # First chapter should end where second chapter starts
        assert result["chapters"][0]["end_time"] == 100.0
        # Last chapter should end at video duration
        assert result["chapters"][1]["end_time"] == video_duration

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_chapters_empty_segments(self, mock_openai_class):
        """Should raise error for empty segments."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        with pytest.raises(AINotesServiceError, match="Segments cannot be empty"):
            service.generate_chapters(self.sample_transcript, [])

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_chapters_invalid_json_fallback(self, mock_openai_class):
        """Should handle invalid JSON response from AI."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        # Return invalid JSON
        mock_response.choices = [
            MagicMock(message=MagicMock(content='This is not valid JSON'))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(AINotesServiceError, match="Failed to parse chapters"):
            service.generate_chapters(self.sample_transcript, self.sample_segments)

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_chapters_limits_count(self, mock_openai_class):
        """Should limit chapters to reasonable count (8-15)."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        # AI tries to return 50 chapters
        chapters_json = [
            {"title": f"Chapter {i}", "start_time": float(i * 10), "summary": f"Content {i}"}
            for i in range(50)
        ]
        mock_response.choices = [
            MagicMock(message=MagicMock(content=str(chapters_json).replace("'", '"')))
        ]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_chapters(self.sample_transcript, self.sample_segments)

        # Should limit to max 15 chapters
        assert len(result["chapters"]) <= 15


class TestAINotesServiceStructuredNotes:
    """Test AI structured notes generation (summary, bullets, flashcards, etc.)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sample_transcript = "In this tutorial, we'll learn about Python. First, we cover variables. Then we discuss functions. Finally, we explore classes and objects."
        self.sample_segments = [
            {"text": "In this tutorial, we'll learn about Python.", "start": 0.0, "duration": 3.0},
            {"text": "First, we cover variables.", "start": 3.0, "duration": 2.5},
            {"text": "Then we discuss functions.", "start": 5.5, "duration": 2.5},
            {"text": "Finally, we explore classes and objects.", "start": 8.0, "duration": 3.0}
        ]
        self.valid_structured_response = {
            "summary": "This tutorial covers Python fundamentals including variables, functions, and classes.",
            "bullets": [
                "Variables store data in Python",
                "Functions are reusable code blocks",
                "Classes enable object-oriented programming"
            ],
            "key_timestamps": [
                {"label": "Introduction", "time": "00:00", "seconds": 0},
                {"label": "Variables", "time": "00:03", "seconds": 3},
                {"label": "Functions", "time": "00:05", "seconds": 5}
            ],
            "flashcards": [
                {"front": "What are variables?", "back": "Variables store data in Python"},
                {"front": "What are functions?", "back": "Reusable blocks of code"}
            ],
            "action_items": ["Practice creating variables", "Write simple functions"],
            "topics": ["python", "programming", "tutorial"],
            "difficulty_level": "beginner"
        }

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_success(self, mock_openai_class):
        """Should generate all structured note components."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        import json
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(self.valid_structured_response)))
        ]
        mock_response.usage = MagicMock(total_tokens=500)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_structured_notes(
            self.sample_transcript,
            self.sample_segments,
            video_title="Python Tutorial"
        )

        assert "summary" in result
        assert "bullets" in result
        assert "key_timestamps" in result
        assert "flashcards" in result
        assert "action_items" in result
        assert "topics" in result
        assert "difficulty_level" in result
        assert result["model_used"] == "gpt-4o-mini"
        assert result["tokens_used"] == 500

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_validates_fields(self, mock_openai_class):
        """Should validate and provide defaults for missing fields."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        # Partial response missing some fields
        partial_response = {
            "summary": "A summary",
            "bullets": ["Point 1"]
            # Missing: key_timestamps, flashcards, action_items, topics, difficulty_level
        }

        mock_response = MagicMock()
        import json
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(partial_response)))
        ]
        mock_response.usage = MagicMock(total_tokens=200)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_structured_notes(
            self.sample_transcript,
            self.sample_segments
        )

        # Should have defaults for missing fields
        assert result["summary"] == "A summary"
        assert result["bullets"] == ["Point 1"]
        assert result["key_timestamps"] == []
        assert result["flashcards"] == []
        assert result["action_items"] == []
        assert result["topics"] == []
        assert result["difficulty_level"] == "intermediate"  # Default

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_validates_difficulty_level(self, mock_openai_class):
        """Should validate difficulty_level to allowed values."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        invalid_difficulty_response = {
            "summary": "Test",
            "bullets": [],
            "difficulty_level": "super_hard"  # Invalid value
        }

        mock_response = MagicMock()
        import json
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(invalid_difficulty_response)))
        ]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_structured_notes(
            self.sample_transcript,
            self.sample_segments
        )

        # Should default to intermediate for invalid values
        assert result["difficulty_level"] == "intermediate"

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_empty_transcript(self, mock_openai_class):
        """Should raise error for empty transcript."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        with pytest.raises(AINotesServiceError, match="Transcript cannot be empty"):
            service.generate_structured_notes("", self.sample_segments)

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_invalid_json(self, mock_openai_class):
        """Should handle invalid JSON response."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This is not valid JSON"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(AINotesServiceError, match="Failed to parse structured notes"):
            service.generate_structured_notes(self.sample_transcript, self.sample_segments)

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_handles_markdown_wrapped_json(self, mock_openai_class):
        """Should handle JSON wrapped in markdown code blocks."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        import json
        wrapped_json = f"```json\n{json.dumps(self.valid_structured_response)}\n```"

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=wrapped_json))
        ]
        mock_response.usage = MagicMock(total_tokens=500)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_structured_notes(
            self.sample_transcript,
            self.sample_segments
        )

        assert result["summary"] == self.valid_structured_response["summary"]
        assert len(result["bullets"]) == 3

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_api_error(self, mock_openai_class):
        """Should handle OpenAI API errors gracefully."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(AINotesServiceError, match="Failed to generate structured notes"):
            service.generate_structured_notes(self.sample_transcript, self.sample_segments)

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_truncates_long_transcript(self, mock_openai_class):
        """Should truncate very long transcripts."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        import json
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(self.valid_structured_response)))
        ]
        mock_response.usage = MagicMock(total_tokens=500)
        mock_client.chat.completions.create.return_value = mock_response

        # Create very long transcript
        long_transcript = "This is a test. " * 50000

        result = service.generate_structured_notes(long_transcript, self.sample_segments)

        # Should still work with truncated transcript
        assert "summary" in result

    @patch('app.services.ai_notes_service.OpenAI')
    def test_generate_structured_notes_with_custom_model(self, mock_openai_class):
        """Should use custom model when specified."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        import json
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(self.valid_structured_response)))
        ]
        mock_response.usage = MagicMock(total_tokens=500)
        mock_client.chat.completions.create.return_value = mock_response

        result = service.generate_structured_notes(
            self.sample_transcript,
            self.sample_segments,
            model="gpt-4"
        )

        assert result["model_used"] == "gpt-4"
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4"


class TestAINotesServiceIntegration:
    """Test complete AI processing workflow."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sample_transcript = "This is a test transcript about Python programming."
        self.sample_segments = [
            {"text": "This is a test transcript about Python programming.", "start": 0.0, "duration": 5.0}
        ]

    @patch('app.services.ai_notes_service.OpenAI')
    def test_process_transcript_full_workflow(self, mock_openai_class):
        """Should generate both notes and chapters together."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        # Mock notes response
        notes_response = MagicMock()
        notes_response.choices = [MagicMock(message=MagicMock(content="# Complete Notes"))]
        notes_response.usage = MagicMock(total_tokens=100)

        # Mock chapters response
        chapters_response = MagicMock()
        chapters_response.choices = [
            MagicMock(message=MagicMock(content='[{"title": "Introduction", "start_time": 0.0, "summary": "Intro"}]'))
        ]
        chapters_response.usage = MagicMock(total_tokens=100)

        # Return different responses for each call
        mock_client.chat.completions.create.side_effect = [notes_response, chapters_response]

        # Generate both
        notes_result = service.generate_notes(self.sample_transcript)
        chapters_result = service.generate_chapters(self.sample_transcript, self.sample_segments)

        assert "markdown_notes" in notes_result
        assert "chapters" in chapters_result
        assert len(chapters_result["chapters"]) > 0

    @patch('app.services.ai_notes_service.OpenAI')
    def test_handles_rate_limiting(self, mock_openai_class):
        """Should handle OpenAI rate limiting errors."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        service = AINotesService(api_key="test-key-123")

        error = Exception("Rate limit exceeded")
        error.status_code = 429
        mock_client.chat.completions.create.side_effect = error

        with pytest.raises(AINotesServiceError, match="Failed to generate notes"):
            service.generate_notes("Test transcript")
