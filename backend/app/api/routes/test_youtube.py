"""
Temporary test endpoints for YouTubeService and AINotesService - for development testing only.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.youtube_service import YouTubeService, YouTubeServiceError
from app.services.ai_notes_service import AINotesService, AINotesServiceError


router = APIRouter(prefix="/test", tags=["testing"])


class YouTubeURLRequest(BaseModel):
    """Request model for YouTube URL."""
    url: str


@router.post("/youtube/process")
async def test_youtube_processing(request: YouTubeURLRequest):
    """
    Test endpoint to process a YouTube URL and return all extracted data.

    This is for development testing only.
    """
    try:
        service = YouTubeService()
        result = service.process_video_url(request.url)

        return {
            "success": True,
            "data": {
                "video_id": result["video_id"],
                "metadata": result["metadata"],
                "transcript_preview": {
                    "language_code": result["transcript"]["language_code"],
                    "provider": result["transcript"]["provider"],
                    "total_segments": len(result["transcript"]["segments"]),
                    "raw_text_preview": result["transcript"]["raw_text"][:500] + "...",
                    "first_3_segments": result["transcript"]["segments"][:3]
                }
            }
        }

    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/ai/generate-notes")
async def test_ai_notes_generation(request: YouTubeURLRequest):
    """
    Test endpoint to process a YouTube video and generate ALL AI content.

    This is for development testing only - combines YouTube extraction with AI processing.
    Generates: markdown_notes, chapters, and structured_notes (summary, bullets, flashcards, etc.)
    """
    try:
        # Step 1: Extract YouTube data
        youtube_service = YouTubeService()
        video_data = youtube_service.process_video_url(request.url)

        # Step 2: Generate AI content
        ai_service = AINotesService()

        transcript = video_data["transcript"]["raw_text"]
        segments = video_data["transcript"]["segments"]
        video_title = video_data["metadata"].get("title", "Untitled")
        video_duration = video_data["metadata"].get("duration_seconds", 0)

        # Generate all 3 types of content (in production these would run in parallel)
        # 1. Markdown notes
        notes_result = ai_service.generate_notes(transcript, video_title=video_title)

        # 2. Chapters with timestamps
        chapters_result = ai_service.generate_chapters(
            transcript,
            segments,
            video_duration=video_duration
        )

        # 3. Structured notes (summary, bullets, flashcards, etc.)
        structured_result = ai_service.generate_structured_notes(
            transcript,
            segments,
            video_title=video_title
        )

        total_tokens = (
            notes_result["tokens_used"] +
            chapters_result["tokens_used"] +
            structured_result["tokens_used"]
        )

        return {
            "success": True,
            "data": {
                "video_id": video_data["video_id"],
                "metadata": video_data["metadata"],
                "ai_notes": {
                    "markdown_notes": notes_result["markdown_notes"],
                    "model_used": notes_result["model_used"],
                    "tokens_used": notes_result["tokens_used"],
                    "was_truncated": notes_result.get("was_truncated", False)
                },
                "chapters": {
                    "count": len(chapters_result["chapters"]),
                    "chapters": chapters_result["chapters"],
                    "model_used": chapters_result["model_used"],
                    "tokens_used": chapters_result["tokens_used"]
                },
                "structured_notes": {
                    "summary": structured_result["summary"],
                    "bullets": structured_result["bullets"],
                    "key_timestamps": structured_result["key_timestamps"],
                    "flashcards": structured_result["flashcards"],
                    "action_items": structured_result["action_items"],
                    "topics": structured_result["topics"],
                    "difficulty_level": structured_result["difficulty_level"],
                    "tokens_used": structured_result["tokens_used"]
                },
                "transcript_info": {
                    "total_segments": len(segments),
                    "language_code": video_data["transcript"]["language_code"]
                },
                "total_tokens_used": total_tokens
            }
        }

    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"YouTube error: {str(e)}"
        )
    except AINotesServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/youtube/extract-id")
async def test_extract_video_id(url: str):
    """
    Test endpoint to extract video ID from YouTube URL.
    """
    try:
        service = YouTubeService()
        video_id = service.extract_video_id(url)

        return {
            "success": True,
            "url": url,
            "video_id": video_id
        }

    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
