"""
Video API routes for processing YouTube videos.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
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
from app.services.guest_service import guest_service
from app.api.dependencies.auth import get_current_user, get_current_user_optional
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

    # Check video limit
    if current_user.videos_analyzed >= current_user.video_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="LIMIT_REACHED"
        )

    # Extract and validate YouTube video ID
    try:
        youtube_video_id = youtube_service.extract_video_id(request.url)
    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Check for duplicate (user already has this video)
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

    # Global cache check - has ANY user already processed this video?
    cached_video = await video_service.find_ready_video_globally(
        youtube_video_id,
        db
    )

    if cached_video:
        # Clone to this user's library instantly!
        # This does NOT count towards user's quota since no AI cost was incurred
        cloned_video = await video_service.clone_video_for_user(
            source_video=cached_video,
            user_id=current_user.id,
            original_url=request.url,
            db=db
        )
        return VideoCreateResponse(
            video=VideoListItem.model_validate(cloned_video),
            job_id="",  # No job needed - already processed!
            message="Video instantly loaded from cache!"
        )

    # Create new video record (no cache hit - needs full processing)
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


@router.post("/guest", response_model=VideoCreateResponse)
async def create_video_guest(
    video_request: VideoCreateRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a YouTube video for processing (guest access).

    Allows anonymous users to process 1 video for free.
    If user is authenticated, redirects to normal flow.
    If video is cached, returns instantly without consuming quota.

    Returns:
        - Video info and job ID if successful
        - 401 with requires_auth=true if guest limit reached
    """
    # If user is authenticated, use normal flow
    if current_user:
        return await create_video(video_request, current_user, db)

    video_service = VideoProcessingService()
    youtube_service = YouTubeService()

    # Extract YouTube video ID first
    try:
        youtube_video_id = youtube_service.extract_video_id(video_request.url)
    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Check guest access state
    access_state = await guest_service.get_guest_access_state(
        db, request, youtube_video_id
    )

    # If video is cached, allow access
    if access_state["is_cached"]:
        cached_video = await video_service.find_ready_video_globally(
            youtube_video_id, db
        )
        if cached_video:
            response = JSONResponse(
                content={
                    "video": VideoListItem.model_validate(cached_video).model_dump(mode="json"),
                    "job_id": "",
                    "message": "Video loaded from cache!",
                    "is_guest": True,
                    "guest_token": access_state["guest_token"]
                }
            )
            # Set guest token cookie
            response.set_cookie(
                key=guest_service.GUEST_TOKEN_COOKIE,
                value=access_state["guest_token"],
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                samesite="lax",
                secure=settings.ENVIRONMENT == "production"
            )
            return response

    # Check if guest can generate new video
    if not access_state["can_generate"]:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "GUEST_LIMIT_REACHED",
                "requires_auth": True,
                "message": "Sign in to continue analyzing videos"
            }
        )

    # Guest can process - create video with null user_id
    video = await video_service.create_video(
        user_id=None,  # Guest video - no user
        youtube_video_id=youtube_video_id,
        original_url=video_request.url,
        db=db
    )

    # Record guest usage BEFORE processing (to prevent race conditions)
    guest_token = access_state["guest_token"]
    ip_hash = guest_service.hash_ip(guest_service.get_client_ip(request))

    await guest_service.record_guest_usage(
        db=db,
        guest_token=guest_token,
        ip_hash=ip_hash,
        video_id=video.id,
        youtube_id=youtube_video_id
    )

    # Enqueue background processing (null user_id for guest)
    job_id = enqueue_video_processing(
        video.id,
        None,  # No user ID for guest
        video_request.url
    )

    response = JSONResponse(
        content={
            "video": VideoListItem.model_validate(video).model_dump(mode="json"),
            "job_id": job_id,
            "message": "Video submitted for processing",
            "is_guest": True,
            "guest_token": guest_token
        }
    )

    # Set guest token cookie
    response.set_cookie(
        key=guest_service.GUEST_TOKEN_COOKIE,
        value=guest_token,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production"
    )

    return response


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

    # Get actual total count (not just returned count)
    total_count = await video_service.count_user_videos(
        current_user.id,
        db,
        status=status_filter
    )

    return VideoListResponse(
        videos=[VideoListItem.model_validate(v) for v in videos],
        total=total_count
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: UUID,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
) -> VideoDetailResponse:
    """
    Get detailed video information including notes and transcript.

    For authenticated users: requires ownership.
    For guests: allows access to guest videos (user_id is NULL).
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

    # Check access permissions
    # Guest videos (user_id=None) are accessible by anyone
    # READY videos are accessible by anyone (cached videos can be viewed by all)
    # Non-READY videos require ownership
    if video.user_id is None:
        # Guest video - allow access (anyone with the ID can view)
        pass
    elif video.status == "READY":
        # Cached/ready videos are accessible by anyone (read-only)
        # This supports the cache-first experience for both guests and signed-in users
        pass
    elif current_user is None:
        # Non-ready video and no authentication
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    elif video.user_id != current_user.id:
        # Non-ready video and user doesn't own it
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
) -> VideoStatusResponse:
    """
    Get video processing status and job information.

    Use this endpoint to poll for processing completion.
    Allows guest access for guest videos.
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

    # Check access permissions (same logic as get_video)
    # Anyone with the video ID can check status - this is needed for:
    # 1. Guest videos (user_id=None)
    # 2. Processing status polling for any video
    # 3. Cached videos accessible to all
    # Only restrict if: non-ready, not owner, and authenticated
    if video.user_id is None:
        # Guest video - allow access
        pass
    elif video.status == "READY":
        # Cached/ready videos - status accessible by anyone
        pass
    elif current_user is None:
        # Non-ready video, no auth - allow status check for guest flow
        pass
    elif video.user_id != current_user.id:
        # Non-ready video, authenticated user who doesn't own it
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
) -> SeekResponse:
    """
    Find the timestamp where a specific topic is discussed.

    Uses AI to understand the query semantically and match it against
    the video transcript. Supports queries in any language.

    Returns the best matching timestamp with confidence level.

    Access control:
    - Guest videos (user_id=None): accessible by anyone
    - READY videos: accessible by anyone (cached videos)
    - Non-READY videos: require ownership
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

    # Check access permissions (same pattern as get_video and chat)
    # Guest videos (user_id=None) are accessible by anyone
    # READY videos are accessible by anyone (cached videos can be searched by all)
    # Non-READY videos require ownership
    if video.user_id is None:
        # Guest video - allow access
        pass
    elif video.status == "READY":
        # Cached/ready videos - search accessible by anyone
        pass
    elif current_user is None:
        # Non-ready video and no authentication
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    elif video.user_id != current_user.id:
        # Non-ready video and user doesn't own it
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
        result = await seek_service.find_timestamp_async(
            query=request.query,
            segments=video.transcript.segments,
            video_duration=video.duration_seconds,
            transcript_id=video.transcript.id,
            db=db
        )

        return SeekResponse(**result)

    except SeekServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
