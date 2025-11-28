"""
Seek Service for finding timestamps in video transcripts using LLM.
"""
from typing import Dict, Any, List, Optional
import json
from openai import OpenAI

from app.core.config import settings


class SeekServiceError(Exception):
    """Custom exception for Seek service errors."""
    pass


class SeekService:
    """Service for finding video timestamps using GPT-3.5-turbo semantic search."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Seek service with lazy client initialization."""
        if api_key is None:
            api_key = settings.OPENAI_API_KEY

        if not api_key:
            raise SeekServiceError("OPENAI_API_KEY environment variable not set")

        self._api_key = api_key
        self._client = None  # Lazy initialization to avoid fork issues

    @property
    def client(self) -> OpenAI:
        """Lazily initialize the OpenAI client to avoid fork() issues on macOS."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def find_timestamp(
        self,
        query: str,
        segments: List[Dict[str, Any]],
        video_duration: Optional[float] = None,
        model: str = "gpt-3.5-turbo"
    ) -> Dict[str, Any]:
        """
        Find the best matching timestamp for a user query.

        Args:
            query: User's search query (can be in any language)
            segments: List of transcript segments with {text, start, duration}
            video_duration: Total video duration in seconds (optional)
            model: OpenAI model to use (default: gpt-3.5-turbo for speed/cost)

        Returns:
            Dictionary containing:
                - timestamp: Seconds into video (or null if no match)
                - confidence: "high", "medium", "low", or "none"
                - matched_text: Relevant excerpt from transcript

        Raises:
            SeekServiceError: If timestamp finding fails
        """
        if not query or not query.strip():
            raise SeekServiceError("Query cannot be empty")

        if not segments:
            raise SeekServiceError("No transcript segments provided")

        # Prepare compact transcript with timestamp markers
        timestamped_transcript = self._prepare_transcript(segments)

        # Build prompt
        system_prompt = """You are a video timestamp finder. Given a transcript with timestamps and a user query, find the EXACT moment in the video where the queried topic is discussed.

IMPORTANT:
- The query may be in ANY language (Hindi, English, Spanish, etc.)
- The transcript may be in a DIFFERENT language than the query
- Understand the MEANING of the query, not just keywords
- Return the timestamp where the topic STARTS being discussed

Return ONLY valid JSON (no markdown, no explanation):
{
  "timestamp": <seconds as number or null>,
  "confidence": "high" | "medium" | "low" | "none",
  "matched_text": "<relevant excerpt from transcript, max 100 chars>"
}

Confidence levels:
- "high": exact topic match, clearly discussed
- "medium": related topic or partial match
- "low": tangentially related
- "none": topic not found in video (timestamp should be null)"""

        duration_info = f"\nVideo duration: {int(video_duration)} seconds" if video_duration else ""

        user_prompt = f"""Find where this topic is discussed in the video:

Query: {query}
{duration_info}

Transcript with timestamps (format: [Xs] text):
{timestamped_transcript}"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()

                result = json.loads(content)
            except json.JSONDecodeError as e:
                raise SeekServiceError(f"Failed to parse LLM response: {str(e)}")

            # Validate and normalize result
            validated_result = {
                "timestamp": result.get("timestamp"),
                "confidence": result.get("confidence", "none"),
                "matched_text": result.get("matched_text", "")[:150]  # Truncate if too long
            }

            # Ensure confidence is valid
            if validated_result["confidence"] not in ["high", "medium", "low", "none"]:
                validated_result["confidence"] = "low"

            # If no timestamp, ensure confidence is "none"
            if validated_result["timestamp"] is None:
                validated_result["confidence"] = "none"

            return validated_result

        except SeekServiceError:
            raise
        except Exception as e:
            raise SeekServiceError(f"Failed to find timestamp: {str(e)}")

    def _prepare_transcript(self, segments: List[Dict[str, Any]], max_chars: int = 12000) -> str:
        """
        Prepare a compact transcript with timestamp markers.

        Groups segments into ~30 second chunks to reduce tokens while
        maintaining timestamp accuracy.

        Args:
            segments: List of transcript segments
            max_chars: Maximum characters to include (default ~3000 tokens)

        Returns:
            Formatted transcript string with timestamp markers
        """
        chunks = []
        chunk_texts = []
        chunk_start = 0

        for seg in segments:
            text = seg.get('text', '').strip()
            start = seg.get('start', 0)

            if text:
                chunk_texts.append(text)

            # Create chunk every ~30 seconds
            if start - chunk_start >= 30 and chunk_texts:
                chunk_text = ' '.join(chunk_texts)
                chunks.append(f"[{int(chunk_start)}s] {chunk_text}")
                chunk_texts = []
                chunk_start = start

        # Don't forget the last chunk
        if chunk_texts:
            chunk_text = ' '.join(chunk_texts)
            chunks.append(f"[{int(chunk_start)}s] {chunk_text}")

        full_transcript = '\n'.join(chunks)

        # Truncate if too long
        if len(full_transcript) > max_chars:
            full_transcript = full_transcript[:max_chars] + "\n[...transcript truncated...]"

        return full_transcript
