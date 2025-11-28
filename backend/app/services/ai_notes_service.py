"""
AI Notes Service for generating notes and chapters from video transcripts.
"""
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from openai import OpenAI

from app.core.config import settings
from app.core.constants import TokenLimits, AIModels
from app.prompts import (
    CHAPTERS_SYSTEM_PROMPT,
    CHAPTERS_USER_PROMPT_TEMPLATE,
    STRUCTURED_NOTES_SYSTEM_PROMPT,
    STRUCTURED_NOTES_USER_PROMPT_TEMPLATE,
    TRANSLITERATION_SYSTEM_PROMPT,
    TRANSLITERATION_USER_PROMPT_TEMPLATE,
)


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

    def generate_chapters(
        self,
        transcript: str,
        segments: List[Dict[str, Any]],
        video_duration: Optional[float] = None,
        model: str = AIModels.CHAPTERS_MODEL
    ) -> Dict[str, Any]:
        """Generate video chapters from transcript segments."""
        if not segments:
            raise AINotesServiceError("Segments cannot be empty")

        # Get duration from last segment if not provided
        if not video_duration:
            last_seg = segments[-1]
            video_duration = last_seg.get('start', 0) + last_seg.get('duration', 0)

        # Send ALL segments - GPT-4o-mini has 128K context, even 2-hour videos (~2400 segments)
        # only use ~28% of context. This ensures AI can pick ANY exact timestamp.

        # Build timestamped transcript - send seconds directly so AI doesn't need to convert
        timestamped_lines = []
        for seg in segments:
            start_seconds = int(seg['start'])
            timestamped_lines.append(f"[{start_seconds}] {seg.get('text', '')}")

        timestamped_text = "\n".join(timestamped_lines)

        user_prompt = CHAPTERS_USER_PROMPT_TEMPLATE.format(
            duration_minutes=int(video_duration // 60),
            transcript=timestamped_text
        )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": CHAPTERS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()
            chapters = self._parse_json_response(content)

            # Validate timestamps - filter out any that exceed video duration
            validated_chapters = []
            for chapter in chapters:
                if chapter.get("start_time", 0) < video_duration:
                    validated_chapters.append(chapter)
            chapters = validated_chapters if validated_chapters else [{"title": "Introduction", "start_time": 0, "summary": "Video content"}]

            # Add end_time to each chapter
            for i, chapter in enumerate(chapters):
                if i < len(chapters) - 1:
                    chapter["end_time"] = chapters[i + 1]["start_time"]
                else:
                    chapter["end_time"] = int(video_duration)

            return {
                "chapters": chapters,
                "model_used": model,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }

        except Exception as e:
            raise AINotesServiceError(f"Failed to generate chapters: {str(e)}")

    def _parse_json_response(self, content: str) -> list:
        """Parse JSON from AI response, handling markdown code blocks."""
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)

    def generate_structured_notes(
        self,
        transcript: str,
        segments: List[Dict[str, Any]],
        video_title: Optional[str] = None,
        model: str = AIModels.NOTES_MODEL
    ) -> Dict[str, Any]:
        """
        Generate structured notes with summary, bullets, flashcards, etc.

        Args:
            transcript: Raw transcript text
            segments: List of transcript segments with timestamps
            video_title: Optional video title for context
            model: OpenAI model to use

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
        max_chars = TokenLimits.STRUCTURED_NOTES_MAX_CHARS
        truncated_transcript = transcript[:max_chars] if len(transcript) > max_chars else transcript

        # Build timestamped context for key_timestamps
        timestamp_context = []
        for seg in segments[:200]:  # Sample of segments for timestamps
            timestamp = seg.get('start', 0)
            text = seg.get('text', '')
            mins = int(timestamp // 60)
            secs = int(timestamp % 60)
            timestamp_context.append(f"[{mins:02d}:{secs:02d}] {text}")

        timestamp_text = "\n".join(timestamp_context)

        video_title_section = f'Video Title: {video_title}' if video_title else ''
        user_prompt = STRUCTURED_NOTES_USER_PROMPT_TEMPLATE.format(
            video_title_section=video_title_section,
            transcript=truncated_transcript,
            timestamp_text=timestamp_text
        )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": STRUCTURED_NOTES_SYSTEM_PROMPT},
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

    def transliterate_to_english(
        self,
        segments: List[Dict[str, Any]],
        source_language: str,
        model: str = AIModels.TRANSLITERATION_MODEL
    ) -> Dict[str, Any]:
        """Transliterate/translate non-English transcript to English using parallel batches."""
        if not segments:
            return {"segments": [], "raw_text": "", "tokens_used": 0, "was_transliterated": False}

        # Skip if already English
        if source_language.lower().startswith('en'):
            raw_text = " ".join([seg.get('text', '') for seg in segments])
            return {"segments": segments, "raw_text": raw_text, "tokens_used": 0, "was_transliterated": False}

        batch_size = TokenLimits.TRANSLITERATION_BATCH_SIZE
        max_parallel = TokenLimits.TRANSLITERATION_MAX_PARALLEL

        # Split into batches
        batches = [segments[i:i + batch_size] for i in range(0, len(segments), batch_size)]
        print(f"  [Transliteration] Processing {len(segments)} segments in {len(batches)} batches")

        # Process batches in parallel
        total_tokens = 0
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            results = list(executor.map(
                lambda batch: self._transliterate_batch(batch, source_language, model),
                batches
            ))

        # Flatten results
        converted_segments = []
        for batch_result, tokens in results:
            converted_segments.extend(batch_result)
            total_tokens += tokens

        raw_text = " ".join([seg['text'] for seg in converted_segments])
        print(f"  [Transliteration] ✓ Complete! {len(converted_segments)} segments, {total_tokens} tokens")

        return {
            "segments": converted_segments,
            "raw_text": raw_text,
            "tokens_used": total_tokens,
            "was_transliterated": True
        }

    def _transliterate_batch(
        self,
        batch: List[Dict[str, Any]],
        source_language: str,
        model: str
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Transliterate a single batch of segments."""
        # Build numbered list
        batch_text = "\n".join([f"{i+1}. {seg.get('text', '')}" for i, seg in enumerate(batch)])

        user_prompt = TRANSLITERATION_USER_PROMPT_TEMPLATE.format(
            num_lines=len(batch),
            source_language=source_language,
            batch_text=batch_text
        )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": TRANSLITERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )

            content = response.choices[0].message.content.strip()
            tokens = response.usage.total_tokens if response.usage else 0
            converted_lines = {
                line.split('.', 1)[0].strip(): line.split('.', 1)[1].strip()
                for line in content.split('\n')
                if '.' in line and line.split('.', 1)[0].strip().isdigit()
            }

            results = []
            for i, seg in enumerate(batch):
                results.append({
                    "text": converted_lines.get(str(i + 1), seg.get('text', '')),
                    "start": seg.get('start', 0),
                    "duration": seg.get('duration', 0)
                })
            return results, tokens

        except Exception as e:
            print(f"  [Transliteration] Batch failed: {e}")
            # Return original on error
            return [{"text": seg.get('text', ''), "start": seg.get('start', 0), "duration": seg.get('duration', 0)} for seg in batch], 0
