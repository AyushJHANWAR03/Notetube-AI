"""
Transcript Processor for NoteTube AI.

Provides three key features:
1. Sentence Merging - merge phrase-level segments into complete sentences
2. Chunking - split long transcripts into 5-min chunks with 45s overlap
3. Temporal Distribution - 60/40 split for chapter coverage

Based on TLDW's proven algorithms, adapted for Python.
"""
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class TranscriptConfig:
    """Configuration constants for transcript processing."""

    # Sentence merging thresholds
    MAX_SENTENCE_DURATION_SECONDS: float = 24.0
    MAX_SENTENCE_WORDS: int = 80
    MAX_SEGMENTS_PER_SENTENCE: int = 20

    # Common abbreviations that don't end sentences
    ABBREVIATIONS: set = None

    # TLDs and file extensions that don't end sentences
    FALSE_PERIOD_SUFFIXES: set = None

    # Chunking parameters
    CHUNK_DURATION_SECONDS: int = 5 * 60  # 5 minutes
    CHUNK_OVERLAP_SECONDS: int = 45
    MIN_CHUNK_STEP_SECONDS: int = 60

    # Temporal distribution
    TEMPORAL_BOUNDARY_RATIO: float = 0.6  # 60% mark
    # For NoteTube chapters: use all unique topics (not limited like TLDW highlights)
    # Set to None to disable limits and show all chapters
    FIRST_SEGMENT_MAX_TOPICS: int = None  # No limit - show all
    SECOND_SEGMENT_MAX_TOPICS: int = None  # No limit - show all

    def __post_init__(self):
        if self.ABBREVIATIONS is None:
            self.ABBREVIATIONS = {
                'dr', 'mr', 'mrs', 'ms', 'prof', 'vs', 'etc', 'inc', 'ltd',
                'jr', 'sr', 'st', 'ave', 'blvd', 'apt', 'no', 'vol', 'pg',
                'fig', 'ch', 'sec', 'dept', 'govt', 'univ', 'corp', 'co',
                'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
            }
        if self.FALSE_PERIOD_SUFFIXES is None:
            self.FALSE_PERIOD_SUFFIXES = {
                '.com', '.org', '.net', '.ai', '.io', '.co', '.edu', '.gov',
                '.js', '.ts', '.py', '.rb', '.go', '.rs', '.cpp', '.c', '.h',
                '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.md',
                '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt',
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', '.mp3'
            }


# Global config instance
CONFIG = TranscriptConfig()


def is_sentence_ending_period(text: str, position: int) -> bool:
    """
    Check if a period at the given position is a sentence-ending period.

    Filters out false positives:
    - Decimal numbers: 2.5, 3.14
    - TLDs: .com, .org
    - File extensions: .js, .py
    - Abbreviations: Dr., Mr., etc.
    """
    if position < 0 or position >= len(text):
        return False

    if text[position] != '.':
        return False

    # Check for decimal numbers (digit before AND after)
    if position > 0 and position < len(text) - 1:
        char_before = text[position - 1]
        char_after = text[position + 1]
        if char_before.isdigit() and char_after.isdigit():
            return False

    # Check for TLDs and file extensions
    # Look for pattern like "example.com" or "file.py"
    # Find the start of the potential extension
    ext_start = position
    while ext_start > 0 and text[ext_start - 1].isalnum():
        ext_start -= 1

    # Find the end of the potential extension
    ext_end = position + 1
    while ext_end < len(text) and text[ext_end].isalnum():
        ext_end += 1

    potential_ext = text[position:ext_end].lower()
    if potential_ext in CONFIG.FALSE_PERIOD_SUFFIXES:
        return False

    # Check for abbreviations
    # Find the word before the period
    word_start = position - 1
    while word_start >= 0 and text[word_start].isalpha():
        word_start -= 1
    word_start += 1

    word_before_period = text[word_start:position].lower()
    if word_before_period in CONFIG.ABBREVIATIONS:
        return False

    return True


