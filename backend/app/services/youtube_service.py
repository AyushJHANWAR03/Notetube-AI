"""
YouTube service for fetching video metadata and transcripts.

Uses youtube-transcript-api as primary method (more reliable, fewer rate limits)
with yt-dlp as fallback. Supports proxy rotation for rate limit bypass.
"""
import re
import time
import random
import os
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs

import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._errors import YouTubeRequestFailed

from app.core.config import settings


# Maximum video duration in seconds (2 hours)
MAX_VIDEO_DURATION = 7200

# Retry configuration - Enabled with exponential backoff
MAX_RETRIES = 5  # Retry up to 5 times
INITIAL_RETRY_DELAY = 5  # Start with 5 seconds
MAX_RETRY_DELAY = 60  # Max 60 seconds between retries

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# Proxy configuration
# Set PROXY_URL in .env for a single proxy: http://user:pass@host:port
# Or set PROXY_LIST for multiple proxies (comma-separated)
# Free proxies are unreliable - consider paid services like:
# - Bright Data (formerly Luminati)
# - Smartproxy
# - Oxylabs
# - ScraperAPI (has YouTube-specific endpoints)
def _get_proxy_list() -> List[str]:
    """Get list of proxies from environment."""
    # Single proxy
    single_proxy = getattr(settings, 'PROXY_URL', None) or os.environ.get('PROXY_URL')
    if single_proxy:
        return [single_proxy]

    # Multiple proxies (comma-separated)
    proxy_list = getattr(settings, 'PROXY_LIST', None) or os.environ.get('PROXY_LIST', '')
    if proxy_list:
        return [p.strip() for p in proxy_list.split(',') if p.strip()]

    return []

PROXY_LIST = _get_proxy_list()


class YouTubeServiceError(Exception):
    """Custom exception for YouTube service errors."""
    pass


