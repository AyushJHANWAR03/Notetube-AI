"""
AI Notes Service for generating notes and chapters from video transcripts.

Uses Groq as primary provider (fast) with OpenAI fallback (reliable).
"""
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import json

from app.core.config import settings
from app.core.constants import TokenLimits, AIModels
from app.services.ai_provider import AIProvider, AIProviderError
from app.prompts import (
    CHAPTERS_SYSTEM_PROMPT,
    CHAPTERS_USER_PROMPT_TEMPLATE,
    STRUCTURED_NOTES_SYSTEM_PROMPT,
    STRUCTURED_NOTES_USER_PROMPT_TEMPLATE,
    TRANSLITERATION_SYSTEM_PROMPT,
    TRANSLITERATION_USER_PROMPT_TEMPLATE,
    CHUNK_TOPICS_SYSTEM_PROMPT,
    CHUNK_TOPICS_USER_PROMPT_TEMPLATE,
)
from app.services.transcript_processor import (
    chunk_transcript,
    deduplicate_candidates,
    apply_temporal_distribution,
)


class AINotesServiceError(Exception):
    """Custom exception for AI Notes service errors."""
    pass


def _get_flashcard_count_for_duration(video_duration: float) -> str:
    """Get recommended flashcard count range based on video duration.

    Args:
        video_duration: Video duration in seconds

    Returns:
        String range like "5-8", "8-12", etc.
    """
    if video_duration < 600:  # < 10 min
        return "5-8"
    elif video_duration < 1800:  # 10-30 min
        return "8-12"
    elif video_duration < 3600:  # 30-60 min
        return "12-18"
    else:  # > 60 min
        return "18-25"


