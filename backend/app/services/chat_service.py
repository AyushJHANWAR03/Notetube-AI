"""
Chat Service for AI-powered conversations about video content.

Uses context from video notes (summary, chapters, topics) to answer questions.
Supports streaming responses via SSE.

TLDW-inspired features:
- Full transcript context for accurate answers
- Timestamp references in responses [MM:SS]
- Fallback suggested questions when AI fails

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


# Fallback suggested prompts when AI generation fails (inspired by TLDW)
FALLBACK_SUGGESTED_PROMPTS = [
    "What are the main takeaways from this video?",
    "Can you explain the key concepts discussed?",
    "What practical advice does this video offer?",
    "What examples or stories are shared?",
    "How can I apply these ideas?",
]


class ChatServiceError(Exception):
    """Custom exception for Chat service errors."""
    pass


class ChatService:
    """Service for chat functionality with video context.

    Uses OpenAI for streaming chat (low latency requirement).
    Uses Groq (with OpenAI fallback) for suggested prompts.
    """

    # Limits - increased for better context (like TLDW)
    MAX_CONTEXT_CHARS = 8000  # Increased from 2000 for more context
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

        # Add chapters with timestamps for TLDW-like referencing
        chapters = getattr(notes, 'chapters', None)
        if chapters and isinstance(chapters, list):
            chapter_lines = []
            for i, ch in enumerate(chapters[:15]):  # Max 15 chapters for more context
                title = ch.get('title', f'Chapter {i+1}')
                start_time = ch.get('start_time', 0)
                summary = ch.get('summary', '')

                # Format timestamp as [MM:SS] or [H:MM:SS]
                if start_time >= 3600:
                    timestamp = f"[{int(start_time // 3600)}:{int((start_time % 3600) // 60):02d}:{int(start_time % 60):02d}]"
                else:
                    timestamp = f"[{int(start_time // 60)}:{int(start_time % 60):02d}]"

                if summary:
                    # Truncate chapter summary
                    if len(summary) > 100:
                        summary = summary[:100] + "..."
                    chapter_lines.append(f"- {timestamp} {title}: {summary}")
                else:
                    chapter_lines.append(f"- {timestamp} {title}")
            if chapter_lines:
                parts.append("Chapters (with timestamps):\n" + "\n".join(chapter_lines))

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
            print(f"[ChatService] Raw response: {content[:200]}...")

            # Parse JSON response - handle various formats
            parsed_content = content

            # Handle markdown code blocks if present
            if parsed_content.startswith("```"):
                parts = parsed_content.split("```")
                if len(parts) >= 2:
                    parsed_content = parts[1]
                    if parsed_content.startswith("json"):
                        parsed_content = parsed_content[4:]
                    parsed_content = parsed_content.strip()

            prompts = json.loads(parsed_content)

            # Handle dict response like {"prompts": [...]} or {"questions": [...]}
            if isinstance(prompts, dict):
                # Try common keys
                for key in ['prompts', 'questions', 'suggested_prompts']:
                    if key in prompts and isinstance(prompts[key], list):
                        prompts = prompts[key]
                        break
                else:
                    # Get first list value from dict
                    for v in prompts.values():
                        if isinstance(v, list):
                            prompts = v
                            break

            # Ensure we have exactly 3 prompts
            if isinstance(prompts, list) and len(prompts) >= 3:
                return prompts[:3]
            elif isinstance(prompts, list):
                # Pad if less than 3
                while len(prompts) < 3:
                    prompts.append("What are the key takeaways from this video?")
                return prompts

            print(f"[ChatService] Unexpected response format: {type(prompts)}")
            return self._get_fallback_prompts()

        except Exception as e:
            print(f"[ChatService] Error generating suggested prompts: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_prompts()

    def _get_fallback_prompts(self, count: int = 3, exclude: List[str] = None) -> List[str]:
        """
        Get fallback suggested prompts when AI generation fails.

        Like TLDW, we have predefined high-quality prompts to fall back to.

        Args:
            count: Number of prompts to return
            exclude: List of prompts to exclude (already asked)

        Returns:
            List of fallback prompt strings
        """
        exclude_lower = set(p.lower() for p in (exclude or []))
        result = []

        for prompt in FALLBACK_SUGGESTED_PROMPTS:
            if prompt.lower() not in exclude_lower:
                result.append(prompt)
            if len(result) >= count:
                break

        return result
