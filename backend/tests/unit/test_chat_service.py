"""
Unit tests for the Chat Service.

TDD: These tests are written before the implementation.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import AsyncGenerator


class TestChatService:
    """Tests for ChatService class."""

    def test_build_context_from_notes(self):
        """Test building context from notes (summary + chapters + topics)."""
        from app.services.chat_service import ChatService

        service = ChatService()

        # Mock notes object
        notes = Mock()
        notes.summary = "This video explains Python basics including variables and functions."
        notes.topics = ["Python", "programming", "beginners"]
        notes.chapters = [
            {"title": "Introduction", "start_time": 0, "summary": "Welcome to Python basics"},
            {"title": "Variables", "start_time": 120, "summary": "Understanding variables and data types"},
            {"title": "Functions", "start_time": 300, "summary": "Creating and using functions"}
        ]

        context = service.build_context(notes)

        # Context should include all three components
        assert "Python basics" in context
        assert "variables" in context.lower()
        assert "functions" in context.lower()
        assert "Python" in context
        assert "Introduction" in context

    def test_build_context_with_missing_data(self):
        """Test building context when some data is missing."""
        from app.services.chat_service import ChatService

        service = ChatService()

        # Mock notes with minimal data
        notes = Mock()
        notes.summary = "A short summary."
        notes.topics = None
        notes.chapters = None

        context = service.build_context(notes)

        # Should still work with just summary
        assert "short summary" in context
        assert len(context) > 0

    def test_generate_suggested_prompts(self):
        """Test generating 3 contextual suggested prompts."""
        from app.services.chat_service import ChatService

        service = ChatService()

        summary = "This video teaches Python programming for beginners."
        topics = ["Python", "programming", "beginner"]
        chapters = [
            {"title": "Variables", "summary": "Learn about Python variables"},
            {"title": "Functions", "summary": "Creating functions in Python"}
        ]

        # Mock the _client directly instead of the property
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='["What is Python?", "How do variables work?", "Can you explain functions?"]'))]
        mock_response.usage = Mock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        service._client = mock_client

        prompts = service.generate_suggested_prompts(summary, topics, chapters)

        assert isinstance(prompts, list)
        assert len(prompts) == 3
        assert all(isinstance(p, str) for p in prompts)

    def test_generate_suggested_prompts_handles_api_error(self):
        """Test that generate_suggested_prompts returns empty list on API error."""
        from app.services.chat_service import ChatService

        service = ChatService()

        # Mock the _client directly
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        service._client = mock_client

        prompts = service.generate_suggested_prompts("summary", ["topic"], [])

        # Should return empty list on error, not crash
        assert prompts == []


class TestChatServiceStreaming:
    """Tests for streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_response_yields_tokens(self):
        """Test that stream_response yields tokens correctly."""
        from app.services.chat_service import ChatService

        service = ChatService()

        message = "What is Python?"
        context = "Python is a programming language."
        history = []

        # Create mock streaming response
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock(delta=Mock(content="Python "))]

        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock(delta=Mock(content="is a "))]

        mock_chunk3 = Mock()
        mock_chunk3.choices = [Mock(delta=Mock(content="language."))]

        mock_stream = MagicMock()
        mock_stream.__iter__ = Mock(return_value=iter([mock_chunk1, mock_chunk2, mock_chunk3]))

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_stream
        service._client = mock_client

        # Collect streamed tokens
        tokens = []
        async for token in service.stream_response(message, context, history):
            tokens.append(token)

        assert len(tokens) == 3
        assert "".join(tokens) == "Python is a language."

    @pytest.mark.asyncio
    async def test_stream_response_includes_history(self):
        """Test that chat history is included in the API call."""
        from app.services.chat_service import ChatService

        service = ChatService()

        message = "Tell me more"
        context = "Python basics"
        history = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."}
        ]

        mock_stream = MagicMock()
        mock_chunk = Mock()
        mock_chunk.choices = [Mock(delta=Mock(content="More info"))]
        mock_stream.__iter__ = Mock(return_value=iter([mock_chunk]))

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_stream
        service._client = mock_client

        tokens = []
        async for token in service.stream_response(message, context, history):
            tokens.append(token)

        # Verify API was called with history
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get('messages', [])

        # Should have: system, context system, history (2), user = 5 messages
        assert len(messages) >= 4


class TestChatServiceContextLength:
    """Tests for context length management."""

    def test_context_stays_within_token_limit(self):
        """Test that built context stays within reasonable token limits."""
        from app.services.chat_service import ChatService

        service = ChatService()

        # Create notes with a lot of content
        notes = Mock()
        notes.summary = "A" * 5000  # Very long summary
        notes.topics = ["topic" + str(i) for i in range(50)]
        notes.chapters = [
            {"title": f"Chapter {i}", "summary": "S" * 200}
            for i in range(20)
        ]

        context = service.build_context(notes)

        # Context should be truncated to stay under ~2000 chars (~500 tokens)
        assert len(context) < 3000

    def test_history_truncation(self):
        """Test that history is truncated to last N messages."""
        from app.services.chat_service import ChatService

        service = ChatService()

        # Create long history
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(20)
        ]

        truncated = service._truncate_history(history, max_messages=10)

        # Should only keep last 10 messages
        assert len(truncated) == 10
        assert truncated[-1]["content"] == "Message 19"