def find_sentence_boundary(text: str) -> int:
    """
    Find the position of a sentence-ending punctuation mark.

    Returns -1 if no boundary found.
    """
    for i, char in enumerate(text):
        if char in '?!':
            return i
        if char == '.' and is_sentence_ending_period(text, i):
            return i
    return -1


def merge_segments_into_sentences(
    segments: List[Dict[str, Any]],
    config: TranscriptConfig = None
) -> List[Dict[str, Any]]:
    """
    Merge transcript segments into complete sentences.

    Algorithm:
    1. Accumulate segments until sentence-ending punctuation
    2. Handle false positives (decimals, URLs, abbreviations)
    3. Force-split if duration/word count thresholds exceeded

    Args:
        segments: List of segment dicts with text, start, duration
        config: Optional custom configuration

    Returns:
        List of merged sentence dicts with text, start, duration
    """
    if not segments:
        return []

    if config is None:
        config = CONFIG

    sentences = []
    current_texts = []
    current_start = None
    current_duration = 0.0
    current_segment_count = 0

    def finalize_sentence():
        """Finalize the current accumulated sentence."""
        nonlocal current_texts, current_start, current_duration, current_segment_count

        if current_texts:
            merged_text = " ".join(current_texts)
            sentences.append({
                "text": merged_text,
                "start": current_start,
                "duration": current_duration
            })

        current_texts = []
        current_start = None
        current_duration = 0.0
        current_segment_count = 0

    def should_force_split() -> bool:
        """Check if we should force-split due to thresholds."""
        if current_duration >= config.MAX_SENTENCE_DURATION_SECONDS:
            return True
        if current_segment_count >= config.MAX_SEGMENTS_PER_SENTENCE:
            return True
        word_count = sum(len(t.split()) for t in current_texts)
        if word_count >= config.MAX_SENTENCE_WORDS:
            return True
        return False

    for segment in segments:
        text = segment.get("text", "").strip()
        start = segment.get("start", 0.0)
        duration = segment.get("duration", 0.0)

        if not text:
            continue

        # Initialize start time for new sentence
        if current_start is None:
            current_start = start

        # Check if we need to force-split before adding
        if should_force_split():
            finalize_sentence()
            current_start = start

        # Add segment to current accumulation
        current_texts.append(text)
        current_duration += duration
        current_segment_count += 1

        # Check for sentence boundary in the accumulated text
        combined_text = " ".join(current_texts)
        boundary_pos = find_sentence_boundary(combined_text)

        if boundary_pos >= 0:
            # Found a sentence boundary
            # Check if it's at the end of the text (complete sentence)
            remaining_after_boundary = combined_text[boundary_pos + 1:].strip()

            if not remaining_after_boundary:
                # Sentence ends cleanly
                finalize_sentence()
            else:
                # There's text after the boundary - need to handle carryover
                # For simplicity, just finalize the whole thing
                # (In production, you'd split and carry over)
                finalize_sentence()

    # Finalize any remaining text
    if current_texts:
        finalize_sentence()

    # Apply safety net: break any remaining long sentences
    final_sentences = []
    for sentence in sentences:
        if sentence["duration"] > config.MAX_SENTENCE_DURATION_SECONDS:
            # Split into chunks
            words = sentence["text"].split()
            chunk_size = config.MAX_SENTENCE_WORDS
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_ratio = len(chunk_words) / len(words) if words else 1
                final_sentences.append({
                    "text": " ".join(chunk_words),
                    "start": sentence["start"] + (sentence["duration"] * i / len(words) if words else 0),
                    "duration": sentence["duration"] * chunk_ratio
                })
        else:
            final_sentences.append(sentence)

    return final_sentences


# ============================================================================
# CHUNKING
# ============================================================================

