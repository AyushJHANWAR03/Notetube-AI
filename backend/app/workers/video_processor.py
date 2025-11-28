"""
Video Processing Worker - Background task for processing YouTube videos.

Uses RQ (Redis Queue) for background job processing.
Runs 2 AI generation tasks in parallel using ThreadPoolExecutor.
"""
import asyncio
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional
from uuid import UUID
import logging

from redis import Redis
from rq import Queue
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.youtube_service import YouTubeService, YouTubeServiceError
from app.services.ai_notes_service import AINotesService, AINotesServiceError
from app.services.video_processing_service import VideoProcessingService
from app.services.chat_service import ChatService, ChatServiceError

# Cooldown between YouTube API calls to avoid rate limits
YOUTUBE_COOLDOWN_SECONDS = 3

# Setup logging
logger = logging.getLogger(__name__)

# Redis connection
redis_conn = Redis.from_url(settings.REDIS_URL)

# RQ Queue
video_queue = Queue("video_processing", connection=redis_conn)

# Async engine for database operations
async_engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def process_video_task(video_id: str, user_id: str, youtube_url: str) -> Dict[str, Any]:
    """
    Background task to process a YouTube video.

    This is the entry point called by RQ worker.

    Args:
        video_id: Video's UUID as string
        user_id: User's UUID as string
        youtube_url: Original YouTube URL

    Returns:
        Dictionary with processing result
    """
    print(f"\n{'='*60}")
    print(f"[JOB START] Processing video: {video_id}")
    print(f"[JOB START] YouTube URL: {youtube_url}")
    print(f"[JOB START] User: {user_id}")
    print(f"{'='*60}\n")

    # Run the async processing in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _process_video_async(
                UUID(video_id),
                UUID(user_id),
                youtube_url
            )
        )
        print(f"\n{'='*60}")
        print(f"[JOB END] Video {video_id} - Result: {result}")
        print(f"{'='*60}\n")
        return result
    finally:
        loop.close()


