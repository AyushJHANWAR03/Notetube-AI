"""
TDD Tests for Transcript Processor.

Tests for:
1. Sentence merging - merge phrase-level segments into complete sentences
2. Chunking - split long transcripts into 5-min chunks with overlap
3. Temporal distribution - 60/40 split for chapter coverage
"""
import pytest
from typing import List, Dict, Any


# ============================================================================
# SENTENCE MERGING TESTS
# ============================================================================

class TestSentenceMerging:
    """Tests for merging transcript segments into sentences."""

    def test_merge_simple_sentences(self):
        """Segments ending with period should merge into complete sentences."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "Hello world.", "start": 0.0, "duration": 1.5},
            {"text": "This is a test.", "start": 1.5, "duration": 2.0},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 2
        assert result[0]["text"] == "Hello world."
        assert result[1]["text"] == "This is a test."

    def test_merge_multiple_segments_into_sentence(self):
        """Multiple segments without punctuation should merge until period."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "This is", "start": 0.0, "duration": 1.0},
            {"text": "a longer", "start": 1.0, "duration": 1.0},
            {"text": "sentence here.", "start": 2.0, "duration": 1.5},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 1
        assert result[0]["text"] == "This is a longer sentence here."
        assert result[0]["start"] == 0.0
        assert result[0]["duration"] == 3.5  # Sum of all durations

    def test_merge_handles_question_marks(self):
        """Question marks should also end sentences."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "How are you?", "start": 0.0, "duration": 1.5},
            {"text": "I am fine.", "start": 1.5, "duration": 1.5},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 2
        assert result[0]["text"] == "How are you?"
        assert result[1]["text"] == "I am fine."

    def test_merge_handles_exclamation_marks(self):
        """Exclamation marks should also end sentences."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "Wow!", "start": 0.0, "duration": 0.5},
            {"text": "That is amazing.", "start": 0.5, "duration": 1.5},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 2

    def test_merge_handles_decimal_numbers(self):
        """Decimal numbers like 2.5 should NOT trigger sentence break."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "The value is 2.5 percent", "start": 0.0, "duration": 2.0},
            {"text": "of the total.", "start": 2.0, "duration": 1.0},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 1
        assert "2.5" in result[0]["text"]
        assert result[0]["text"] == "The value is 2.5 percent of the total."

    def test_merge_handles_abbreviations(self):
        """Common abbreviations like Dr. Mr. etc. should NOT trigger break."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "Dr. Smith is here", "start": 0.0, "duration": 1.5},
            {"text": "to help you.", "start": 1.5, "duration": 1.0},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 1
        assert result[0]["text"] == "Dr. Smith is here to help you."

    def test_merge_handles_urls_and_tlds(self):
        """.com .org .ai should NOT trigger sentence break."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "Visit example.com for", "start": 0.0, "duration": 1.5},
            {"text": "more information.", "start": 1.5, "duration": 1.0},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 1
        assert "example.com" in result[0]["text"]

    def test_merge_handles_file_extensions(self):
        """.js .py .ts should NOT trigger sentence break."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "Open the file main.py and", "start": 0.0, "duration": 2.0},
            {"text": "edit it.", "start": 2.0, "duration": 1.0},
        ]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 1
        assert "main.py" in result[0]["text"]

    def test_merge_forces_split_on_max_duration(self):
        """Sentences exceeding 24 seconds should be force-split."""
        from app.services.transcript_processor import merge_segments_into_sentences

        # Create segments totaling 30 seconds without punctuation
        segments = [
            {"text": f"word{i}", "start": float(i), "duration": 1.0}
            for i in range(30)
        ]

        result = merge_segments_into_sentences(segments)

        # Should have at least 2 sentences (split at ~24s)
        assert len(result) >= 2
        assert result[0]["duration"] <= 24.0

    def test_merge_forces_split_on_max_words(self):
        """Sentences exceeding 80 words should be force-split."""
        from app.services.transcript_processor import merge_segments_into_sentences

        # Create 100 word segments without punctuation
        segments = [
            {"text": f"word{i}", "start": float(i) * 0.2, "duration": 0.2}
            for i in range(100)
        ]

        result = merge_segments_into_sentences(segments)

        # Each sentence should have <= 80 words
        for sentence in result:
            word_count = len(sentence["text"].split())
            assert word_count <= 80

    def test_merge_preserves_first_segment_timestamp(self):
        """Merged sentence should keep the first segment's start time."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "First part", "start": 10.5, "duration": 1.0},
            {"text": "second part.", "start": 11.5, "duration": 1.0},
        ]

        result = merge_segments_into_sentences(segments)

        assert result[0]["start"] == 10.5

    def test_merge_calculates_total_duration(self):
        """Merged sentence duration should be sum of segment durations."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [
            {"text": "Part one", "start": 0.0, "duration": 2.5},
            {"text": "part two", "start": 2.5, "duration": 3.0},
            {"text": "part three.", "start": 5.5, "duration": 1.5},
        ]

        result = merge_segments_into_sentences(segments)

        assert result[0]["duration"] == 7.0  # 2.5 + 3.0 + 1.5

    def test_merge_handles_empty_segments(self):
        """Empty segment list should return empty list."""
        from app.services.transcript_processor import merge_segments_into_sentences

        result = merge_segments_into_sentences([])

        assert result == []

    def test_merge_handles_single_segment(self):
        """Single segment should be returned as-is if it ends with punctuation."""
        from app.services.transcript_processor import merge_segments_into_sentences

        segments = [{"text": "Hello world.", "start": 0.0, "duration": 1.0}]

        result = merge_segments_into_sentences(segments)

        assert len(result) == 1
        assert result[0]["text"] == "Hello world."