class AINotesService:
    """Service for generating AI-powered notes and chapters from transcripts.

    Uses Groq as primary AI provider for speed, with OpenAI as fallback.
    """

    def __init__(self):
        """Initialize the AI Notes service with the unified AI provider."""
        self._provider = None  # Lazy initialization to avoid fork issues

    @property
    def provider(self) -> AIProvider:
        """Lazily initialize the AI provider to avoid fork() issues on macOS."""
        if self._provider is None:
            self._provider = AIProvider()
        return self._provider

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
            messages = [
                {"role": "system", "content": CHAPTERS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            response = self.provider.generate(
                messages=messages,
                model=model,
                temperature=0.3,
                max_tokens=2000,
                json_mode=True
            )

            chapters = self._parse_json_response(response.content)

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
                "model_used": f"{response.provider.value}:{response.model}",
                "tokens_used": response.tokens_used
            }

        except AIProviderError as e:
            raise AINotesServiceError(f"Failed to generate chapters: {str(e)}")
        except Exception as e:
            raise AINotesServiceError(f"Failed to generate chapters: {str(e)}")

    def generate_chapters_chunked(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        requested_chapters: int = 10,
        model: str = AIModels.CHAPTERS_MODEL
    ) -> Dict[str, Any]:
        """
        Generate chapters using map-reduce over 5-minute chunks.

        For long videos (>10 min), this approach:
        1. Chunks transcript into 5-min windows with 45s overlap
        2. Processes each chunk in parallel to find topic candidates
        3. Deduplicates overlapping topics
        4. Applies 60/40 temporal distribution for full video coverage

        Args:
            segments: List of transcript segments
            video_duration: Video duration in seconds
            requested_chapters: Target number of chapters
            model: AI model to use

        Returns:
            Dictionary with chapters, model_used, tokens_used
        """
        if not segments:
            raise AINotesServiceError("Segments cannot be empty")

        print(f"  [Chunked] Starting map-reduce chapter generation...")
        print(f"  [Chunked] Video duration: {int(video_duration)}s ({int(video_duration // 60)} min)")

        # Step 1: Chunk the transcript
        chunks = chunk_transcript(segments, video_duration)
        print(f"  [Chunked] Created {len(chunks)} chunks (5-min with 45s overlap)")

        # Step 2: Process chunks in parallel (MAP phase)
        total_tokens = 0
        all_candidates = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            chunk_args = [
                (chunk, i, len(chunks), model)
                for i, chunk in enumerate(chunks)
            ]
            results = list(executor.map(
                lambda args: self._process_chunk_for_topics(*args),
                chunk_args
            ))

        for candidates, tokens in results:
            all_candidates.extend(candidates)
            total_tokens += tokens

        print(f"  [Chunked] MAP phase complete: {len(all_candidates)} candidates, {total_tokens} tokens")

        # Step 3: Deduplicate overlapping candidates
        unique_candidates = deduplicate_candidates(all_candidates, key="title")
        print(f"  [Chunked] After deduplication: {len(unique_candidates)} unique topics")

        # Step 4: Apply 60/40 temporal distribution (REDUCE phase)
        final_topics = apply_temporal_distribution(
            unique_candidates,
            video_duration,
            requested_topics=requested_chapters
        )
        print(f"  [Chunked] After 60/40 distribution: {len(final_topics)} final chapters")

        # Step 5: Build final chapters
        chapters = []

        # Always start with Introduction at 0
        if not final_topics or final_topics[0].get("start_time", 0) > 0:
            chapters.append({
                "title": "Introduction",
                "start_time": 0,
                "summary": "Video introduction and opening"
            })

        for topic in final_topics:
            chapters.append({
                "title": topic.get("title", "Topic"),
                "start_time": topic.get("start_time", 0),
                "summary": topic.get("summary", "")
            })

        # Sort by start_time and add end_times
        chapters = sorted(chapters, key=lambda x: x["start_time"])

        for i, chapter in enumerate(chapters):
            if i < len(chapters) - 1:
                chapter["end_time"] = chapters[i + 1]["start_time"]
            else:
                chapter["end_time"] = int(video_duration)

        print(f"  [Chunked] ✓ Generated {len(chapters)} chapters")

        return {
            "chapters": chapters,
            "model_used": f"chunked:{model}",
            "tokens_used": total_tokens
        }

    def _process_chunk_for_topics(
        self,
        chunk: Dict[str, Any],
        chunk_index: int,
        total_chunks: int,
        model: str
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Process a single chunk to find topic candidates.

        Returns up to 2 topics per chunk.
        """
        segments = chunk.get("segments", [])
        if not segments:
            return [], 0

        # Build timestamped transcript for this chunk
        timestamped_lines = []
        for seg in segments:
            start_seconds = int(seg.get('start', 0))
            timestamped_lines.append(f"[{start_seconds}] {seg.get('text', '')}")

        transcript_text = "\n".join(timestamped_lines)

        user_prompt = CHUNK_TOPICS_USER_PROMPT_TEMPLATE.format(
            chunk_index=chunk_index + 1,
            total_chunks=total_chunks,
            start_time=int(chunk.get("start_time", 0)),
            end_time=int(chunk.get("end_time", 0)),
            transcript=transcript_text
        )

        try:
            messages = [
                {"role": "system", "content": CHUNK_TOPICS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            response = self.provider.generate(
                messages=messages,
                model=model,
                temperature=0.3,
                max_tokens=500,
                json_mode=True
            )

            parsed = self._parse_json_response(response.content)

            # Handle both array and object responses
            if isinstance(parsed, dict):
                # AI might return {"topics": [...]} instead of just [...]
                topics = parsed.get("topics", []) or list(parsed.values())[0] if parsed else []
            elif isinstance(parsed, list):
                topics = parsed
            else:
                topics = []

            # Validate and limit to 2 topics per chunk
            valid_topics = []
            for topic in topics[:2]:
                if isinstance(topic, dict) and "title" in topic and "start_time" in topic:
                    valid_topics.append(topic)

            return valid_topics, response.tokens_used

        except Exception as e:
            print(f"  [Chunked] Chunk {chunk_index + 1} failed: {e}")
            return [], 0

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
        video_duration: float = 0,
        model: str = AIModels.NOTES_MODEL
    ) -> Dict[str, Any]:
        """
        Generate structured notes with summary, bullets, flashcards, etc.

        Args:
            transcript: Raw transcript text
            segments: List of transcript segments with timestamps
            video_title: Optional video title for context
            video_duration: Video duration in seconds (for dynamic flashcard count)
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

        # Build timestamped context for key_timestamps - use ALL segments
        # GPT-4o-mini has 128K context, so we can handle full transcripts
        timestamp_context = []
        for seg in segments:
            timestamp = seg.get('start', 0)
            text = seg.get('text', '')
            mins = int(timestamp // 60)
            secs = int(timestamp % 60)
            timestamp_context.append(f"[{mins:02d}:{secs:02d}] {text}")

        timestamp_text = "\n".join(timestamp_context)

        # Calculate dynamic flashcard count based on video duration
        flashcard_count = _get_flashcard_count_for_duration(video_duration)

        # Format system prompt with dynamic flashcard count
        system_prompt = STRUCTURED_NOTES_SYSTEM_PROMPT.format(
            flashcard_count=flashcard_count
        )

        video_title_section = f'Video Title: {video_title}' if video_title else ''
        user_prompt = STRUCTURED_NOTES_USER_PROMPT_TEMPLATE.format(
            video_title_section=video_title_section,
            transcript=truncated_transcript,
            timestamp_text=timestamp_text
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = self.provider.generate(
                messages=messages,
                model=model,
                temperature=0.5,
                max_tokens=3000,
                json_mode=True
            )

            content = response.content.strip()

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
                "model_used": f"{response.provider.value}:{response.model}",
                "tokens_used": response.tokens_used
            }

            # Validate difficulty_level
            if validated_result["difficulty_level"] not in ["beginner", "intermediate", "advanced"]:
                validated_result["difficulty_level"] = "intermediate"

            return validated_result

        except AIProviderError as e:
            raise AINotesServiceError(f"Failed to generate structured notes: {str(e)}")
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
            messages = [
                {"role": "system", "content": TRANSLITERATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            response = self.provider.generate(
                messages=messages,
                model=model,
                temperature=0.2,
                max_tokens=4000
            )

            content = response.content.strip()
            tokens = response.tokens_used
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
