"""
AI Notes Service for generating notes and chapters from video transcripts.
"""
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
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

IMPORTANT: ALWAYS write notes in ENGLISH, regardless of the transcript's original language. Translate all content to English.

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
        Uses a two-step approach:
        1. Pre-calculate evenly spaced time slots
        2. Ask AI to name each slot based on content at that time
        """
        if not segments:
            raise AINotesServiceError("Segments cannot be empty")

        # Get actual video duration from segments if not provided
        if not video_duration and segments:
            last_seg = segments[-1]
            video_duration = last_seg.get('start', 0) + last_seg.get('duration', 0)

        # Calculate number of chapters: 1 per 3 minutes, min 6, max 25
        num_chapters = max(6, min(25, int(video_duration / 180))) if video_duration else 10

        # Pre-calculate evenly spaced chapter start times
        chapter_interval = video_duration / num_chapters
        chapter_times = []
        for i in range(num_chapters):
            start_time = int(i * chapter_interval)
            chapter_times.append(start_time)

        # Build context for each chapter slot - get transcript around each timestamp
        chapter_contexts = []
        for i, start_time in enumerate(chapter_times):
            end_time = chapter_times[i + 1] if i < len(chapter_times) - 1 else int(video_duration)

            # Get segments in this time range
            slot_text = []
            for seg in segments:
                seg_start = seg.get('start', 0)
                if start_time <= seg_start < end_time:
                    slot_text.append(seg.get('text', ''))

            # Take first ~500 chars of this slot's content
            content = ' '.join(slot_text)[:500]
            mins = int(start_time // 60)
            secs = int(start_time % 60)

            chapter_contexts.append({
                "slot": i + 1,
                "time": f"{mins}:{secs:02d}",
                "seconds": start_time,
                "content_preview": content if content else "(no transcript at this point)"
            })

        # Format for prompt
        slots_text = ""
        for ctx in chapter_contexts:
            slots_text += f"\nSlot {ctx['slot']} at {ctx['time']} ({ctx['seconds']}s):\n{ctx['content_preview']}\n"

        total_mins = int(video_duration // 60)
        total_secs = int(video_duration % 60)

        system_prompt = """You are creating YouTube video chapters with titles and summaries. I will give you pre-calculated timestamps with content previews. Your job is to give each slot a short title AND a brief summary.

RULES:
- Titles must be 2-5 words max
- Use specific, descriptive names based on the content
- Examples: "The Problem", "Building the Demo", "Q&A Session", "Key Takeaways"
- NO generic names like "Part 1", "Section 2", "Middle", "Continued"
- First slot should be "Introduction" or describe what the video starts with
- Last slot should be "Conclusion", "Wrap Up", "Final Thoughts" or similar
- Summary should be 1-2 sentences describing what's covered in that chapter
- ALWAYS write in ENGLISH regardless of transcript language

Return ONLY a JSON array with title and summary for each slot:
[
  {"slot": 1, "title": "Introduction", "summary": "Brief overview of the video topic and what will be covered."},
  {"slot": 2, "title": "The Main Topic", "summary": "Explanation of the core concept with examples."},
  ...
]"""

        user_prompt = f"""Video length: {total_mins}:{total_secs:02d} ({int(video_duration)} seconds)
Number of chapters needed: {num_chapters}

Give a title AND summary for each of these {num_chapters} chapter slots:
{slots_text}

Return JSON array with title and summary for each slot."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            ai_titles = json.loads(content)

            # Build final chapters by combining pre-calculated times with AI titles and summaries
            chapters = []
            for i, time_sec in enumerate(chapter_times):
                # Find matching title and summary from AI response
                title = "Chapter"
                summary = ""
                for item in ai_titles:
                    if item.get("slot") == i + 1:
                        title = item.get("title", "Chapter")
                        summary = item.get("summary", "")
                        break

                # Fallback titles
                if not title or title == "Chapter":
                    if i == 0:
                        title = "Introduction"
                    elif i == len(chapter_times) - 1:
                        title = "Conclusion"
                    else:
                        title = f"Part {i + 1}"

                chapters.append({
                    "title": title,
                    "start_time": time_sec,
                    "summary": summary
                })

            # Calculate end times
            for i in range(len(chapters)):
                if i < len(chapters) - 1:
                    chapters[i]["end_time"] = chapters[i + 1]["start_time"]
                else:
                    chapters[i]["end_time"] = video_duration

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

