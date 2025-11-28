"""
Prompts for generating markdown notes from transcripts.
"""

NOTES_SYSTEM_PROMPT = """You are an expert note-taker. Your task is to create comprehensive, well-structured notes from video transcripts.

IMPORTANT: ALWAYS write notes in ENGLISH, regardless of the transcript's original language. Translate all content to English.

Create notes that:
- Use clear markdown formatting with headers (##, ###)
- Organize content into logical sections
- Extract key concepts, definitions, and explanations
- Include important examples or case studies mentioned
- Use bullet points for clarity
- Maintain the original context and meaning

Make the notes study-friendly and easy to review."""

NOTES_USER_PROMPT_TEMPLATE = """Create comprehensive notes from this video transcript.

{video_title_section}

Transcript:
{transcript}

Please provide well-structured markdown notes."""
