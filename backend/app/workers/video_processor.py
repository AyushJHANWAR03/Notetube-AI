"""
Video Processing Worker - Background task for processing YouTube videos.

Uses RQ (Redis Queue) for background job processing.
Runs 2 AI generation tasks in parallel using ThreadPoolExecutor.

IMPORTANT: This worker uses SYNCHRONOUS database operations (psycopg2)
to avoid greenlet/async issues with the RQ worker.
"""
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from redis import Redis
from rq import Queue
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.services.youtube_service import YouTubeService, YouTubeServiceError
from app.services.ai_notes_service import AINotesService, AINotesServiceError
from app.services.chat_service import ChatService, ChatServiceError
from app.services.transcript_processor import TranscriptProcessor
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.notes import Notes
from app.models.job import Job
from app.models.user import User
from app.core.constants import VideoStatus, JobStatus, JobType

# Cooldown between YouTube API calls to avoid rate limits
YOUTUBE_COOLDOWN_SECONDS = 3

# Redis connection
redis_conn = Redis.from_url(settings.REDIS_URL)

# RQ Queue
video_queue = Queue("video_processing", connection=redis_conn)


def get_sync_database_url(async_url: str) -> str:
    """Convert async psycopg URL to sync psycopg2 URL."""
    # postgresql+psycopg -> postgresql+psycopg2
    if "+psycopg" in async_url and "+psycopg2" not in async_url:
        return async_url.replace("+psycopg", "+psycopg2")
    return async_url