def chunk_transcript(
    segments: List[Dict[str, Any]],
    video_duration: float,
    chunk_duration: int = None,
    overlap: int = None,
    config: TranscriptConfig = None
) -> List[Dict[str, Any]]:
    """
    Split transcript into overlapping chunks for parallel processing.

    Algorithm:
    1. Use sliding window with overlap
    2. Collect segments within each window
    3. Handle tail chunk for remaining segments

    Args:
        segments: List of segment dicts
        video_duration: Total video duration in seconds
        chunk_duration: Duration of each chunk (default: 5 min)
        overlap: Overlap between chunks (default: 45s)
        config: Optional custom configuration

    Returns:
        List of chunk dicts with segments, start_time, end_time, chunk_index
    """
    if not segments:
        return []

    if config is None:
        config = CONFIG

    if chunk_duration is None:
        chunk_duration = config.CHUNK_DURATION_SECONDS
    if overlap is None:
        overlap = config.CHUNK_OVERLAP_SECONDS

    # Ensure minimum chunk duration
    effective_duration = max(180, chunk_duration)  # At least 3 minutes
    effective_overlap = min(max(overlap, 45), effective_duration // 2)
    step = max(config.MIN_CHUNK_STEP_SECONDS, effective_duration - effective_overlap)

    # If video is shorter than chunk duration, return single chunk
    if video_duration <= effective_duration:
        return [{
            "chunk_index": 0,
            "start_time": 0.0,
            "end_time": video_duration,
            "segments": list(segments)
        }]

    chunks = []
    chunk_index = 0
    window_start = 0.0

    while window_start < video_duration:
        window_end = min(window_start + effective_duration, video_duration)

        # Collect segments in this window
        chunk_segments = [
            seg for seg in segments
            if window_start <= seg.get("start", 0) < window_end
        ]

        if chunk_segments:
            chunks.append({
                "chunk_index": chunk_index,
                "start_time": window_start,
                "end_time": window_end,
                "segments": chunk_segments
            })
            chunk_index += 1

        window_start += step

        # Stop if we've covered the whole video
        if window_start >= video_duration:
            break

    # Ensure tail is captured - if last segment isn't in any chunk
    if segments:
        last_segment_start = segments[-1].get("start", 0)
        last_chunk_end = chunks[-1]["end_time"] if chunks else 0

        if last_segment_start >= last_chunk_end:
            # Add a tail chunk
            tail_segments = [
                seg for seg in segments
                if seg.get("start", 0) >= last_chunk_end - overlap
            ]
            if tail_segments:
                chunks.append({
                    "chunk_index": chunk_index,
                    "start_time": last_chunk_end - overlap,
                    "end_time": video_duration,
                    "segments": tail_segments
                })

    return chunks


# ============================================================================
# TEMPORAL DISTRIBUTION
# ============================================================================

def calculate_temporal_boundary(video_duration: float, ratio: float = 0.6) -> float:
    """Calculate the temporal boundary (default: 60% of video duration)."""
    return video_duration * ratio


def split_by_temporal_boundary(
    candidates: List[Dict[str, Any]],
    video_duration: float,
    boundary_ratio: float = 0.6
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Split candidates into first segment (before boundary) and second segment (after).

    Args:
        candidates: List of candidate topics with start_time
        video_duration: Total video duration
        boundary_ratio: Where to split (default: 0.6 = 60%)

    Returns:
        Tuple of (first_segment_candidates, second_segment_candidates)
    """
    boundary = video_duration * boundary_ratio

    first_segment = [c for c in candidates if c.get("start_time", 0) < boundary]
    second_segment = [c for c in candidates if c.get("start_time", 0) >= boundary]

    return first_segment, second_segment


def deduplicate_candidates(
    candidates: List[Dict[str, Any]],
    key: str = "title"
) -> List[Dict[str, Any]]:
    """
    Remove duplicate candidates based on a key field.

    Keeps the first occurrence of each unique value.
    """
    seen = set()
    result = []

    for candidate in candidates:
        value = candidate.get(key, "")
        if value not in seen:
            seen.add(value)
            result.append(candidate)

    return result


def apply_temporal_distribution(
    candidates: List[Dict[str, Any]],
    video_duration: float,
    requested_topics: int = 5,
    config: TranscriptConfig = None
) -> List[Dict[str, Any]]:
    """
    Apply 60/40 temporal distribution to ensure full video coverage.

    Algorithm:
    1. Split candidates at 60% boundary
    2. Allocate up to 3 topics from first 60%
    3. Allocate up to 2 topics from last 40%
    4. Sort by start_time

    Args:
        candidates: List of candidate topics with start_time and optionally score
        video_duration: Total video duration
        requested_topics: Total number of topics to return
        config: Optional custom configuration

    Returns:
        List of selected topics, sorted by start_time
    """
    if not candidates:
        return []

    if config is None:
        config = CONFIG

    # For short videos (< 5 min), just return top candidates
    if video_duration < 300:
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        result = sorted_candidates[:requested_topics]
        return sorted(result, key=lambda x: x.get("start_time", 0))

    # Split by temporal boundary
    first_segment, second_segment = split_by_temporal_boundary(
        candidates, video_duration, config.TEMPORAL_BOUNDARY_RATIO
    )

    # Calculate allocation - None means no limit (show all chapters)
    if config.FIRST_SEGMENT_MAX_TOPICS is None and config.SECOND_SEGMENT_MAX_TOPICS is None:
        # No limits - return all unique candidates sorted by time
        result = sorted(candidates, key=lambda x: x.get("start_time", 0))
        return result

    # Legacy behavior with limits (for TLDW-style highlights)
    first_max = config.FIRST_SEGMENT_MAX_TOPICS or len(first_segment)
    second_max = config.SECOND_SEGMENT_MAX_TOPICS or len(second_segment)
    first_target = min(first_max, requested_topics)
    second_target = min(second_max, requested_topics - first_target)

    # Handle edge case: no candidates in first segment
    if not first_segment:
        # Use all from second segment
        sorted_second = sorted(second_segment, key=lambda x: x.get("score", 0), reverse=True)
        result = sorted_second[:requested_topics]
        return sorted(result, key=lambda x: x.get("start_time", 0))

    # Handle edge case: no candidates in second segment
    if not second_segment:
        sorted_first = sorted(first_segment, key=lambda x: x.get("score", 0), reverse=True)
        result = sorted_first[:requested_topics]
        return sorted(result, key=lambda x: x.get("start_time", 0))

    # Select from each segment based on score
    sorted_first = sorted(first_segment, key=lambda x: x.get("score", 0), reverse=True)
    sorted_second = sorted(second_segment, key=lambda x: x.get("score", 0), reverse=True)

    selected_first = sorted_first[:first_target]
    selected_second = sorted_second[:second_target]

    # Combine and sort by time
    result = selected_first + selected_second
    result = sorted(result, key=lambda x: x.get("start_time", 0))

    return result


# ============================================================================
# TRANSCRIPT PROCESSOR CLASS
# ============================================================================

class TranscriptProcessor:
    """
    Main class for processing transcripts.

    Combines sentence merging, chunking, and temporal distribution.
    """

    def __init__(self, config: TranscriptConfig = None):
        self.config = config or TranscriptConfig()

    def merge_sentences(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge segments into sentences."""
        return merge_segments_into_sentences(segments, self.config)

    def chunk(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float
    ) -> List[Dict[str, Any]]:
        """Chunk transcript into overlapping windows."""
        return chunk_transcript(segments, video_duration, config=self.config)

    def apply_distribution(
        self,
        candidates: List[Dict[str, Any]],
        video_duration: float,
        requested_topics: int = 5
    ) -> List[Dict[str, Any]]:
        """Apply temporal distribution to candidates."""
        return apply_temporal_distribution(
            candidates, video_duration, requested_topics, self.config
        )

    def process(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float
    ) -> Dict[str, Any]:
        """
        Full processing pipeline.

        1. Merge segments into sentences
        2. Chunk for parallel processing

        Returns dict with merged_segments, chunks
        """
        merged = self.merge_sentences(segments)
        chunks = self.chunk(merged, video_duration)

        return {
            "merged_segments": merged,
            "chunks": chunks,
            "original_segment_count": len(segments),
            "merged_segment_count": len(merged),
            "chunk_count": len(chunks)
        }
