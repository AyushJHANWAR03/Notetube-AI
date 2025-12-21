"""
Chat Service for AI-powered conversations about video content.

Uses context from video notes (summary, chapters, topics) to answer questions.
Supports streaming responses via SSE.

Note: Streaming chat uses OpenAI directly for low latency.
Suggested prompts use Groq (with OpenAI fallback) for speed.
"""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI

from app.core.config import settings
from app.core.constants import AIModels
from app.services.ai_provider import AIProvider
from app.prompts import (
    CHAT_SYSTEM_PROMPT,
    CHAT_USER_PROMPT_TEMPLATE,
    SUGGESTED_PROMPTS_SYSTEM_PROMPT,
    SUGGESTED_PROMPTS_USER_TEMPLATE,
)


class ChatServiceError(Exception):
    """Custom exception for Chat service errors."""
    pass


class ChatService:
    """Service for chat functionality with video context.

    Uses OpenAI for streaming chat (low latency requirement).
    Uses Groq (with OpenAI fallback) for suggested prompts.
    """

    # Limits
    MAX_CONTEXT_CHARS = 2000
    MAX_HISTORY_MESSAGES = 10

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Chat service with lazy client initialization."""
        if api_key is None:
            api_key = settings.OPENAI_API_KEY

        if not api_key:
            raise ChatServiceError("OPENAI_API_KEY environment variable not set")

        self._api_key = api_key
        self._client = None
        self._provider = None

    @property
    def client(self) -> OpenAI:
        """Lazily initialize the OpenAI client for streaming chat."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    @property
    def provider(self) -> AIProvider:
        """Lazily initialize the AI provider for non-streaming calls."""
        if self._provider is None:
            self._provider = AIProvider()
        return self._provider

    def build_context(self, notes) -> str:
        """
        Build context string from notes (summary + chapters + topics).

        Args:
            notes: Notes object with summary, chapters, topics fields

        Returns:
            Formatted context string for the AI
        """
        parts = []

        # Add summary
        summary = getattr(notes, 'summary', '') or ''
        if summary:
            # Truncate long summaries
            if len(summary) > 1000:
                summary = summary[:1000] + "..."
            parts.append(f"Summary: {summary}")

        # Add topics
        topics = getattr(notes, 'topics', None)
        if topics and isinstance(topics, list):
            topics_str = ", ".join(topics[:10])  # Max 10 topics
            parts.append(f"Main topics: {topics_str}")

        # Add chapters
        chapters = getattr(notes, 'chapters', None)
        if chapters and isinstance(chapters, list):
            chapter_lines = []
            for i, ch in enumerate(chapters[:10]):  # Max 10 chapters
                title = ch.get('title', f'Chapter {i+1}')
                summary = ch.get('summary', '')
                if summary:
                    # Truncate chapter summary
                    if len(summary) > 100:
                        summary = summary[:100] + "..."
                    chapter_lines.append(f"- {title}: {summary}")
                else:
                    chapter_lines.append(f"- {title}")
            if chapter_lines:
                parts.append("Chapters:\n" + "\n".join(chapter_lines))

        context = "\n\n".join(parts)

        # Final truncation to stay within limits
        if len(context) > self.MAX_CONTEXT_CHARS:
            context = context[:self.MAX_CONTEXT_CHARS] + "..."

        return context

    def _truncate_history(self, history: List[Dict[str, str]], max_messages: int = None) -> List[Dict[str, str]]:
        """
        Truncate chat history to keep only the most recent messages.

        Args:
            history: Full chat history
            max_messages: Maximum number of messages to keep

        Returns:
            Truncated history list
        """
        if max_messages is None:
            max_messages = self.MAX_HISTORY_MESSAGES

        if len(history) <= max_messages:
            return history

        return history[-max_messages:]

    async def stream_response(
        self,
        message: str,
        context: str,
        history: List[Dict[str, str]],
        model: str = AIModels.SEEK_MODEL  # Use gpt-3.5-turbo for chat
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response from OpenAI.

        Args:
            message: User's message
            context: Video context (summary + chapters + topics)
            history: Previous chat messages
            model: OpenAI model to use

        Yields:
            Tokens as they stream from OpenAI
        """
        # Build messages array
        messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT}
        ]

        # Add context as a system message
        if context:
            messages.append({
                "role": "system",
                "content": f"Video context:\n{context}"
            })

        # Add truncated history
        truncated_history = self._truncate_history(history)
        messages.extend(truncated_history)

        # Add current user message
        messages.append({"role": "user", "content": message})

        # Call OpenAI with streaming
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            stream=True
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate_suggested_prompts(
        self,
        summary: str,
        topics: List[str],
        chapters: List[Dict[str, Any]],
        model: str = AIModels.SEEK_MODEL
    ) -> List[str]:
        """
        Generate 3 suggested prompts based on video content.

        Uses Groq (with OpenAI fallback) for fast generation.

        Args:
            summary: Video summary
            topics: List of video topics
            chapters: List of chapter dictionaries

        Returns:
            List of 3 suggested prompt strings
        """
        try:
            # Format chapters for prompt
            chapters_text = ""
            if chapters:
                chapter_lines = []
                for ch in chapters[:5]:  # Use first 5 chapters
                    title = ch.get('title', '')
                    ch_summary = ch.get('summary', '')
                    if title:
                        chapter_lines.append(f"- {title}: {ch_summary[:100]}" if ch_summary else f"- {title}")
                chapters_text = "\n".join(chapter_lines)

            # Format topics
            topics_text = ", ".join(topics[:5]) if topics else "General content"

            user_prompt = SUGGESTED_PROMPTS_USER_TEMPLATE.format(
                summary=summary[:500] if summary else "No summary available",
                topics=topics_text,
                chapters=chapters_text or "No chapters available"
            )

            messages = [
                {"role": "system", "content": SUGGESTED_PROMPTS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            response = self.provider.generate(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=300,
                json_mode=True
            )

            content = response.content.strip()

            # Parse JSON response
            # Handle markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            prompts = json.loads(content)

            # Ensure we have exactly 3 prompts
            if isinstance(prompts, list) and len(prompts) >= 3:
                return prompts[:3]
            elif isinstance(prompts, list):
                # Pad if less than 3
                while len(prompts) < 3:
                    prompts.append("What are the key takeaways from this video?")
                return prompts

            return []

        except Exception as e:
            print(f"[ChatService] Error generating suggested prompts: {e}")
            return []