# Create SYNCHRONOUS database engine (uses psycopg2)
sync_database_url = get_sync_database_url(settings.DATABASE_URL)
sync_engine = create_engine(sync_database_url, echo=False, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


def process_video_task(video_id: str, user_id: str, youtube_url: str) -> Dict[str, Any]:
    """
    Background task to process a YouTube video.

    This is the entry point called by RQ worker.
    Uses SYNCHRONOUS database operations.

    Args:
        video_id: Video's UUID as string
        user_id: User's UUID as string
        youtube_url: Original YouTube URL

    Returns:
        Dictionary with processing result
    """
    print(f"\n{'='*60}")
    print(f"[JOB START] Processing video: {video_id}")
    print(f"  - URL: {youtube_url}")
    print(f"  - User: {user_id}")
    print(f"{'='*60}")

    result = _process_video_sync(
        UUID(video_id),
        UUID(user_id),
        youtube_url
    )

    print(f"\n{'='*60}")
    print(f"[JOB END] Video: {video_id} | Success: {result.get('success', False)}")
    print(f"{'='*60}\n")
    return result


def _process_video_sync(
    video_id: UUID,
    user_id: UUID,
    youtube_url: str
) -> Dict[str, Any]:
    """
    Synchronous implementation of video processing.

    Steps:
    1. Update video status to PROCESSING
    2. Extract YouTube video data (metadata + transcript)
    3. Run AI generation tasks in parallel
    4. Save everything to database
    5. Update video status to READY (or FAILED)
    """
    with SyncSessionLocal() as db:
        job = None

        try:
            # Create processing job
            print(f"[STEP 1/7] Creating processing job in database...")
            job = Job(
                video_id=video_id,
                type=JobType.VIDEO_PROCESS,
                status=JobStatus.PENDING,
                progress=0
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            print(f"[STEP 1/7] ✓ Job created: {job.id}")

            # Update video status to PROCESSING
            print(f"[STEP 2/7] Updating video status to PROCESSING...")
            video = db.execute(select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if video:
                video.status = VideoStatus.PROCESSING
                db.commit()
            print(f"[STEP 2/7] ✓ Video status updated")

            # Update job status
            job.status = JobStatus.FETCHING_TRANSCRIPT
            job.progress = 10
            job.started_at = datetime.utcnow()
            db.commit()

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

            video = db.execute(select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if video:
                video.title = video_data["metadata"].get("title")
                video.thumbnail_url = video_data["metadata"].get("thumbnail_url")
                video.duration_seconds = video_data["metadata"].get("duration_seconds")
                db.commit()
            print(f"[STEP 4/7] ✓ Metadata saved")

            # Save transcript
            print(f"[STEP 4/7] Saving transcript to database...")
            print(f"  - Language: {video_data['transcript']['language_code']}")
            print(f"  - Provider: {video_data['transcript']['provider']}")
            print(f"  - Segments: {len(video_data['transcript']['segments'])}")

            # Check if transcript exists
            existing_transcript = db.execute(
                select(Transcript).where(Transcript.video_id == video_id)
            ).scalar_one_or_none()

            if existing_transcript:
                existing_transcript.language_code = video_data["transcript"]["language_code"]
                existing_transcript.provider = video_data["transcript"]["provider"]
                existing_transcript.raw_text = video_data["transcript"]["raw_text"]
                existing_transcript.segments = video_data["transcript"]["segments"]
            else:
                transcript_obj = Transcript(
                    video_id=video_id,
                    language_code=video_data["transcript"]["language_code"],
                    provider=video_data["transcript"]["provider"],
                    raw_text=video_data["transcript"]["raw_text"],
                    segments=video_data["transcript"]["segments"]
                )
                db.add(transcript_obj)
            db.commit()
            print(f"[STEP 4/7] ✓ Transcript saved")

            # Get transcript data
            transcript = video_data["transcript"]["raw_text"]
            segments = video_data["transcript"]["segments"]
            language_code = video_data["transcript"]["language_code"]

            # Merge segments into sentences for better AI comprehension
            print(f"[STEP 4.1/7] Merging segments into sentences...")
            print(f"  - Original segments: {len(segments)}")
            transcript_processor = TranscriptProcessor()
            merged_segments = transcript_processor.merge_sentences(segments)
            print(f"  - Merged segments: {len(merged_segments)}")
            print(f"[STEP 4.1/7] ✓ Segments merged into sentences")

            # Use merged segments for AI processing
            segments = merged_segments

            # Transliterate non-English transcripts to English
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
                    existing_transcript = db.execute(
                        select(Transcript).where(Transcript.video_id == video_id)
                    ).scalar_one_or_none()
                    if existing_transcript:
                        existing_transcript.language_code = "en"
                        existing_transcript.provider = video_data["transcript"]["provider"] + "_transliterated"
                        existing_transcript.raw_text = transcript
                        existing_transcript.segments = segments
                        db.commit()
                    print(f"[STEP 4.5/7] ✓ English transcript saved")
                else:
                    print(f"[STEP 4.5/7] Skipped (already English)")

            # Update job status
            job.status = JobStatus.GENERATING_NOTES
            job.progress = 40
            db.commit()

            # Generate AI content in parallel
            video_title = video_data["metadata"].get("title", "Untitled")
            video_duration = video_data["metadata"].get("duration_seconds", 0)

            print(f"[STEP 5/7] Starting AI content generation (2 parallel tasks)...")
            print(f"  - Transcript length: {len(transcript)} chars")
            print(f"  - Video title: {video_title}")
            ai_results = _generate_ai_content_parallel(
                transcript,
                segments,
                video_title,
                video_duration
            )

            # For long videos, derive key_timestamps from chapters (better full-video coverage)
            if video_duration > 600 and ai_results["chapters"]["chapters"]:
                print(f"[STEP 5/7] Deriving key_timestamps from chapters (long video)...")
                key_timestamps = _derive_key_timestamps_from_chapters(
                    ai_results["chapters"]["chapters"],
                    video_duration
                )
                ai_results["structured"]["key_timestamps"] = key_timestamps
                print(f"[STEP 5/7] ✓ Derived {len(key_timestamps)} key_timestamps from chapters")

            print(f"[STEP 5/7] ✓ AI content generated")

            # Generate suggested chat prompts
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
            except Exception as e:
                print(f"[STEP 5.5/7] ⚠ Unexpected error generating prompts: {e}")

            # Save notes to database
            print(f"[STEP 6/7] Saving AI-generated notes to database...")
            print(f"  - Summary length: {len(ai_results['structured']['summary'])} chars")
            print(f"  - Bullets: {len(ai_results['structured']['bullets'])} items")
            print(f"  - Chapters: {len(ai_results['chapters']['chapters'])} chapters")
            print(f"  - Flashcards: {len(ai_results['structured']['flashcards'])} cards")

            notes = Notes(
                video_id=video_id,
                summary=ai_results["structured"]["summary"],
                bullets=ai_results["structured"]["bullets"],
                key_timestamps=ai_results["structured"]["key_timestamps"],
                flashcards=ai_results["structured"]["flashcards"],
                action_items=ai_results["structured"]["action_items"],
                topics=ai_results["structured"]["topics"],
                difficulty_level=ai_results["structured"]["difficulty_level"],
                markdown_notes="",
                chapters=ai_results["chapters"]["chapters"],
                notes_model=ai_results["structured"]["model_used"],
                notes_tokens=ai_results["structured"]["tokens_used"],
                chapters_tokens=ai_results["chapters"]["tokens_used"],
                was_truncated="N",
                raw_llm_output={
                    "chapters": ai_results["chapters"],
                    "structured": ai_results["structured"]
                },
                suggested_prompts=suggested_prompts if suggested_prompts else None
            )
            db.add(notes)
            db.commit()
            print(f"[STEP 6/7] ✓ Notes saved to database")

            # Mark as complete
            print(f"[STEP 7/7] Marking video as READY...")
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()
            db.commit()

            video = db.execute(select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if video:
                video.status = VideoStatus.READY
                video.processed_at = datetime.utcnow()
                db.commit()

            # Increment user's videos_analyzed counter
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if user:
                user.videos_analyzed += 1
                db.commit()

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
            error_msg = str(e)
            print(f"\n[ERROR] ❌ YouTube fetch failed!")
            print(f"[ERROR] {error_msg}")

            if job:
                job.status = JobStatus.FAILED
                job.error_message = error_msg
                job.completed_at = datetime.utcnow()
                db.commit()

            video = db.execute(select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if video:
                video.status = VideoStatus.FAILED
                video.failure_reason = error_msg
                db.commit()

            return {"success": False, "error": error_msg}

        except AINotesServiceError as e:
            error_msg = f"AI error: {str(e)}"
            print(f"\n[ERROR] ❌ AI generation failed!")
            print(f"[ERROR] {error_msg}")

            if job:
                job.status = JobStatus.FAILED
                job.error_message = error_msg
                job.completed_at = datetime.utcnow()
                db.commit()

            video = db.execute(select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if video:
                video.status = VideoStatus.FAILED
                video.failure_reason = error_msg
                db.commit()

            return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"\n[ERROR] ❌ Unexpected error!")
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()

            if job:
                job.status = JobStatus.FAILED
                job.error_message = error_msg
                job.completed_at = datetime.utcnow()
                db.commit()

            video = db.execute(select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if video:
                video.status = VideoStatus.FAILED
                video.failure_reason = error_msg
                db.commit()

            return {"success": False, "error": error_msg}


def _generate_ai_content_parallel(
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
        # Use chunked generation for long videos (>10 min) for better coverage
        if video_duration > 600:
            print(f"  [AI] Starting CHUNKED chapters generation (video > 10 min)...")
            result = ai_service.generate_chapters_chunked(
                segments,
                video_duration=video_duration,
                requested_chapters=10
            )
        else:
            print(f"  [AI] Starting chapters generation (short video)...")
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
    print(f"  [AI] Launching 2 parallel AI requests (Groq primary, OpenAI fallback)...")
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


def _derive_key_timestamps_from_chapters(
    chapters: List[Dict[str, Any]],
    video_duration: float
) -> List[Dict[str, Any]]:
    """
    Derive key_timestamps from chapters for full video coverage.

    For long videos, chapters already have good temporal distribution via
    the chunked map-reduce approach. We pick 5-8 chapters as key moments.

    Args:
        chapters: List of chapter dictionaries from generate_chapters_chunked()
        video_duration: Video duration in seconds

    Returns:
        List of key_timestamp dictionaries with label, time (MM:SS), seconds
    """
    if not chapters:
        return []

    # Skip "Introduction" chapter if it exists at 0
    meaningful_chapters = [
        ch for ch in chapters
        if ch.get("start_time", 0) > 0 or ch.get("title", "").lower() != "introduction"
    ]

    # If we have <= 8 chapters, use all of them
    # If we have more, pick 8 distributed across the video (60/40 split)
    if len(meaningful_chapters) <= 8:
        selected = meaningful_chapters
    else:
        # Apply 60/40 temporal distribution
        boundary = video_duration * 0.6
        first_half = [ch for ch in meaningful_chapters if ch.get("start_time", 0) < boundary]
        second_half = [ch for ch in meaningful_chapters if ch.get("start_time", 0) >= boundary]

        # Pick up to 5 from first 60%, up to 3 from last 40%
        selected = first_half[:5] + second_half[:3]

    # Convert to key_timestamp format
    key_timestamps = []
    for ch in selected:
        start_time = ch.get("start_time", 0)
        mins = int(start_time // 60)
        secs = int(start_time % 60)

        key_timestamps.append({
            "label": ch.get("title", "Key moment"),
            "time": f"{mins}:{secs:02d}",
            "seconds": start_time
        })

    # Sort by time
    key_timestamps.sort(key=lambda x: x["seconds"])

    return key_timestamps


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

    print(f"[QUEUE] Enqueued video {video_id} for processing. Job ID: {job.id}")
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
