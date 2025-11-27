"""
AI Notes Service for generating notes and chapters from video transcripts.
"""
from typing import Dict, Any, List, Optional
import json
from openai import OpenAI

from app.core.config import settings


class AINotesServiceError(Exception):
    """Custom exception for AI Notes service errors."""
    pass


class AINotesService:
    """Service for generating AI-powered notes and chapters from transcripts."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI Notes service with lazy client initialization."""
        if api_key is None:
            api_key = settings.OPENAI_API_KEY

        if not api_key:
            raise AINotesServiceError("OPENAI_API_KEY environment variable not set")

        self._api_key = api_key
        self._client = None  # Lazy initialization to avoid fork issues

    @property
    def client(self) -> OpenAI:
        """Lazily initialize the OpenAI client to avoid fork() issues on macOS."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def generate_notes(
        self,
        transcript: str,
        video_title: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Generate formatted markdown notes from video transcript.

        Args:
            transcript: Raw transcript text
            video_title: Optional video title for context
            model: OpenAI model to use (default: gpt-4o-mini)

        Returns:
            Dictionary containing:
                - markdown_notes: Formatted notes in markdown
                - model_used: Model that was used
                - tokens_used: Number of tokens consumed
                - was_truncated: Whether transcript was truncated

        Raises:
            AINotesServiceError: If notes generation fails
        """
        if not transcript or not transcript.strip():
            raise AINotesServiceError("Transcript cannot be empty")

        # Token limit handling - GPT-4o-mini has 128k context window
        # Reserve ~4k tokens for response, use ~120k for input
        # Rough estimate: 1 token ≈ 4 characters
        MAX_CHARS = 120000 * 4  # ~480k characters
        was_truncated = False

        if len(transcript) > MAX_CHARS:
            transcript = transcript[:MAX_CHARS]
            was_truncated = True

        # Build prompt
        system_prompt = """You are an expert note-taker. Your task is to create comprehensive, well-structured notes from video transcripts.

Create notes that:
- Use clear markdown formatting with headers (##, ###)
- Organize content into logical sections
- Extract key concepts, definitions, and explanations
- Include important examples or case studies mentioned
- Use bullet points for clarity
- Maintain the original context and meaning

Make the notes study-friendly and easy to review."""

        user_prompt = f"""Create comprehensive notes from this video transcript.

{f'Video Title: {video_title}' if video_title else ''}

Transcript:
{transcript}

Please provide well-structured markdown notes."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )

            markdown_notes = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            return {
                "markdown_notes": markdown_notes,
                "model_used": model,
                "tokens_used": tokens_used,
                "was_truncated": was_truncated
            }

        except Exception as e:
            raise AINotesServiceError(f"Failed to generate notes: {str(e)}")

    def generate_chapters(
        self,
        transcript: str,
        segments: List[Dict[str, Any]],
        video_duration: Optional[float] = None,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Generate video chapters with timestamps from transcript.

        Args:
            transcript: Raw transcript text
            segments: List of transcript segments with timestamps
            video_duration: Total video duration in seconds (optional)
            model: OpenAI model to use (default: gpt-4o-mini)

        Returns:
            Dictionary containing:
                - chapters: List of chapters with title, start_time, end_time, summary
                - model_used: Model that was used
                - tokens_used: Number of tokens consumed

        Raises:
            AINotesServiceError: If chapter generation fails
        """
        if not segments:
            raise AINotesServiceError("Segments cannot be empty")

        # Let AI decide chapter count - just provide video info
        # Create transcript with timestamps for chapter generation
        total_segments = len(segments)

        # Sample segments to fit in context window, but cover ENTIRE video
        max_segments = 1200  # Enough for most videos

        if total_segments > max_segments:
            # Sample evenly across the entire video
            step = max(1, total_segments // max_segments)
            sampled_segments = segments[::step]
            # ALWAYS include last 20 segments to ensure we cover the end
            if len(sampled_segments) > max_segments:
                sampled_segments = sampled_segments[:max_segments-20] + segments[-20:]
        else:
            sampled_segments = segments

        timestamped_transcript = []
        for seg in sampled_segments:
            timestamp = seg.get('start', 0)
            text = seg.get('text', '')
            timestamped_transcript.append(f"[{timestamp:.1f}s] {text}")

        timestamped_text = "\n".join(timestamped_transcript)

        # Calculate video duration info for prompt
        duration_info = ""
        if video_duration:
            hours = int(video_duration // 3600)
            mins = int((video_duration % 3600) // 60)
            secs = int(video_duration % 60)
            if hours > 0:
                duration_info = f"Video duration: {hours} hour {mins} minutes ({int(video_duration)} seconds total)"
            else:
                duration_info = f"Video duration: {mins} minutes {secs} seconds ({int(video_duration)} seconds total)"

        system_prompt = f"""You are an expert at analyzing video content and creating meaningful chapter breakdowns.

{duration_info}

Analyze the transcript and create chapters that cover the ENTIRE video from start to finish.

Guidelines:
- Create as many chapters as needed to properly segment the content (you decide the number)
- First chapter should be "Introduction" or similar, starting at 0.0 seconds
- Last chapter should cover the conclusion/wrap-up section near the end of the video
- Each chapter should represent a distinct topic or section change
- Chapters should be distributed across the ENTIRE video duration
- Create descriptive chapter titles (3-8 words)
- Write brief summaries (1-2 sentences) for each chapter

Return ONLY a valid JSON array with this structure:
[
  {{
    "title": "Introduction",
    "start_time": 0.0,
    "summary": "Brief description"
  }},
  ...more chapters covering the whole video...,
  {{
    "title": "Conclusion/Wrap-up",
    "start_time": <near end of video>,
    "summary": "Brief description"
  }}
]

CRITICAL RULES:
- start_time must be in SECONDS (e.g., 120.0 for 2 minutes, 3600.0 for 1 hour)
- Chapters must be in chronological order
- Return ONLY the JSON array, no other text
- MUST cover from 0 seconds to approximately {int(video_duration) if video_duration else 'the end'} seconds"""

        user_prompt = f"""Create chapters for this video transcript. The video is {int(video_duration) if video_duration else 'unknown'} seconds long.
Cover the ENTIRE video from beginning (0 seconds) to end ({int(video_duration) if video_duration else 'last timestamp'} seconds).

Transcript with timestamps:
{timestamped_text}

Return the chapters as a JSON array."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=4000  # Increased for more chapters
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()

                chapters = json.loads(content)
            except json.JSONDecodeError as e:
                raise AINotesServiceError(f"Failed to parse chapters JSON: {str(e)}")

            # Validate chapters
            if not isinstance(chapters, list):
                raise AINotesServiceError("Chapters must be a list")

            # Reasonable limit to prevent excessive chapters (max 50)
            chapters = chapters[:50]

            # Calculate end times
            for i in range(len(chapters)):
                if i < len(chapters) - 1:
                    # End time is the start of the next chapter
                    chapters[i]["end_time"] = chapters[i + 1]["start_time"]
                else:
                    # Last chapter ends at video duration or last segment
                    if video_duration:
                        chapters[i]["end_time"] = video_duration
                    elif segments:
                        last_segment = segments[-1]
                        chapters[i]["end_time"] = last_segment.get('start', 0) + last_segment.get('duration', 0)
                    else:
                        chapters[i]["end_time"] = chapters[i]["start_time"] + 60  # Default 1 minute

            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            return {
                "chapters": chapters,
                "model_used": model,
                "tokens_used": tokens_used
            }

        except AINotesServiceError:
            raise
        except Exception as e:
            raise AINotesServiceError(f"Failed to generate chapters: {str(e)}")

    def generate_structured_notes(
        self,
        transcript: str,
        segments: List[Dict[str, Any]],
        video_title: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Generate structured notes with summary, bullets, flashcards, etc.

        Args:
            transcript: Raw transcript text
            segments: List of transcript segments with timestamps
            video_title: Optional video title for context
            model: OpenAI model to use (default: gpt-4o-mini)

        Returns:
            Dictionary containing:
                - summary: 2-3 sentence summary
                - bullets: List of key points (5-10 items)
                - key_timestamps: List of important moments with timestamps
                - flashcards: List of Q&A pairs for studying
                - action_items: List of actionable takeaways
                - topics: List of main topics/tags
                - difficulty_level: beginner/intermediate/advanced
                - model_used: Model that was used
                - tokens_used: Number of tokens consumed

        Raises:
            AINotesServiceError: If generation fails
        """
        if not transcript or not transcript.strip():
            raise AINotesServiceError("Transcript cannot be empty")

        # Truncate if too long
        MAX_CHARS = 100000  # ~25k tokens for input
        truncated_transcript = transcript[:MAX_CHARS] if len(transcript) > MAX_CHARS else transcript

        # Build timestamped context for key_timestamps
        timestamp_context = []
        for seg in segments[:200]:  # Sample of segments for timestamps
            timestamp = seg.get('start', 0)
            text = seg.get('text', '')
            mins = int(timestamp // 60)
            secs = int(timestamp % 60)
            timestamp_context.append(f"[{mins:02d}:{secs:02d}] {text}")

        timestamp_text = "\n".join(timestamp_context)

        system_prompt = """You are an expert educational content analyzer. Analyze video transcripts and generate structured learning materials.

Return a valid JSON object with EXACTLY this structure:
{
  "summary": "A 2-3 sentence summary of the video content",
  "bullets": ["Key point 1", "Key point 2", ...],
  "key_timestamps": [
    {"label": "Topic name", "time": "MM:SS", "seconds": 123},
    ...
  ],
  "flashcards": [
    {"front": "Question?", "back": "Answer"},
    ...
  ],
  "action_items": ["Action 1", "Action 2", ...],
  "topics": ["topic1", "topic2", ...],
  "difficulty_level": "beginner" | "intermediate" | "advanced"
}

Guidelines:
- summary: Concise 2-3 sentences capturing the main message
- bullets: 5-10 most important takeaways
- key_timestamps: 5-8 important moments with accurate timestamps from the transcript
- flashcards: 5-10 Q&A pairs for studying the content
- action_items: 3-5 actionable steps viewers can take (or empty array if none)
- topics: 3-7 topic tags for categorization
- difficulty_level: Based on content complexity

Return ONLY the JSON object, no additional text."""

        user_prompt = f"""Analyze this video and generate structured learning materials.

{f'Video Title: {video_title}' if video_title else ''}

Transcript:
{truncated_transcript}

Timestamped segments for reference:
{timestamp_text}

Return the structured JSON response."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=3000
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
                raise AINotesServiceError(f"Failed to parse structured notes JSON: {str(e)}")

            # Validate required fields with defaults
            validated_result = {
                "summary": result.get("summary", ""),
                "bullets": result.get("bullets", []),
                "key_timestamps": result.get("key_timestamps", []),
                "flashcards": result.get("flashcards", []),
                "action_items": result.get("action_items", []),
                "topics": result.get("topics", []),
                "difficulty_level": result.get("difficulty_level", "intermediate"),
                "model_used": model,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }

            # Validate difficulty_level
            if validated_result["difficulty_level"] not in ["beginner", "intermediate", "advanced"]:
                validated_result["difficulty_level"] = "intermediate"

            return validated_result

        except AINotesServiceError:
            raise
        except Exception as e:
            raise AINotesServiceError(f"Failed to generate structured notes: {str(e)}")
