"""
Centralized prompts for all AI services.
"""
from app.prompts.notes_prompts import (
    NOTES_SYSTEM_PROMPT,
    NOTES_USER_PROMPT_TEMPLATE,
)
from app.prompts.chapters_prompts import (
    CHAPTERS_SYSTEM_PROMPT,
    CHAPTERS_USER_PROMPT_TEMPLATE,
)
from app.prompts.structured_notes_prompts import (
    STRUCTURED_NOTES_SYSTEM_PROMPT,
    STRUCTURED_NOTES_USER_PROMPT_TEMPLATE,
)
from app.prompts.transliteration_prompts import (
    TRANSLITERATION_SYSTEM_PROMPT,
    TRANSLITERATION_USER_PROMPT_TEMPLATE,
)
from app.prompts.rewrite_prompts import REWRITE_PROMPTS
from app.prompts.seek_prompts import (
    SEEK_SYSTEM_PROMPT,
    SEEK_USER_PROMPT_TEMPLATE,
)
from app.prompts.chat_prompts import (
    CHAT_SYSTEM_PROMPT,
    CHAT_USER_PROMPT_TEMPLATE,
    SUGGESTED_PROMPTS_SYSTEM_PROMPT,
    SUGGESTED_PROMPTS_USER_TEMPLATE,
)
from app.prompts.chunk_topics_prompts import (
    CHUNK_TOPICS_SYSTEM_PROMPT,
    CHUNK_TOPICS_USER_PROMPT_TEMPLATE,
)

__all__ = [
    # Notes generation
    "NOTES_SYSTEM_PROMPT",
    "NOTES_USER_PROMPT_TEMPLATE",
    # Chapters generation
    "CHAPTERS_SYSTEM_PROMPT",
    "CHAPTERS_USER_PROMPT_TEMPLATE",
    # Structured notes
    "STRUCTURED_NOTES_SYSTEM_PROMPT",
    "STRUCTURED_NOTES_USER_PROMPT_TEMPLATE",
    # Transliteration
    "TRANSLITERATION_SYSTEM_PROMPT",
    "TRANSLITERATION_USER_PROMPT_TEMPLATE",
    # Rewrite styles
    "REWRITE_PROMPTS",
    # Seek/search
    "SEEK_SYSTEM_PROMPT",
    "SEEK_USER_PROMPT_TEMPLATE",
    # Chat
    "CHAT_SYSTEM_PROMPT",
    "CHAT_USER_PROMPT_TEMPLATE",
    "SUGGESTED_PROMPTS_SYSTEM_PROMPT",
    "SUGGESTED_PROMPTS_USER_TEMPLATE",
    # Chunk topics (for map-reduce chapter generation)
    "CHUNK_TOPICS_SYSTEM_PROMPT",
    "CHUNK_TOPICS_USER_PROMPT_TEMPLATE",
]