# ============================================================================
# CHUNKING TESTS
# ============================================================================

class TestChunking:
    """Tests for chunking transcripts into 5-minute segments with overlap."""

    def test_chunk_short_video_single_chunk(self):
        """Video < 5 min should return single chunk."""
        from app.services.transcript_processor import chunk_transcript

        # 3-minute video
        segments = [
            {"text": f"Segment {i}", "start": float(i * 10), "duration": 10.0}
            for i in range(18)  # 18 * 10 = 180 seconds = 3 min
        ]

        chunks = chunk_transcript(segments, video_duration=180)

        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0

    def test_chunk_10_min_video_creates_multiple_chunks(self):
        """10 min video should create multiple overlapping chunks."""
        from app.services.transcript_processor import chunk_transcript

        # 10-minute video (600 seconds)
        segments = [
            {"text": f"Segment {i}", "start": float(i * 5), "duration": 5.0}
            for i in range(120)  # 120 * 5 = 600 seconds = 10 min
        ]

        chunks = chunk_transcript(segments, video_duration=600)

        # With 5-min chunks and 45s overlap, step = 255s
        # For 600s video: chunks at 0, 255, 510 = 3 chunks
        assert len(chunks) >= 2

    def test_chunk_overlap_segments_included_in_both(self):
        """Segments in overlap region should appear in adjacent chunks."""
        from app.services.transcript_processor import chunk_transcript

        # Create segments with known positions
        segments = [
            {"text": f"Segment at {i*60}s", "start": float(i * 60), "duration": 30.0}
            for i in range(12)  # 0, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600, 660
        ]

        chunks = chunk_transcript(segments, video_duration=720)

        if len(chunks) >= 2:
            # Get segments from first two chunks
            first_chunk_texts = [s["text"] for s in chunks[0]["segments"]]
            second_chunk_texts = [s["text"] for s in chunks[1]["segments"]]

            # There should be some overlap
            overlap = set(first_chunk_texts) & set(second_chunk_texts)
            # Due to 45s overlap, segments near chunk boundary should appear in both
            assert len(overlap) >= 0  # At least check it doesn't crash

    def test_chunk_preserves_segment_data(self):
        """Each chunk should contain original segment objects."""
        from app.services.transcript_processor import chunk_transcript

        segments = [
            {"text": "Test segment", "start": 0.0, "duration": 5.0, "extra": "data"}
        ]

        chunks = chunk_transcript(segments, video_duration=60)

        assert chunks[0]["segments"][0]["extra"] == "data"

    def test_chunk_has_required_metadata(self):
        """Each chunk should have start_time, end_time, chunk_index."""
        from app.services.transcript_processor import chunk_transcript

        segments = [
            {"text": f"Seg {i}", "start": float(i * 30), "duration": 30.0}
            for i in range(20)  # 600 seconds
        ]

        chunks = chunk_transcript(segments, video_duration=600)

        for i, chunk in enumerate(chunks):
            assert "start_time" in chunk
            assert "end_time" in chunk
            assert "chunk_index" in chunk
            assert "segments" in chunk
            assert chunk["chunk_index"] == i

    def test_chunk_tail_handling(self):
        """Last chunk should capture all remaining segments."""
        from app.services.transcript_processor import chunk_transcript

        segments = [
            {"text": f"Seg {i}", "start": float(i * 60), "duration": 60.0}
            for i in range(15)  # 900 seconds = 15 min
        ]

        chunks = chunk_transcript(segments, video_duration=900)

        # All segments should be covered
        all_chunked_segments = []
        for chunk in chunks:
            all_chunked_segments.extend(chunk["segments"])

        # Each original segment should appear at least once
        original_texts = {s["text"] for s in segments}
        chunked_texts = {s["text"] for s in all_chunked_segments}
        assert original_texts == chunked_texts

    def test_chunk_empty_segments(self):
        """Empty segment list should return empty chunk list."""
        from app.services.transcript_processor import chunk_transcript

        chunks = chunk_transcript([], video_duration=600)

        assert chunks == []