IMPORTANT: ALWAYS write ALL content in ENGLISH, regardless of the transcript's original language. Translate everything to English.

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

    def transliterate_to_english(
        self,
        segments: List[Dict[str, Any]],
        source_language: str,
        model: str = "gpt-3.5-turbo"
    ) -> Dict[str, Any]:
        """
        Transliterate non-English transcript segments to readable English.
        Uses parallel batch processing for speed.

        Handles both:
        1. Transliteration: Hindi/other scripts containing phonetic English → Roman English
           (e.g., "हाई एवरीवन" → "Hi everyone")
        2. Translation: Actual foreign language content → English meaning

        Uses GPT-3.5-turbo for cost efficiency - this is a lightweight text conversion task.
        Processes batches in parallel for ~3-4x speed improvement.

        Args:
            segments: List of transcript segments with text, start, duration
            source_language: Source language code (e.g., 'hi', 'es', 'fr')
            model: OpenAI model to use (default: gpt-3.5-turbo for cost)

        Returns:
            Dictionary containing:
                - segments: Converted segments with preserved timing
                - raw_text: Full converted text
                - tokens_used: Total tokens consumed
                - was_transliterated: Whether conversion was performed
        """
        if not segments:
            return {"segments": [], "raw_text": "", "tokens_used": 0, "was_transliterated": False}

        # Skip if already in English
        if source_language.lower().startswith('en'):
            raw_text = " ".join([seg.get('text', '') for seg in segments])
            return {"segments": segments, "raw_text": raw_text, "tokens_used": 0, "was_transliterated": False}

        # Batch segments for efficient processing
        BATCH_SIZE = 100
        MAX_PARALLEL = 4  # Run up to 4 API calls in parallel

        # Create batches with their indices
        batches: List[Tuple[int, List[Dict[str, Any]]]] = []
        for batch_start in range(0, len(segments), BATCH_SIZE):
            batch = segments[batch_start:batch_start + BATCH_SIZE]
            batches.append((batch_start, batch))

        print(f"  [Transliteration] Processing {len(segments)} segments in {len(batches)} batches (parallel={MAX_PARALLEL})")

        # Process a single batch
        def process_batch(batch_info: Tuple[int, List[Dict[str, Any]]]) -> Tuple[int, List[Dict[str, Any]], int]:
            batch_idx, batch = batch_info
            batch_results = []
            tokens = 0

            # Create numbered list for conversion
            texts_to_convert = []
            for i, seg in enumerate(batch):
                texts_to_convert.append(f"{i+1}. {seg.get('text', '')}")

            batch_text = "\n".join(texts_to_convert)

            # Smart prompt that handles both transliteration AND translation
            system_prompt = """You are a transcript converter. Convert the given text to readable English.

The text might be:
1. PHONETIC ENGLISH in non-Latin script (like Hindi/Devanagari containing English words spoken phonetically)
   - Example: "हाई एवरीवन एंड वेलकम" → "Hi everyone and welcome"
   - This is English SPOKEN but written in Hindi script - convert to Roman letters

2. ACTUAL foreign language content
   - Translate the meaning to English

RULES:
- Keep the line numbers (1., 2., etc.)
- Output readable, natural English
- Keep the same number of lines
- Output ONLY the converted numbered list"""

            user_prompt = f"""Convert these {len(batch)} lines to English (transliterate if phonetic English, translate if actual {source_language}):

{batch_text}"""

            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=4000
                )

                content = response.choices[0].message.content.strip()
                tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0

                # Parse converted lines back
                converted_lines = content.split('\n')

                for i, seg in enumerate(batch):
                    converted_text = seg.get('text', '')  # Default to original

                    # Find matching converted line
                    prefix = f"{i+1}."
                    for line in converted_lines:
                        line = line.strip()
                        if line.startswith(prefix):
                            converted_text = line[len(prefix):].strip()
                            break

                    batch_results.append({
                        "text": converted_text,
                        "start": seg.get('start', 0),
                        "duration": seg.get('duration', 0)
                    })

            except Exception as e:
                # On error, keep original text for this batch
                print(f"  [Transliteration] Batch {batch_idx} failed: {e}")
                for seg in batch:
                    batch_results.append({
                        "text": seg.get('text', ''),
                        "start": seg.get('start', 0),
                        "duration": seg.get('duration', 0)
                    })

            return (batch_idx, batch_results, tokens)

        # Process batches in parallel
        results_map: Dict[int, List[Dict[str, Any]]] = {}
        total_tokens = 0

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
            futures = {executor.submit(process_batch, batch): batch[0] for batch in batches}

            for future in as_completed(futures):
                batch_idx, batch_results, tokens = future.result()
                results_map[batch_idx] = batch_results
                total_tokens += tokens
                print(f"  [Transliteration] ✓ Batch at {batch_idx} done ({tokens} tokens)")

        # Reassemble results in order
        converted_segments = []
        for batch_start in range(0, len(segments), BATCH_SIZE):
            if batch_start in results_map:
                converted_segments.extend(results_map[batch_start])

        # Build raw text from converted segments
        raw_text = " ".join([seg['text'] for seg in converted_segments])

        print(f"  [Transliteration] ✓ Complete! {len(converted_segments)} segments, {total_tokens} tokens")

        return {
            "segments": converted_segments,
            "raw_text": raw_text,
            "tokens_used": total_tokens,
            "was_transliterated": True
        }
