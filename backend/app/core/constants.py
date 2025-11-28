"""
Centralized constants for the application.
"""


class VideoStatus:
    """Video processing status constants."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class JobStatus:
    """Background job status constants."""
    PENDING = "PENDING"
    FETCHING_TRANSCRIPT = "FETCHING_TRANSCRIPT"
    GENERATING_NOTES = "GENERATING_NOTES"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobType:
    """Background job type constants."""
    VIDEO_PROCESS = "VIDEO_PROCESS"
    PDF_EXPORT = "PDF_EXPORT"


# AI Model defaults
class AIModels:
    """Default AI model configurations."""
    NOTES_MODEL = "gpt-4o-mini"
    CHAPTERS_MODEL = "gpt-4o-mini"
    SEEK_MODEL = "gpt-3.5-turbo"
    REWRITE_MODEL = "gpt-3.5-turbo"
    TRANSLITERATION_MODEL = "gpt-3.5-turbo"


# Token limits
class TokenLimits:
    """Token limit configurations."""
    NOTES_MAX_CHARS = 480000  # ~120k tokens for GPT-4o-mini
    STRUCTURED_NOTES_MAX_CHARS = 100000  # ~25k tokens
    TRANSLITERATION_BATCH_SIZE = 100
    TRANSLITERATION_MAX_PARALLEL = 4


# Video constraints
class VideoConstraints:
    """Video processing constraints."""
    MAX_DURATION_SECONDS = 7200  # 2 hours