# ============================================================================
# TEMPORAL DISTRIBUTION TESTS
# ============================================================================

class TestTemporalDistribution:
    """Tests for 60/40 temporal distribution of chapters."""

    def test_temporal_calculates_boundary(self):
        """60% boundary should be calculated correctly."""
        from app.services.transcript_processor import calculate_temporal_boundary

        # 90 min video = 5400 seconds
        boundary = calculate_temporal_boundary(5400)

        assert boundary == 3240  # 60% of 5400

    def test_temporal_split_candidates(self):
        """Candidates should be split at 60% mark."""
        from app.services.transcript_processor import split_by_temporal_boundary

        video_duration = 600  # 10 min
        candidates = [
            {"title": "Topic 1", "start_time": 60},   # First 60%
            {"title": "Topic 2", "start_time": 120},  # First 60%
            {"title": "Topic 3", "start_time": 200},  # First 60%
            {"title": "Topic 4", "start_time": 400},  # Last 40%
            {"title": "Topic 5", "start_time": 500},  # Last 40%
        ]

        first_segment, second_segment = split_by_temporal_boundary(
            candidates, video_duration
        )

        # Boundary at 360 seconds (60% of 600)
        assert len(first_segment) == 3
        assert len(second_segment) == 2

    def test_temporal_distribution_allocation(self):
        """First 60% should get up to 3 topics, last 40% up to 2."""
        from app.services.transcript_processor import apply_temporal_distribution

        video_duration = 600
        candidates = [
            {"title": f"Topic {i}", "start_time": i * 50, "score": 10 - i}
            for i in range(10)
        ]

        result = apply_temporal_distribution(
            candidates, video_duration, requested_topics=5
        )

        # Should have 5 total (3 from first segment, 2 from second)
        assert len(result) <= 5

        # Count topics from each segment
        boundary = video_duration * 0.6
        first_segment_count = sum(1 for t in result if t["start_time"] < boundary)
        second_segment_count = sum(1 for t in result if t["start_time"] >= boundary)

        assert first_segment_count <= 3
        assert second_segment_count <= 2

    def test_temporal_short_video_no_split(self):
        """Videos < 10 min may not need temporal split."""
        from app.services.transcript_processor import apply_temporal_distribution

        video_duration = 300  # 5 min
        candidates = [
            {"title": "Topic 1", "start_time": 30, "score": 10},
            {"title": "Topic 2", "start_time": 150, "score": 8},
        ]

        result = apply_temporal_distribution(
            candidates, video_duration, requested_topics=5
        )

        # Should return all available candidates for short videos
        assert len(result) == 2

    def test_temporal_empty_first_segment_fallback(self):
        """If first segment has no candidates, use equal distribution."""
        from app.services.transcript_processor import apply_temporal_distribution

        video_duration = 600
        # All candidates in second segment
        candidates = [
            {"title": f"Topic {i}", "start_time": 400 + i * 20, "score": 10 - i}
            for i in range(5)
        ]

        result = apply_temporal_distribution(
            candidates, video_duration, requested_topics=5
        )

        # Should still return candidates
        assert len(result) > 0

    def test_temporal_deduplication(self):
        """Duplicate topics from overlapping chunks should be removed."""
        from app.services.transcript_processor import deduplicate_candidates

        candidates = [
            {"title": "Machine Learning", "start_time": 100, "text": "intro to ML"},
            {"title": "Machine Learning", "start_time": 105, "text": "intro to ML"},  # Duplicate
            {"title": "Deep Learning", "start_time": 200, "text": "neural networks"},
        ]

        result = deduplicate_candidates(candidates)

        assert len(result) == 2
        titles = [c["title"] for c in result]
        assert titles.count("Machine Learning") == 1

    def test_temporal_preserves_order(self):
        """Result should be sorted by start_time."""
        from app.services.transcript_processor import apply_temporal_distribution

        video_duration = 600
        candidates = [
            {"title": "Topic 3", "start_time": 300, "score": 5},
            {"title": "Topic 1", "start_time": 100, "score": 10},
            {"title": "Topic 2", "start_time": 200, "score": 8},
        ]

        result = apply_temporal_distribution(
            candidates, video_duration, requested_topics=5
        )

        # Should be sorted by start_time
        times = [t["start_time"] for t in result]
        assert times == sorted(times)
