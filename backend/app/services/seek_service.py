"""
Seek Service for finding timestamps in video transcripts using LLM.
Uses a slot-based approach to ensure full video coverage for long videos.
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
        Uses slot-based indexing to ensure full video coverage.
        """
        if not query or not query.strip():
            raise SeekServiceError("Query cannot be empty")

        if not segments:
            raise SeekServiceError("No transcript segments provided")

        # Get video duration from segments if not provided
        if not video_duration and segments:
            last_seg = segments[-1]
            video_duration = last_seg.get('start', 0) + last_seg.get('duration', 0)

        # Build searchable index with time slots covering entire video
        search_index = self._build_search_index(segments, video_duration)

        # Format index for AI
        index_text = ""
        for slot in search_index:
            index_text += f"\n[{slot['id']}] {slot['time_label']} ({slot['start_sec']}s):\n{slot['content']}\n"

        total_mins = int(video_duration // 60) if video_duration else 0
        total_secs = int(video_duration % 60) if video_duration else 0

        system_prompt = """You are a video search assistant. Given a search query and a video index, find where the topic is discussed.

TASK: Look at each time slot's content and find the BEST match for the user's query.

RULES:
- Search the ENTIRE index, not just the beginning
- The query may be in ANY language - understand the meaning
- Pick the slot where the topic is MOST CLEARLY discussed
- If topic appears multiple times, pick the FIRST occurrence

Return ONLY valid JSON:
{
  "slot_id": <number or null if not found>,
  "confidence": "high" | "medium" | "low" | "none",
  "reason": "<brief explanation, max 50 chars>"
}

Confidence:
- "high": exact topic match found
- "medium": related topic found
- "low": weak/tangential match
- "none": topic not in video (slot_id should be null)"""

        user_prompt = f"""Find where this topic is discussed in the {total_mins}:{total_secs:02d} video:

Query: "{query}"

Search through ALL {len(search_index)} time slots below:
{index_text}

Which slot best matches the query?"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Low temperature for consistency
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                return {
                    "timestamp": None,
                    "confidence": "none",
                    "matched_text": ""
                }

            # Convert slot_id to actual timestamp
            slot_id = result.get("slot_id")
            timestamp = None
            matched_text = ""

            if slot_id is not None:
                for slot in search_index:
                    if slot["id"] == slot_id:
                        timestamp = slot["start_sec"]
                        matched_text = slot["content"][:100]
                        break

            confidence = result.get("confidence", "none")
            if confidence not in ["high", "medium", "low", "none"]:
                confidence = "low"

            if timestamp is None:
                confidence = "none"

            return {
                "timestamp": timestamp,
                "confidence": confidence,
                "matched_text": matched_text
            }

        except SeekServiceError:
            raise
        except Exception as e:
            raise SeekServiceError(f"Failed to find timestamp: {str(e)}")

    def _build_search_index(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float
    ) -> List[Dict[str, Any]]:
        """
        Build a searchable index with evenly spaced time slots.
        Each slot contains a content preview from that part of the video.
        Guarantees full video coverage.
        """
        if not segments or not video_duration:
            return []

        # Calculate slot duration based on video length
        # Shorter videos: smaller slots for precision
        # Longer videos: larger slots to fit in context
        if video_duration > 7200:  # > 2 hours
            slot_duration = 180  # 3 minute slots
            max_slots = 50
        elif video_duration > 3600:  # > 1 hour
            slot_duration = 120  # 2 minute slots
            max_slots = 40
        elif video_duration > 1800:  # > 30 min
            slot_duration = 90  # 1.5 minute slots
            max_slots = 30
        else:
            slot_duration = 60  # 1 minute slots
            max_slots = 25

        # Calculate actual number of slots
        num_slots = min(max_slots, max(10, int(video_duration / slot_duration)))
        actual_slot_duration = video_duration / num_slots

        search_index = []

        for i in range(num_slots):
            start_time = int(i * actual_slot_duration)
            end_time = int((i + 1) * actual_slot_duration)

            # Get all text in this time range
            slot_text = []
            for seg in segments:
                seg_start = seg.get('start', 0)
                if start_time <= seg_start < end_time:
                    slot_text.append(seg.get('text', ''))

            # Join and truncate content
            content = ' '.join(slot_text)
            # Keep ~300 chars per slot for long videos, more for short
            max_content_len = 500 if video_duration < 1800 else 300
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."

            # Format time label
            mins = int(start_time // 60)
            secs = int(start_time % 60)

            search_index.append({
                "id": i + 1,
                "start_sec": start_time,
                "end_sec": end_time,
                "time_label": f"{mins}:{secs:02d}",
                "content": content if content else "(silence/no speech)"
            })

        return search_index
