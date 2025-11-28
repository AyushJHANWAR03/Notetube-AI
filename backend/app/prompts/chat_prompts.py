"""
Prompts for chat functionality with video context.
"""

CHAT_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions about a video based on provided context.
You have access to the video's summary, chapter breakdowns, and main topics.

Guidelines:
- Be concise and direct in your answers
- Reference specific parts of the video when relevant
- If you don't have enough context to answer, say so clearly
- Stay focused on the video content - don't make up information
- Keep responses under 200 words unless more detail is explicitly requested"""

CHAT_USER_PROMPT_TEMPLATE = """Based on this video context:

{context}

User question: {message}

Provide a helpful, concise answer based on the video content."""

SUGGESTED_PROMPTS_SYSTEM_PROMPT = """You are an AI that generates 3 engaging questions users might want to ask about a video.
Generate questions that are:
- Specific to the video content
- Thought-provoking and useful
- Varied in scope (e.g., one about key concepts, one about practical applications, one about deeper understanding)

Return ONLY a JSON array of 3 strings, no other text."""

SUGGESTED_PROMPTS_USER_TEMPLATE = """Based on this video content:

Summary: {summary}

Topics: {topics}

Chapters:
{chapters}

Generate 3 engaging questions a viewer might want to ask about this video.
Return ONLY a JSON array like: ["Question 1?", "Question 2?", "Question 3?"]"""
