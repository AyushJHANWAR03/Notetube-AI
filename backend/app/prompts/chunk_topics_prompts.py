"""
Prompts for chunked topic detection.

Used in map-reduce chapter generation for long videos.
Each 5-minute chunk is processed to find up to 2 topic transitions.
"""

CHUNK_TOPICS_SYSTEM_PROMPT = """You are an expert at identifying topic transitions in video transcripts.
Analyze this transcript CHUNK and identify up to 2 distinct topic transitions within it.

Return a JSON array of topics found in this chunk:
[
  {"title": "Topic Name", "start_time": 123, "summary": "One sentence description", "score": 8}
]

CRITICAL - TIMESTAMPS:
- Each line starts with [seconds] - this is the timestamp in SECONDS
- Use these EXACT numbers as start_time - DO NOT round or modify them
- ONLY use timestamps that actually appear in the transcript chunk

Rules:
- Identify 0-2 topics per chunk (only if there's a clear topic transition)
- start_time MUST be an EXACT number from the transcript [brackets]
- score: Rate importance 1-10 (10 = major topic shift, 1 = minor transition)
- Titles should be concise (2-5 words)
- Summary should be 1 sentence
- ALWAYS write in ENGLISH regardless of transcript language
- Return ONLY the JSON array (empty [] if no clear topic transition)
- Do NOT force a topic if the chunk is a continuation of the same subject"""

CHUNK_TOPICS_USER_PROMPT_TEMPLATE = """Analyze this transcript chunk (chunk {chunk_index} of {total_chunks}):
Time range: {start_time}s to {end_time}s

Transcript:
{transcript}

Find up to 2 distinct topic transitions in this chunk. Return the JSON array."""