async def _process_video_async(
    video_id: UUID,
    user_id: UUID,
    youtube_url: str
) -> Dict[str, Any]:
    """
    Async implementation of video processing.

    Steps:
    1. Update video status to PROCESSING
    2. Extract YouTube video data (metadata + transcript)
    3. Run all 3 AI generation tasks in parallel
    4. Save everything to database
    5. Update video status to READY (or FAILED)
    """
    video_service = VideoProcessingService()

    async with AsyncSessionLocal() as db:
        job = None

        try:
            # Create processing job
            print(f"[STEP 1/7] Creating processing job in database...")
            job = await video_service.create_job(
                video_id,
                video_service.JOB_TYPE_VIDEO_PROCESS,
                db
            )
            print(f"[STEP 1/7] ✓ Job created: {job.id}")

            # Update video status to PROCESSING
            print(f"[STEP 2/7] Updating video status to PROCESSING...")
            await video_service.update_video_status(
                video_id,
                video_service.STATUS_PROCESSING,
                db
            )
            print(f"[STEP 2/7] ✓ Video status updated")

            # Step 1: Fetch YouTube data (with caching)
            await video_service.update_job_status(
                job.id,
                video_service.JOB_FETCHING_TRANSCRIPT,
                db,
                progress=10
            )

            youtube_service = YouTubeService()
            yt_video_id = youtube_service.extract_video_id(youtube_url)
            print(f"[STEP 3/7] Extracted YouTube video ID: {yt_video_id}")

            # Check Redis cache for transcript first
            cache_key = f"transcript:{yt_video_id}"
            cached_data = redis_conn.get(cache_key)

            if cached_data:
                print(f"[STEP 3/7] ✓ Using CACHED transcript for {yt_video_id}")
                video_data = json.loads(cached_data)
            else:
                # Fetch from YouTube
                print(f"[STEP 3/7] Fetching transcript from YouTube (no cache)...")
                video_data = youtube_service.process_video_url(youtube_url)

                # Cache for 24 hours (transcripts don't change often)
                redis_conn.setex(cache_key, 86400, json.dumps(video_data))
                print(f"[STEP 3/7] ✓ Transcript cached for 24 hours")

                # Add cooldown after YouTube fetch to avoid rate limits
                time.sleep(YOUTUBE_COOLDOWN_SECONDS)
                print(f"[STEP 3/7] ✓ Fetched transcript: {len(video_data['transcript']['segments'])} segments")

            # Update video metadata
            print(f"[STEP 4/7] Saving video metadata...")
            print(f"  - Title: {video_data['metadata'].get('title', 'N/A')}")
            print(f"  - Duration: {video_data['metadata'].get('duration_seconds', 0)} seconds")
            await video_service.update_video_metadata(
                video_id,
                db,
                title=video_data["metadata"].get("title"),
                thumbnail_url=video_data["metadata"].get("thumbnail"),
                duration_seconds=video_data["metadata"].get("duration_seconds")
            )
            print(f"[STEP 4/7] ✓ Metadata saved")

            # Save transcript
            print(f"[STEP 4/7] Saving transcript to database...")
            print(f"  - Language: {video_data['transcript']['language_code']}")
            print(f"  - Provider: {video_data['transcript']['provider']}")
            print(f"  - Segments: {len(video_data['transcript']['segments'])}")
            await video_service.save_transcript(
                video_id=video_id,
                language_code=video_data["transcript"]["language_code"],
                provider=video_data["transcript"]["provider"],
                raw_text=video_data["transcript"]["raw_text"],
                segments=video_data["transcript"]["segments"],
                db=db
            )
            print(f"[STEP 4/7] ✓ Transcript saved")

            # Get transcript data
            transcript = video_data["transcript"]["raw_text"]
            segments = video_data["transcript"]["segments"]
            language_code = video_data["transcript"]["language_code"]

            # Step 2: Transliterate non-English transcripts to English
            transliteration_tokens = 0
            if not language_code.lower().startswith('en'):
                print(f"[STEP 4.5/7] Transliterating {language_code} transcript to English...")
                print(f"  - Original segments: {len(segments)}")

                ai_service = AINotesService()
                transliteration_result = ai_service.transliterate_to_english(
                    segments=segments,
                    source_language=language_code
                )

                if transliteration_result.get("was_transliterated"):
                    segments = transliteration_result["segments"]
                    transcript = transliteration_result["raw_text"]
                    transliteration_tokens = transliteration_result["tokens_used"]
                    print(f"[STEP 4.5/7] ✓ Transliteration complete ({transliteration_tokens} tokens)")
                    print(f"  - Sample: {segments[0]['text'][:100] if segments else 'N/A'}...")

                    # Update transcript in database with English version
                    print(f"[STEP 4.5/7] Updating transcript with English version...")
                    await video_service.save_transcript(
                        video_id=video_id,
                        language_code="en",  # Now English
                        provider=video_data["transcript"]["provider"] + "_transliterated",
                        raw_text=transcript,
                        segments=segments,
                        db=db
                    )
                    print(f"[STEP 4.5/7] ✓ English transcript saved")
                else:
                    print(f"[STEP 4.5/7] Skipped (already English)")

            await video_service.update_job_status(
                job.id,
                video_service.JOB_GENERATING_NOTES,
                db,
                progress=40
            )

            # Step 3: Generate AI content in parallel
            video_title = video_data["metadata"].get("title", "Untitled")
            video_duration = video_data["metadata"].get("duration_seconds", 0)

            print(f"[STEP 5/7] Starting AI content generation (2 parallel tasks)...")
            print(f"  - Transcript length: {len(transcript)} chars")
            print(f"  - Video title: {video_title}")
            ai_results = await _generate_ai_content_parallel(
                transcript,
                segments,
                video_title,
                video_duration
            )
            print(f"[STEP 5/7] ✓ AI content generated")

            # Step 3.5: Generate suggested chat prompts
            print(f"[STEP 5.5/7] Generating suggested chat prompts...")
            suggested_prompts = []
            try:
                chat_service = ChatService()
                suggested_prompts = chat_service.generate_suggested_prompts(
                    summary=ai_results["structured"]["summary"],
                    topics=ai_results["structured"]["topics"],
                    chapters=ai_results["chapters"]["chapters"]
                )
                print(f"[STEP 5.5/7] ✓ Generated {len(suggested_prompts)} suggested prompts")
            except ChatServiceError as e:
                print(f"[STEP 5.5/7] ⚠ Could not generate suggested prompts: {e}")
                # Non-fatal error, continue without suggested prompts
            except Exception as e:
                print(f"[STEP 5.5/7] ⚠ Unexpected error generating prompts: {e}")
                # Non-fatal error, continue without suggested prompts

            # Step 3: Save notes to database
            print(f"[STEP 6/7] Saving AI-generated notes to database...")
            print(f"  - Summary length: {len(ai_results['structured']['summary'])} chars")
            print(f"  - Bullets: {len(ai_results['structured']['bullets'])} items")
            print(f"  - Chapters: {len(ai_results['chapters']['chapters'])} chapters")
            print(f"  - Flashcards: {len(ai_results['structured']['flashcards'])} cards")
            await video_service.save_notes(
                video_id=video_id,
                db=db,
                # Structured notes
                summary=ai_results["structured"]["summary"],
                bullets=ai_results["structured"]["bullets"],
                key_timestamps=ai_results["structured"]["key_timestamps"],
                flashcards=ai_results["structured"]["flashcards"],
                action_items=ai_results["structured"]["action_items"],
                topics=ai_results["structured"]["topics"],
                difficulty_level=ai_results["structured"]["difficulty_level"],
                # Full notes - no longer generated, pass empty string
                markdown_notes="",
                chapters=ai_results["chapters"]["chapters"],
                # AI metadata
                notes_model=ai_results["structured"]["model_used"],
                notes_tokens=ai_results["structured"]["tokens_used"],
                chapters_tokens=ai_results["chapters"]["tokens_used"],
                was_truncated=False,
                raw_llm_output={
                    "chapters": ai_results["chapters"],
                    "structured": ai_results["structured"]
                },
                # Chat suggested prompts
                suggested_prompts=suggested_prompts if suggested_prompts else None
            )
            print(f"[STEP 6/7] ✓ Notes saved to database")

            # Step 4: Mark as complete
            print(f"[STEP 7/7] Marking video as READY...")
            await video_service.update_job_status(
                job.id,
                video_service.JOB_COMPLETED,
                db,
                progress=100
            )

            await video_service.update_video_status(
                video_id,
                video_service.STATUS_READY,
                db
            )

            total_tokens = (
                ai_results["chapters"]["tokens_used"] +
                ai_results["structured"]["tokens_used"] +
                transliteration_tokens
            )

            print(f"[STEP 7/7] ✓ Video processing COMPLETE!")
            print(f"  - Total tokens used: {total_tokens}")
            if transliteration_tokens > 0:
                print(f"  - Transliteration tokens: {transliteration_tokens}")
            print(f"  - Chapters tokens: {ai_results['chapters']['tokens_used']}")
            print(f"  - Structured tokens: {ai_results['structured']['tokens_used']}")

            return {
                "success": True,
                "video_id": str(video_id),
                "total_tokens": total_tokens
            }

        except YouTubeServiceError as e:
            error_msg = f"YouTube error: {str(e)}"
            print(f"\n[ERROR] ❌ YouTube fetch failed!")
            print(f"[ERROR] {error_msg}")

            if job:
                await video_service.update_job_status(
                    job.id,
                    video_service.JOB_FAILED,
                    db,
                    error_message=error_msg
                )

            await video_service.update_video_status(
                video_id,
                video_service.STATUS_FAILED,
                db,
                failure_reason=error_msg
            )

            return {"success": False, "error": error_msg}

        except AINotesServiceError as e:
            error_msg = f"AI error: {str(e)}"
            print(f"\n[ERROR] ❌ AI generation failed!")
            print(f"[ERROR] {error_msg}")

            if job:
                await video_service.update_job_status(
                    job.id,
                    video_service.JOB_FAILED,
                    db,
                    error_message=error_msg
                )

            await video_service.update_video_status(
                video_id,
                video_service.STATUS_FAILED,
                db,
                failure_reason=error_msg
            )

            return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"\n[ERROR] ❌ Unexpected error!")
            print(f"[ERROR] {error_msg}")

            if job:
                await video_service.update_job_status(
                    job.id,
                    video_service.JOB_FAILED,
                    db,
                    error_message=error_msg
                )

            await video_service.update_video_status(
                video_id,
                video_service.STATUS_FAILED,
                db,
                failure_reason=error_msg
            )

            return {"success": False, "error": error_msg}


