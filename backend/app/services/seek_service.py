"""
Seek Service for finding timestamps in video transcripts.

Supports two search modes:
1. Embedding-based search (fast, accurate) - uses pre-computed embeddings
2. LLM-based search (fallback) - uses slot-based approach with GPT

For new videos with embeddings, uses cosine similarity search.
For old videos without embeddings, falls back to LLM-based search.
"""
from typing import Dict, Any, List, Optional, Union
from uuid import UUID
import json

from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.constants import AIModels
from app.prompts import SEEK_SYSTEM_PROMPT, SEEK_USER_PROMPT_TEMPLATE
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError
from app.models.transcript_embedding import TranscriptEmbedding


class SeekServiceError(Exception):
    """Custom exception for Seek service errors."""
    pass


class SeekService:
    """
    Service for finding video timestamps using semantic search.

    Primary: Embedding-based search (cosine similarity)
    Fallback: LLM-based search (GPT slot-based)
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Seek service with lazy client initialization."""
        if api_key is None:
            api_key = settings.OPENAI_API_KEY

        if not api_key:
            raise SeekServiceError("OPENAI_API_KEY environment variable not set")

        self._api_key = api_key
        self._client = None  # Lazy initialization to avoid fork issues
        self._embedding_service = None

    @property
    def client(self) -> OpenAI:
        """Lazily initialize the OpenAI client to avoid fork() issues on macOS."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazily initialize the EmbeddingService."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService(api_key=self._api_key)
        return self._embedding_service

    async def find_timestamp_with_embeddings_async(
        self,
        query: str,
        transcript_id: UUID,
        db: AsyncSession,
        top_k: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Find timestamp using pre-computed embeddings (fast path) - async version.

        Args:
            query: Search query from user
            transcript_id: UUID of the transcript
            db: Async database session
            top_k: Number of top results to consider

        Returns:
            Dict with timestamp, confidence, and matched_text, or None if no embeddings
        """
        if not query or not query.strip():
            raise SeekServiceError("Query cannot be empty")

        # Check if embeddings exist for this transcript
        result = await db.execute(
            select(TranscriptEmbedding)
            .where(TranscriptEmbedding.transcript_id == transcript_id)
            .limit(1)
        )
        embedding_exists = result.scalar_one_or_none()

        if not embedding_exists:
            return None  # Signal to use fallback

        # Embed the query
        try:
            query_embedding = self.embedding_service.embed_query(query)
        except EmbeddingServiceError as e:
            raise SeekServiceError(f"Failed to embed query: {str(e)}")

        # Get all embeddings for this transcript
        result = await db.execute(
            select(TranscriptEmbedding)
            .where(TranscriptEmbedding.transcript_id == transcript_id)
            .order_by(TranscriptEmbedding.segment_index)
        )
        embeddings = result.scalars().all()

        if not embeddings:
            return None  # Signal to use fallback

        # Calculate similarity for each embedding
        results = []
        for emb in embeddings:
            similarity = self.embedding_service.cosine_similarity(
                query_embedding,
                list(emb.embedding)
            )
            results.append({
                "start_time": emb.start_time,
                "text": emb.segment_text,
                "similarity": similarity
            })

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Get best match
        if not results:
            return {
                "timestamp": None,
                "confidence": "none",
                "matched_text": ""
            }

        best_match = results[0]
        confidence = self.embedding_service.similarity_to_confidence(best_match["similarity"])

        return {
            "timestamp": best_match["start_time"],
            "confidence": confidence,
            "matched_text": best_match["text"][:100] if best_match["text"] else ""
        }

    def find_timestamp_with_embeddings(
        self,
        query: str,
        transcript_id: UUID,
        db: Session,
        top_k: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Find timestamp using pre-computed embeddings (fast path) - sync version.
        Used by the worker for sync database sessions.

        Args:
            query: Search query from user
            transcript_id: UUID of the transcript
            db: Database session
            top_k: Number of top results to consider

        Returns:
            Dict with timestamp, confidence, and matched_text, or None if no embeddings
        """
        if not query or not query.strip():
            raise SeekServiceError("Query cannot be empty")

        # Check if embeddings exist for this transcript
        embedding_count = db.execute(
            select(TranscriptEmbedding)
            .where(TranscriptEmbedding.transcript_id == transcript_id)
            .limit(1)
        ).scalar_one_or_none()

        if not embedding_count:
            return None  # Signal to use fallback

        # Embed the query
        try:
            query_embedding = self.embedding_service.embed_query(query)
        except EmbeddingServiceError as e:
            raise SeekServiceError(f"Failed to embed query: {str(e)}")

        # Get all embeddings for this transcript
        embeddings = db.execute(
            select(TranscriptEmbedding)
            .where(TranscriptEmbedding.transcript_id == transcript_id)
            .order_by(TranscriptEmbedding.segment_index)
        ).scalars().all()

        if not embeddings:
            return None  # Signal to use fallback

        # Calculate similarity for each embedding
        results = []
        for emb in embeddings:
            similarity = self.embedding_service.cosine_similarity(
                query_embedding,
                list(emb.embedding)
            )
            results.append({
                "start_time": emb.start_time,
                "text": emb.segment_text,
                "similarity": similarity
            })

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Get best match
        if not results:
            return {
                "timestamp": None,
                "confidence": "none",
                "matched_text": ""
            }

        best_match = results[0]
        confidence = self.embedding_service.similarity_to_confidence(best_match["similarity"])

        return {
            "timestamp": best_match["start_time"],
            "confidence": confidence,
            "matched_text": best_match["text"][:100] if best_match["text"] else ""
        }

    async def find_timestamp_async(
        self,
        query: str,
        segments: List[Dict[str, Any]],
        video_duration: Optional[float] = None,
        model: str = AIModels.SEEK_MODEL,
        transcript_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Find the best matching timestamp for a user query (async version).

        If transcript_id and db are provided, tries embedding search first.
        Falls back to LLM-based slot search if no embeddings exist.

        Args:
            query: Search query from user
            segments: Transcript segments (for LLM fallback)
            video_duration: Video duration in seconds
            model: LLM model to use for fallback
            transcript_id: UUID of transcript (for embedding search)
            db: Async database session (for embedding search)

        Returns:
            Dict with timestamp, confidence, and matched_text
        """
        if not query or not query.strip():
            raise SeekServiceError("Query cannot be empty")

        # Try embedding-based search first (if available)
        if transcript_id and db:
            try:
                result = await self.find_timestamp_with_embeddings_async(query, transcript_id, db)
                if result is not None:
                    return result
                # result is None means no embeddings, fall through to LLM
            except SeekServiceError:
                # Fall back to LLM search
                pass

        # Fallback: LLM-based slot search
        return self._find_timestamp_with_llm(query, segments, video_duration, model)

    def find_timestamp(
        self,
        query: str,
        segments: List[Dict[str, Any]],
        video_duration: Optional[float] = None,
        model: str = AIModels.SEEK_MODEL,
        transcript_id: Optional[UUID] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Find the best matching timestamp for a user query (sync version).

        If transcript_id and db are provided, tries embedding search first.
        Falls back to LLM-based slot search if no embeddings exist.

        Args:
            query: Search query from user
            segments: Transcript segments (for LLM fallback)
            video_duration: Video duration in seconds
            model: LLM model to use for fallback
            transcript_id: UUID of transcript (for embedding search)
            db: Database session (for embedding search)

        Returns:
            Dict with timestamp, confidence, and matched_text
        """
        if not query or not query.strip():
            raise SeekServiceError("Query cannot be empty")

        # Try embedding-based search first (if available)
        if transcript_id and db:
            try:
                result = self.find_timestamp_with_embeddings(query, transcript_id, db)
                if result is not None:
                    return result
                # result is None means no embeddings, fall through to LLM
            except SeekServiceError:
                # Fall back to LLM search
                pass

        # Fallback: LLM-based slot search
        return self._find_timestamp_with_llm(query, segments, video_duration, model)

    def _find_timestamp_with_llm(
        self,
        query: str,
        segments: List[Dict[str, Any]],
        video_duration: Optional[float] = None,
        model: str = AIModels.SEEK_MODEL
    ) -> Dict[str, Any]:
        """
        Find timestamp using LLM-based slot search (fallback method).

        Uses slot-based indexing to ensure full video coverage.
        """
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

        user_prompt = SEEK_USER_PROMPT_TEMPLATE.format(
            total_mins=total_mins,
            total_secs=total_secs,
            query=query,
            num_slots=len(search_index),
            index_text=index_text
        )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SEEK_SYSTEM_PROMPT},
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