class YouTubeService:
    """Service for interacting with YouTube videos."""

    def _execute_with_retry(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result

        Raises:
            YouTubeServiceError: If all retries fail
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a rate limit error
                if '429' in error_str or 'too many requests' in error_str or 'rate limit' in error_str:
                    if attempt < MAX_RETRIES - 1:
                        # Calculate exponential backoff with jitter
                        delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                        jitter = random.uniform(0, delay * 0.1)  # Add 0-10% jitter
                        total_delay = delay + jitter

                        print(f"Rate limit hit, retrying in {total_delay:.2f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(total_delay)
                        continue
                    else:
                        raise YouTubeServiceError(
                            f"Rate limit exceeded after {MAX_RETRIES} attempts. Please try again later."
                        )
                else:
                    # Non-rate-limit error, don't retry
                    raise

        # If we get here, all retries failed
        raise YouTubeServiceError(f"Failed after {MAX_RETRIES} attempts: {str(last_error)}")

    def _get_random_user_agent(self) -> str:
        """Get a random user agent for requests."""
        return random.choice(USER_AGENTS)

    def extract_video_id(self, url: str) -> str:
        """
        Extract YouTube video ID from various URL formats.

        Args:
            url: YouTube URL (watch, short, embed, etc.)

        Returns:
            Video ID string

        Raises:
            YouTubeServiceError: If URL is invalid or video ID cannot be extracted
        """
        if not url or not isinstance(url, str):
            raise YouTubeServiceError("Invalid YouTube URL")

        # Patterns for different YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise YouTubeServiceError("Invalid YouTube URL - could not extract video ID")

    def get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch video metadata using yt-dlp with retry logic.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary containing video metadata

        Raises:
            YouTubeServiceError: If metadata cannot be fetched or video exceeds duration limit
        """
        def _fetch_metadata():
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Configure yt-dlp options with random user agent
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'user_agent': self._get_random_user_agent(),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Check duration limit
                duration = info.get('duration', 0)
                if duration > MAX_VIDEO_DURATION:
                    raise YouTubeServiceError(
                        f"Video duration exceeds maximum allowed length of {MAX_VIDEO_DURATION // 3600} hours"
                    )

                return {
                    "video_id": video_id,
                    "title": info.get('title', 'Unknown'),
                    "duration_seconds": duration,
                    "thumbnail_url": info.get('thumbnail', ''),
                    "channel": info.get('uploader', 'Unknown')
                }

        try:
            return self._execute_with_retry(_fetch_metadata)
        except YouTubeServiceError:
            raise
        except Exception as e:
            raise YouTubeServiceError(f"Failed to fetch video metadata: {str(e)}")

    def get_transcript(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch video transcript using multiple methods for reliability.

        Primary: youtube-transcript-api (lightweight, better rate limits)
        Fallback: yt-dlp (more comprehensive but heavier)

        Args:
            video_id: YouTube video ID
            language: Language code (default: "en")

        Returns:
            Dictionary containing transcript data

        Raises:
            YouTubeServiceError: If transcript cannot be fetched
        """
        api_error_msg = None

        # Try youtube-transcript-api first (more reliable, fewer rate limits)
        try:
            return self._get_transcript_via_api(video_id, language)
        except Exception as e:
            api_error_msg = str(e)
            print(f"youtube-transcript-api failed: {api_error_msg}, trying yt-dlp fallback...")

        # Fallback to yt-dlp
        try:
            return self._get_transcript_via_ytdlp(video_id, language)
        except Exception as e:
            raise YouTubeServiceError(
                f"All transcript methods failed. API error: {api_error_msg}, yt-dlp error: {e}"
            )

    def _get_transcript_via_api(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch transcript using youtube-transcript-api library.
        This is more lightweight and has better rate limit handling.

        Supports:
        - English transcripts (manual or auto-generated)
        - Non-English transcripts (Hindi, Spanish, etc.) - returned as-is for AI processing

        NOTE: We NO LONGER translate non-English transcripts to avoid YouTube rate limits.
        GPT-4o handles Hindi/Spanish/etc. transcripts directly with excellent results.
        """
        def _fetch():
            # Use proxy if available
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": proxy, "https": proxy}
                print(f"[Transcript] Using proxy: {proxy[:30]}...")

            # Try to get transcript in preferred language order
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)

            transcript = None
            actual_language = language
            provider = "youtube_auto"

            # Strategy 1: Try English manual transcripts first (highest quality)
            try:
                transcript = transcript_list.find_manually_created_transcript(['en', language])
                provider = "youtube_manual"
                actual_language = transcript.language_code
                print(f"[Transcript] Found English manual transcript")
            except NoTranscriptFound:
                pass

            # Strategy 2: Try English auto-generated
            if not transcript:
                try:
                    transcript = transcript_list.find_generated_transcript(['en', language])
                    provider = "youtube_auto"
                    actual_language = transcript.language_code
                    print(f"[Transcript] Found English auto-generated transcript")
                except NoTranscriptFound:
                    pass

            # Strategy 3: Try ANY available transcript WITHOUT translation
            # GPT-4o handles Hindi, Spanish, etc. natively - no need to translate
            # This avoids YouTube's aggressive rate limiting on translation API
            if not transcript:
                try:
                    # Get list of all available transcripts
                    available = list(transcript_list)
                    if available:
                        # Prefer manual over auto-generated
                        manual_transcripts = [t for t in available if not t.is_generated]
                        auto_transcripts = [t for t in available if t.is_generated]

                        if manual_transcripts:
                            transcript = manual_transcripts[0]
                            provider = "youtube_manual"
                            actual_language = transcript.language_code
                            print(f"[Transcript] Found {actual_language} manual transcript (no translation)")
                        elif auto_transcripts:
                            transcript = auto_transcripts[0]
                            provider = "youtube_auto"
                            actual_language = transcript.language_code
                            print(f"[Transcript] Found {actual_language} auto-generated transcript (no translation)")
                except Exception as e:
                    print(f"[Transcript] Failed to find any transcript: {e}")

            if not transcript:
                raise YouTubeServiceError("No captions/subtitles available for this video")

            # Fetch the actual transcript data
            transcript_data = transcript.fetch()

            if not transcript_data:
                raise YouTubeServiceError("Transcript is empty")

            # Convert to our format
            segments = []
            raw_text_parts = []

            for entry in transcript_data:
                text = entry.get('text', '').strip()
                if text:
                    segments.append({
                        "text": text,
                        "start": entry.get('start', 0),
                        "duration": entry.get('duration', 0)
                    })
                    raw_text_parts.append(text)

            raw_text = " ".join(raw_text_parts)

            return {
                "language_code": actual_language,
                "provider": provider,
                "raw_text": raw_text,
                "segments": segments
            }

        return self._execute_with_retry(_fetch)

    def _get_transcript_via_ytdlp(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch transcript using yt-dlp as fallback method.
        Tries multiple languages including Hindi for Indian content.

        NOTE: We NO LONGER translate - GPT-4o handles Hindi/Spanish/etc. directly.
        This avoids YouTube's aggressive rate limiting on translation endpoints.
        """
        def _fetch_transcript():
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Configure yt-dlp to get subtitle URLs with random user agent
            # Include common languages for broader support
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language, 'en', 'hi', 'es', 'fr', 'de', 'pt'],
                'user_agent': self._get_random_user_agent(),
            }

            # Use proxy if available
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                ydl_opts['proxy'] = proxy
                print(f"[yt-dlp] Using proxy: {proxy[:30]}...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                automatic_captions = info.get('automatic_captions', {})
                subtitles = info.get('subtitles', {})

                caption_list = None
                provider = "youtube_auto"
                actual_language = language
                source_language = None  # Track original language for translation

                # Priority order for caption selection - PREFER ENGLISH FIRST
                # 1. English auto-captions (best for our use case)
                # 2. English manual subtitles
                # 3. Requested language
                # 4. Any other language (will need translation)

                # First, try to get English directly
                if 'en' in automatic_captions:
                    caption_list = automatic_captions['en']
                    actual_language = 'en'
                    provider = "youtube_auto"
                    print(f"[yt-dlp] Found English auto-captions")
                elif 'en' in subtitles:
                    caption_list = subtitles['en']
                    actual_language = 'en'
                    provider = "youtube_manual"
                    print(f"[yt-dlp] Found English manual subtitles")

                # If no English, try to get translated version
                # YouTube auto-captions often have "en-orig" or translated versions
                if not caption_list:
                    # Look for any English variant in auto-captions
                    for lang_code in automatic_captions.keys():
                        if lang_code.startswith('en'):
                            caption_list = automatic_captions[lang_code]
                            actual_language = 'en'
                            provider = "youtube_auto_translated"
                            print(f"[yt-dlp] Found English variant: {lang_code}")
                            break

                # If still no English, get the source language and use it directly
                # GPT-4o handles Hindi, Spanish, etc. natively - no translation needed!
                if not caption_list:
                    lang_priority = ['hi', 'es', 'fr', 'de', 'pt']
                    for lang in lang_priority:
                        if lang in automatic_captions:
                            caption_list = automatic_captions[lang]
                            actual_language = lang
                            source_language = lang
                            provider = "youtube_auto"
                            print(f"[yt-dlp] Found {lang} auto-captions (GPT-4o will process directly)")
                            break
                        if lang in subtitles:
                            caption_list = subtitles[lang]
                            actual_language = lang
                            source_language = lang
                            provider = "youtube_manual"
                            print(f"[yt-dlp] Found {lang} manual subtitles (GPT-4o will process directly)")
                            break

                # Last resort: any available caption
                if not caption_list:
                    if automatic_captions:
                        first_lang = list(automatic_captions.keys())[0]
                        caption_list = automatic_captions[first_lang]
                        actual_language = first_lang
                        source_language = first_lang
                        provider = "youtube_auto"
                        print(f"[yt-dlp] Found {first_lang} auto-captions (fallback)")
                    elif subtitles:
                        first_lang = list(subtitles.keys())[0]
                        caption_list = subtitles[first_lang]
                        actual_language = first_lang
                        source_language = first_lang
                        provider = "youtube_manual"
                        print(f"[yt-dlp] Found {first_lang} manual subtitles (fallback)")

                if not caption_list:
                    raise YouTubeServiceError("No captions/subtitles available for this video")

                subtitle_url = None
                for cap in caption_list:
                    if cap.get('ext') == 'json3':
                        subtitle_url = cap.get('url')
                        break

                if not subtitle_url and caption_list:
                    subtitle_url = caption_list[0].get('url')

                if not subtitle_url:
                    raise YouTubeServiceError("Could not find subtitle URL")

                headers = {'User-Agent': self._get_random_user_agent()}
                response = requests.get(subtitle_url, timeout=30, headers=headers)
                response.raise_for_status()

                subtitle_data = response.json()

                segments = []
                raw_text_parts = []
                events = subtitle_data.get('events', [])

                for event in events:
                    segs = event.get('segs', [])
                    if segs:
                        text = ''.join([seg.get('utf8', '') for seg in segs]).strip()
                        if text:
                            segments.append({
                                "text": text,
                                "start": event.get('tStartMs', 0) / 1000.0,
                                "duration": event.get('dDurationMs', 0) / 1000.0
                            })
                            raw_text_parts.append(text)

                if not segments:
                    raise YouTubeServiceError("Transcript is empty")

                raw_text = " ".join(raw_text_parts)

                return {
                    "language_code": actual_language,
                    "provider": provider,
                    "raw_text": raw_text,
                    "segments": segments
                }

        return self._execute_with_retry(_fetch_transcript)

    def process_video_url(self, url: str, language: str = "en") -> Dict[str, Any]:
        """
        Complete workflow: extract video ID, fetch metadata and transcript.

        Args:
            url: YouTube URL
            language: Transcript language (default: "en")

        Returns:
            Dictionary containing video_id, metadata, and transcript

        Raises:
            YouTubeServiceError: If any step fails
        """
        # Extract video ID
        video_id = self.extract_video_id(url)

        # Fetch metadata
        metadata = self.get_video_metadata(video_id)

        # Fetch transcript
        transcript = self.get_transcript(video_id, language)

        return {
            "video_id": video_id,
            "metadata": metadata,
            "transcript": transcript
        }