async def _generate_ai_content_parallel(
    transcript: str,
    segments: list,
    video_title: str,
    video_duration: float
) -> Dict[str, Any]:
    """
    Generate all AI content in parallel using ThreadPoolExecutor.

    Runs 2 tasks concurrently:
    1. generate_chapters() - Video chapters (Breakdown tab)
    2. generate_structured_notes() - Summary, bullets, flashcards, etc.

    Args:
        transcript: Full transcript text
        segments: List of transcript segments with timestamps
        video_title: Video title
        video_duration: Video duration in seconds

    Returns:
        Dictionary with all AI generation results
    """
    ai_service = AINotesService()

    def generate_chapters():
        print(f"  [AI] Starting chapters generation...")
        result = ai_service.generate_chapters(
            transcript,
            segments,
            video_duration=video_duration
        )
        print(f"  [AI] ✓ Chapters done ({len(result['chapters'])} chapters, {result['tokens_used']} tokens)")
        return result

    def generate_structured():
        print(f"  [AI] Starting structured notes generation...")
        result = ai_service.generate_structured_notes(
            transcript,
            segments,
            video_title=video_title
        )
        print(f"  [AI] ✓ Structured notes done ({result['tokens_used']} tokens)")
        return result

    # Run 2 AI tasks in parallel
    print(f"  [AI] Launching 2 parallel OpenAI requests...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(generate_chapters): "chapters",
            executor.submit(generate_structured): "structured"
        }

        results = {}
        for future in as_completed(futures):
            task_name = futures[future]
            try:
                results[task_name] = future.result()
            except Exception as e:
                print(f"  [AI] ❌ Task '{task_name}' FAILED: {str(e)}")
                raise AINotesServiceError(f"Failed to generate {task_name}: {str(e)}")

    print(f"  [AI] All 2 AI tasks completed successfully")
    return results


def enqueue_video_processing(video_id: UUID, user_id: UUID, youtube_url: str) -> str:
    """
    Enqueue a video for background processing.

    Args:
        video_id: Video's UUID
        user_id: User's UUID
        youtube_url: YouTube URL to process

    Returns:
        Job ID from RQ
    """
    job = video_queue.enqueue(
        process_video_task,
        str(video_id),
        str(user_id),
        youtube_url,
        job_timeout=600,  # 10 minute timeout
        result_ttl=3600   # Keep result for 1 hour
    )

    logger.info(f"Enqueued video {video_id} for processing. Job ID: {job.id}")
    return job.id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a queued job.

    Args:
        job_id: RQ job ID

    Returns:
        Dictionary with job status or None if not found
    """
    from rq.job import Job

    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            "job_id": job_id,
            "status": job.get_status(),
            "result": job.result,
            "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "exc_info": job.exc_info
        }
    except Exception:
        return None
