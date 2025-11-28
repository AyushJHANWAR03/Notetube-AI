"""
Video API routes for processing YouTube videos.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.video import (
    VideoCreateRequest,
    VideoCreateResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoListItem,
    VideoStatusResponse,
    NotesSchema,
    TranscriptSchema,
    JobStatusSchema,
    SeekRequest,
    SeekResponse
)
from app.schemas.user import User
from app.services.video_processing_service import VideoProcessingService
from app.services.youtube_service import YouTubeService, YouTubeServiceError
from app.services.seek_service import SeekService, SeekServiceError
from app.api.dependencies.auth import get_current_user
from app.workers.video_processor import enqueue_video_processing


router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("", response_model=VideoCreateResponse)
async def create_video(
    request: VideoCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> VideoCreateResponse:
    """
    Submit a YouTube video for processing.

    - Validates the YouTube URL
    - Checks for duplicate videos
    - Creates a video record
    - Enqueues background processing

    Returns video info and job ID for tracking.
    """
    video_service = VideoProcessingService()
    youtube_service = YouTubeService()

    # Extract and validate YouTube video ID
    try:
        youtube_video_id = youtube_service.extract_video_id(request.url)
    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Check for duplicate
    existing_video = await video_service.check_duplicate_video(
        current_user.id,
        youtube_video_id,
        db
    )

    if existing_video:
        # Return existing video instead of creating duplicate
        return VideoCreateResponse(
            video=VideoListItem.model_validate(existing_video),
            job_id="",  # No new job needed
            message="Video already exists in your library"
        )

    # Create new video record
    video = await video_service.create_video(
        user_id=current_user.id,
        youtube_video_id=youtube_video_id,
        original_url=request.url,
        db=db
    )

    # Enqueue background processing
    job_id = enqueue_video_processing(
        video.id,
        current_user.id,
        request.url
    )

    return VideoCreateResponse(
        video=VideoListItem.model_validate(video),
        job_id=job_id,
        message="Video submitted for processing"
    )


@router.get("", response_model=VideoListResponse)
async def list_videos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, alias="status")
) -> VideoListResponse:
    """
    Get all videos for the current user.

    Supports pagination and filtering by status.
    """
    video_service = VideoProcessingService()

    videos = await video_service.get_user_videos(
        current_user.id,
        db,
        limit=limit,
        offset=offset,
        status=status_filter
    )

    return VideoListResponse(
        videos=[VideoListItem.model_validate(v) for v in videos],
        total=len(videos)
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> VideoDetailResponse:
    """
    Get detailed video information including notes and transcript.
    """
    video_service = VideoProcessingService()

    video = await video_service.get_video_by_id(
        video_id,
        db,
        include_relations=True
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Verify ownership
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video"
        )

    # Build response with related data
    response_data = {
        "id": video.id,
        "youtube_video_id": video.youtube_video_id,
        "original_url": video.original_url,
        "title": video.title,
        "thumbnail_url": video.thumbnail_url,
        "duration_seconds": video.duration_seconds,
        "status": video.status,
        "failure_reason": video.failure_reason,
        "created_at": video.created_at,
        "updated_at": video.updated_at,
        "processed_at": video.processed_at,
        "notes": None,
        "transcript": None
    }

    if video.notes:
        response_data["notes"] = {
            "summary": video.notes.summary,
            "bullets": video.notes.bullets,
            "key_timestamps": video.notes.key_timestamps,
            "flashcards": video.notes.flashcards,
            "action_items": video.notes.action_items,
            "topics": video.notes.topics,
            "difficulty_level": video.notes.difficulty_level,
            "markdown_notes": video.notes.markdown_notes,
            "chapters": video.notes.chapters,
            "suggested_prompts": video.notes.suggested_prompts
        }

    if video.transcript:
        response_data["transcript"] = {
            "language_code": video.transcript.language_code,
            "provider": video.transcript.provider,
            "raw_text": video.transcript.raw_text,
            "segments": video.transcript.segments
        }

    return VideoDetailResponse(**response_data)


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> VideoStatusResponse:
    """
    Get video processing status and job information.

    Use this endpoint to poll for processing completion.
    """
    video_service = VideoProcessingService()

    video = await video_service.get_video_by_id(
        video_id,
        db,
        include_relations=True
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Verify ownership
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video"
        )

    jobs = [JobStatusSchema.model_validate(j) for j in video.jobs] if video.jobs else []

    return VideoStatusResponse(
        video=VideoListItem.model_validate(video),
        jobs=jobs
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a video and all its related data.
    """
    video_service = VideoProcessingService()

    video = await video_service.get_video_by_id(video_id, db)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Verify ownership
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this video"
        )

    await video_service.delete_video(video_id, db)


@router.post("/{video_id}/reprocess", response_model=VideoCreateResponse)
async def reprocess_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> VideoCreateResponse:
    """
    Reprocess a failed video.

    Only works for videos with FAILED status.
    """
    video_service = VideoProcessingService()

    video = await video_service.get_video_by_id(video_id, db)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Verify ownership
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reprocess this video"
        )

    if video.status != "FAILED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reprocess failed videos"
        )

    # Reset status to pending
    await video_service.update_video_status(
        video_id,
        video_service.STATUS_PENDING,
        db
    )

    # Enqueue for processing
    job_id = enqueue_video_processing(
        video.id,
        current_user.id,
        video.original_url
    )

    # Refresh video data
    video = await video_service.get_video_by_id(video_id, db)

    return VideoCreateResponse(
        video=VideoListItem.model_validate(video),
        job_id=job_id,
        message="Video resubmitted for processing"
    )


@router.post("/{video_id}/seek", response_model=SeekResponse)
async def seek_to_topic(
    video_id: UUID,
    request: SeekRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SeekResponse:
    """
    Find the timestamp where a specific topic is discussed.

    Uses AI to understand the query semantically and match it against
    the video transcript. Supports queries in any language.

    Returns the best matching timestamp with confidence level.
    """
    video_service = VideoProcessingService()

    video = await video_service.get_video_by_id(
        video_id,
        db,
        include_relations=True
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Verify ownership
    if video.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video"
        )

    # Check if transcript exists
    if not video.transcript or not video.transcript.segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transcript available for this video"
        )

    try:
        seek_service = SeekService()
        result = seek_service.find_timestamp(
            query=request.query,
            segments=video.transcript.segments,
            video_duration=video.duration_seconds
        )

        return SeekResponse(**result)

    except SeekServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
