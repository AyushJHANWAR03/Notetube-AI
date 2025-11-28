"""
Video Processing Service for handling video creation, status updates, and all related DB operations.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.video import Video
from app.models.transcript import Transcript
from app.models.notes import Notes
from app.models.job import Job
from app.core.constants import VideoStatus, JobStatus, JobType


class VideoProcessingServiceError(Exception):
    """Custom exception for video processing service errors."""
    pass


class VideoProcessingService:
    """Service for video processing database operations."""

    # Video status constants (using centralized constants)
    STATUS_PENDING = VideoStatus.PENDING
    STATUS_PROCESSING = VideoStatus.PROCESSING
    STATUS_READY = VideoStatus.READY
    STATUS_FAILED = VideoStatus.FAILED

    # Job type constants
    JOB_TYPE_VIDEO_PROCESS = JobType.VIDEO_PROCESS
    JOB_TYPE_PDF_EXPORT = JobType.PDF_EXPORT

    # Job status constants
    JOB_PENDING = JobStatus.PENDING
    JOB_FETCHING_TRANSCRIPT = JobStatus.FETCHING_TRANSCRIPT
    JOB_GENERATING_NOTES = JobStatus.GENERATING_NOTES
    JOB_COMPLETED = JobStatus.COMPLETED
    JOB_FAILED = JobStatus.FAILED

    async def create_video(
        self,
        user_id: UUID,
        youtube_video_id: str,
        original_url: str,
        db: AsyncSession,
        title: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ) -> Video:
        """
        Create a new video record.

        Args:
            user_id: User's UUID
            youtube_video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")
            original_url: Original YouTube URL submitted by user
            db: Database session
            title: Video title (optional, can be updated later)
            thumbnail_url: Thumbnail URL (optional)
            duration_seconds: Video duration in seconds (optional)

        Returns:
            Created Video object
        """
        video = Video(
            user_id=user_id,
            youtube_video_id=youtube_video_id,
            original_url=original_url,
            title=title,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration_seconds,
            status=self.STATUS_PENDING
        )
        db.add(video)
        await db.commit()
        await db.refresh(video)
        return video

    async def get_video_by_id(
        self,
        video_id: UUID,
        db: AsyncSession,
        include_relations: bool = False
    ) -> Optional[Video]:
        """
        Get video by ID.

        Args:
            video_id: Video's UUID
            db: Database session
            include_relations: Whether to eagerly load transcript, notes, jobs

        Returns:
            Video object or None if not found
        """
        query = select(Video).where(Video.id == video_id)

        if include_relations:
            query = query.options(
                selectinload(Video.transcript),
                selectinload(Video.notes),
                selectinload(Video.jobs)
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_video_by_youtube_id(
        self,
        user_id: UUID,
        youtube_video_id: str,
        db: AsyncSession
    ) -> Optional[Video]:
        """
        Get video by YouTube video ID for a specific user.

        Args:
            user_id: User's UUID
            youtube_video_id: YouTube video ID
            db: Database session

        Returns:
            Video object or None if not found
        """
        result = await db.execute(
            select(Video).where(
                Video.user_id == user_id,
                Video.youtube_video_id == youtube_video_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_videos(
        self,
        user_id: UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        exclude_failed: bool = True
    ) -> List[Video]:
        """
        Get all videos for a user.

        Args:
            user_id: User's UUID
            db: Database session
            limit: Maximum number of videos to return
            offset: Number of videos to skip
            status: Filter by status (optional)
            exclude_failed: Whether to exclude failed videos (default True)

        Returns:
            List of Video objects
        """
        query = select(Video).where(Video.user_id == user_id)

        if status:
            query = query.where(Video.status == status)
        elif exclude_failed:
            # Exclude failed videos by default (unless specific status filter is used)
            query = query.where(Video.status != self.STATUS_FAILED)

        query = query.order_by(Video.created_at.desc()).limit(limit).offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_video_status(
        self,
        video_id: UUID,
        status: str,
        db: AsyncSession,
        failure_reason: Optional[str] = None
    ) -> Optional[Video]:
        """
        Update video processing status.

        Args:
            video_id: Video's UUID
            status: New status (PENDING, PROCESSING, READY, FAILED)
            db: Database session
            failure_reason: Reason for failure (only for FAILED status)

        Returns:
            Updated Video object or None if not found
        """
        video = await self.get_video_by_id(video_id, db)
        if not video:
            return None

        video.status = status
        if status == self.STATUS_FAILED:
            video.failure_reason = failure_reason
        elif status == self.STATUS_READY:
            video.processed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(video)
        return video

    async def update_video_metadata(
        self,
        video_id: UUID,
        db: AsyncSession,
        title: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ) -> Optional[Video]:
        """
        Update video metadata after fetching from YouTube.

        Args:
            video_id: Video's UUID
            db: Database session
            title: Video title
            thumbnail_url: Thumbnail URL
            duration_seconds: Video duration

        Returns:
            Updated Video object or None if not found
        """
        video = await self.get_video_by_id(video_id, db)
        if not video:
            return None

        if title is not None:
            video.title = title
        if thumbnail_url is not None:
            video.thumbnail_url = thumbnail_url
        if duration_seconds is not None:
            video.duration_seconds = duration_seconds

        await db.commit()
        await db.refresh(video)
        return video

    async def create_job(
        self,
        video_id: UUID,
        job_type: str,
        db: AsyncSession
    ) -> Job:
        """
        Create a new processing job.

        Args:
            video_id: Video's UUID
            job_type: Job type (VIDEO_PROCESS, PDF_EXPORT)
            db: Database session

        Returns:
            Created Job object
        """
        job = Job(
            video_id=video_id,
            type=job_type,
            status=self.JOB_PENDING,
            progress=0
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        db: AsyncSession,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[Job]:
        """
        Update job status and progress.

        Args:
            job_id: Job's UUID
            status: New status
            db: Database session
            progress: Progress percentage (0-100)
            error_message: Error message if failed

        Returns:
            Updated Job object or None if not found
        """
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            return None

        job.status = status
        if progress is not None:
            job.progress = progress
        if error_message:
            job.error_message = error_message

        if status == self.JOB_PENDING:
            pass
        elif status in [self.JOB_FETCHING_TRANSCRIPT, self.JOB_GENERATING_NOTES]:
            if job.started_at is None:
                job.started_at = datetime.utcnow()
        elif status in [self.JOB_COMPLETED, self.JOB_FAILED]:
            job.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(job)
        return job

    async def get_job_by_id(self, job_id: UUID, db: AsyncSession) -> Optional[Job]:
        """
        Get job by ID.

        Args:
            job_id: Job's UUID
            db: Database session

        Returns:
            Job object or None if not found
        """
        result = await db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def save_transcript(
        self,
        video_id: UUID,
        language_code: str,
        provider: str,
        raw_text: str,
        segments: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Transcript:
        """
        Save or update transcript for a video.

        Args:
            video_id: Video's UUID
            language_code: Language code (e.g., "en")
            provider: Transcript provider (e.g., "youtube_auto")
            raw_text: Full transcript text
            segments: List of transcript segments with timestamps
            db: Database session

        Returns:
            Created or updated Transcript object
        """
        # Check if transcript already exists for this video
        existing = await self.get_transcript_by_video_id(video_id, db)

        if existing:
            # Update existing transcript (e.g., for transliteration)
            existing.language_code = language_code
            existing.provider = provider
            existing.raw_text = raw_text
            existing.segments = segments
            await db.commit()
            await db.refresh(existing)
            return existing

        # Create new transcript
        transcript = Transcript(
            video_id=video_id,
            language_code=language_code,
            provider=provider,
            raw_text=raw_text,
            segments=segments
        )
        db.add(transcript)
        await db.commit()
        await db.refresh(transcript)
        return transcript

    async def get_transcript_by_video_id(
        self,
        video_id: UUID,
        db: AsyncSession
    ) -> Optional[Transcript]:
        """
        Get transcript by video ID.

        Args:
            video_id: Video's UUID
            db: Database session

        Returns:
            Transcript object or None if not found
        """
        result = await db.execute(
            select(Transcript).where(Transcript.video_id == video_id)
        )
        return result.scalar_one_or_none()

    async def save_notes(
        self,
        video_id: UUID,
        db: AsyncSession,
        # Structured notes fields
        summary: str,
        bullets: List[str],
        key_timestamps: List[Dict[str, Any]],
        flashcards: List[Dict[str, str]],
        action_items: List[str],
        topics: List[str],
        difficulty_level: str,
        # Full notes fields
        markdown_notes: str,
        chapters: List[Dict[str, Any]],
        # AI metadata
        notes_model: str,
        notes_tokens: int,
        chapters_tokens: int,
        was_truncated: bool = False,
        raw_llm_output: Optional[Dict[str, Any]] = None
    ) -> Notes:
        """
        Save AI-generated notes for a video.

        Args:
            video_id: Video's UUID
            db: Database session
            summary: 2-3 sentence summary
            bullets: List of key points
            key_timestamps: List of important moments with timestamps
            flashcards: List of Q&A pairs
            action_items: List of actionable takeaways
            topics: List of topic tags
            difficulty_level: beginner/intermediate/advanced
            markdown_notes: Full markdown notes
            chapters: List of chapters with timestamps
            notes_model: AI model used
            notes_tokens: Tokens used for notes generation
            chapters_tokens: Tokens used for chapters generation
            was_truncated: Whether transcript was truncated
            raw_llm_output: Raw LLM output for debugging

        Returns:
            Created Notes object
        """
        notes = Notes(
            video_id=video_id,
            summary=summary,
            bullets=bullets,
            key_timestamps=key_timestamps,
            flashcards=flashcards,
            action_items=action_items,
            topics=topics,
            difficulty_level=difficulty_level,
            markdown_notes=markdown_notes,
            chapters=chapters,
            notes_model=notes_model,
            notes_tokens=notes_tokens,
            chapters_tokens=chapters_tokens,
            was_truncated="Y" if was_truncated else "N",
            raw_llm_output=raw_llm_output
        )
        db.add(notes)
        await db.commit()
        await db.refresh(notes)
        return notes

    async def get_notes_by_video_id(
        self,
        video_id: UUID,
        db: AsyncSession
    ) -> Optional[Notes]:
        """
        Get notes by video ID.

        Args:
            video_id: Video's UUID
            db: Database session

        Returns:
            Notes object or None if not found
        """
        result = await db.execute(
            select(Notes).where(Notes.video_id == video_id)
        )
        return result.scalar_one_or_none()

    async def delete_video(self, video_id: UUID, db: AsyncSession) -> bool:
        """
        Delete a video and all related data (cascade).

        Args:
            video_id: Video's UUID
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        video = await self.get_video_by_id(video_id, db)
        if not video:
            return False

        await db.delete(video)
        await db.commit()
        return True

    async def check_duplicate_video(
        self,
        user_id: UUID,
        youtube_video_id: str,
        db: AsyncSession
    ) -> Optional[Video]:
        """
        Check if user already has this video processed.

        Args:
            user_id: User's UUID
            youtube_video_id: YouTube video ID
            db: Database session

        Returns:
            Existing Video if found, None otherwise
        """
        return await self.get_video_by_youtube_id(user_id, youtube_video_id, db)
