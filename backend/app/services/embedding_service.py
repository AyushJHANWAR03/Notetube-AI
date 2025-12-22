"""
Embedding Service for semantic search in video transcripts.
Uses OpenAI's text-embedding-3-small model to generate and search embeddings.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
import math

from openai import OpenAI

from app.core.config import settings


class EmbeddingServiceError(Exception):
    """Custom exception for Embedding service errors."""
    pass


class EmbeddingService:
    """
    Service for generating and searching transcript embeddings.

    Uses OpenAI's text-embedding-3-small for cost-effective semantic search.
    - 1536 dimensions
    - $0.02 per 1M tokens
    - Supports 100+ languages
    """

    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    BATCH_SIZE = 100  # OpenAI allows batching up to 2048 inputs

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Embedding service with lazy client initialization."""
        if api_key is None:
            api_key = settings.OPENAI_API_KEY

        if not api_key:
            raise EmbeddingServiceError("OPENAI_API_KEY environment variable not set")

        self._api_key = api_key
        self._client = None  # Lazy initialization to avoid fork issues

    @property
    def client(self) -> OpenAI:
        """Lazily initialize the OpenAI client to avoid fork() issues on macOS."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def generate_embeddings(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for transcript segments.

        Args:
            segments: List of transcript segments with 'text', 'start', 'duration' keys

        Returns:
            List of dicts with segment info and embedding vector:
            [{"segment_index": 0, "text": "...", "start": 0.5, "duration": 3.2, "embedding": [...]}, ...]
        """
        if not segments:
            return []

        # Extract text from segments
        texts = [seg.get('text', '').strip() for seg in segments]

        # Filter out empty texts but keep track of indices
        valid_indices = [i for i, t in enumerate(texts) if t]
        valid_texts = [texts[i] for i in valid_indices]

        if not valid_texts:
            return []

        # Generate embeddings in batches
        all_embeddings = []
        for i in range(0, len(valid_texts), self.BATCH_SIZE):
            batch_texts = valid_texts[i:i + self.BATCH_SIZE]

            try:
                response = self.client.embeddings.create(
                    input=batch_texts,
                    model=self.MODEL
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                raise EmbeddingServiceError(f"Failed to generate embeddings: {str(e)}")

        # Map embeddings back to original segment structure
        results = []
        embedding_idx = 0
        for i, seg in enumerate(segments):
            if i in valid_indices:
                results.append({
                    "segment_index": i,
                    "text": seg.get('text', '').strip(),
                    "start": seg.get('start', 0),
                    "duration": seg.get('duration', 0),
                    "embedding": all_embeddings[embedding_idx]
                })
                embedding_idx += 1

        return results

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query string

        Returns:
            Embedding vector (list of 1536 floats)
        """
        if not query or not query.strip():
            raise EmbeddingServiceError("Query cannot be empty")

        try:
            response = self.client.embeddings.create(
                input=query.strip(),
                model=self.MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            raise EmbeddingServiceError(f"Failed to embed query: {str(e)}")

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity score (0 to 1, higher is more similar)
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have the same length")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def similarity_to_confidence(similarity: float) -> str:
        """
        Convert similarity score to confidence level.

        Args:
            similarity: Cosine similarity score (0 to 1)

        Returns:
            Confidence level: "high", "medium", "low", or "none"
        """
        if similarity >= 0.75:
            return "high"
        elif similarity >= 0.55:
            return "medium"
        elif similarity >= 0.35:
            return "low"
        else:
            return "none"
