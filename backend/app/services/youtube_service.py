"""
YouTube service for fetching video metadata and transcripts.

Uses yt-dlp for all YouTube operations - more reliable and resilient than
youtube-transcript-api which gets rate-limited frequently.
"""
import re
import time
import random
import os
from typing import Dict, Any, List
from urllib.parse import urlparse, parse_qs

import requests
import yt_dlp

from app.core.config import settings


# Maximum video duration in seconds (2 hours)
MAX_VIDEO_DURATION = 7200

# Retry configuration - Fail fast for better UX
MAX_RETRIES = 2  # Only retry twice (quick fail)
INITIAL_RETRY_DELAY = 2  # Start with 2 seconds
MAX_RETRY_DELAY = 5  # Max 5 seconds between retries

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# Proxy configuration
def _get_proxy_list() -> List[str]:
    """Get list of proxies from environment."""
    single_proxy = getattr(settings, 'PROXY_URL', None) or os.environ.get('PROXY_URL')
    if single_proxy:
        return [single_proxy]

    proxy_list = getattr(settings, 'PROXY_LIST', None) or os.environ.get('PROXY_LIST', '')
    if proxy_list:
        return [p.strip() for p in proxy_list.split(',') if p.strip()]

    return []

PROXY_LIST = _get_proxy_list()

# Browser to use for cookies (chrome, firefox, safari, edge, opera, brave)
COOKIES_BROWSER = os.environ.get('YOUTUBE_COOKIES_BROWSER', 'chrome')


class YouTubeServiceError(Exception):
    """Custom exception for YouTube service errors."""
    pass


class YouTubeService:
    """Service for interacting with YouTube videos."""

    def _execute_with_retry(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic.
        Handles both 429 (rate limit) and 403 (forbidden/blocked) errors.
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a rate limit or blocked error (both 429 and 403)
                is_rate_limit = '429' in error_str or 'too many requests' in error_str or 'rate limit' in error_str
                is_forbidden = '403' in error_str or 'forbidden' in error_str

                if is_rate_limit or is_forbidden:
                    if attempt < MAX_RETRIES - 1:
                        # Use longer delays for 403 errors as they indicate IP blocking
                        base_delay = INITIAL_RETRY_DELAY * 2 if is_forbidden else INITIAL_RETRY_DELAY
                        delay = min(base_delay * (2 ** attempt), MAX_RETRY_DELAY)
                        jitter = random.uniform(0, delay * 0.2)
                        total_delay = delay + jitter

                        error_type = "Forbidden (IP blocked)" if is_forbidden else "Rate limit"
                        print(f"[YouTube] {error_type} hit, retrying in {total_delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(total_delay)
                        continue
                    else:
                        error_msg = "IP blocked by YouTube" if is_forbidden else "Rate limit exceeded"
                        raise YouTubeServiceError(
                            f"{error_msg} after {MAX_RETRIES} attempts. Please try again later."
                        )
                else:
                    raise

        raise YouTubeServiceError(f"Failed after {MAX_RETRIES} attempts: {str(last_error)}")

    def _get_random_user_agent(self) -> str:
        """Get a random user agent for requests."""
        return random.choice(USER_AGENTS)

    def extract_video_id(self, url: str) -> str:
        """
        Extract YouTube video ID from various URL formats.
        """
        if not url or not isinstance(url, str):
            raise YouTubeServiceError("Invalid YouTube URL")

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
        Fetch video metadata using yt-dlp.
        """
        def _fetch_metadata():
            url = f"https://www.youtube.com/watch?v={video_id}"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'user_agent': self._get_random_user_agent(),
                'ignore_no_formats_error': True,  # We only need metadata, not video formats
                'source_address': '0.0.0.0',  # Force IPv4 to avoid IPv6 rate limits
            }

            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                ydl_opts['proxy'] = proxy
                print(f"[YouTube] Using proxy: {proxy[:30]}...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

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
        Fetch video transcript using yt-dlp.

        Supports multiple languages - GPT-4o handles non-English transcripts directly.
        """
        def _fetch_transcript():
            url = f"https://www.youtube.com/watch?v={video_id}"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language, 'en', 'hi', 'es', 'fr', 'de', 'pt'],
                'user_agent': self._get_random_user_agent(),
                'ignore_no_formats_error': True,  # We only need captions, not video formats
                'source_address': '0.0.0.0',  # Force IPv4 to avoid IPv6 rate limits
            }

            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                ydl_opts['proxy'] = proxy
                print(f"[YouTube] Using proxy: {proxy[:30]}...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                automatic_captions = info.get('automatic_captions', {})
                subtitles = info.get('subtitles', {})

                caption_list = None
                provider = "youtube_auto"
                actual_language = language

                # Simple approach: Get first available caption in native language
                # GPT-4o handles translation to English, so we don't need English captions
                # This avoids rate limits from YouTube's auto-translate feature

                # Priority 1: Manual subtitles (more accurate, less rate-limited)
                if subtitles:
                    first_lang = list(subtitles.keys())[0]
                    caption_list = subtitles[first_lang]
                    actual_language = first_lang
                    provider = "youtube_manual"
                    print(f"[YouTube] Found {first_lang} manual subtitles")

                # Priority 2: Auto-generated captions
                elif automatic_captions:
                    first_lang = list(automatic_captions.keys())[0]
                    caption_list = automatic_captions[first_lang]
                    actual_language = first_lang
                    provider = "youtube_auto"
                    print(f"[YouTube] Found {first_lang} auto-captions")

                if not caption_list:
                    raise YouTubeServiceError("No captions/subtitles available for this video")

                # Get subtitle URL (prefer json3 format)
                subtitle_url = None
                for cap in caption_list:
                    if cap.get('ext') == 'json3':
                        subtitle_url = cap.get('url')
                        break

                if not subtitle_url and caption_list:
                    subtitle_url = caption_list[0].get('url')

                if not subtitle_url:
                    raise YouTubeServiceError("Could not find subtitle URL")

                # Fetch and parse subtitles - use same proxy as yt-dlp
                headers = {'User-Agent': self._get_random_user_agent()}
                proxies = None
                if PROXY_LIST:
                    proxy = random.choice(PROXY_LIST)
                    proxies = {'http': proxy, 'https': proxy}
                response = requests.get(subtitle_url, timeout=30, headers=headers, proxies=proxies)
                response.raise_for_status()

                # Check if response is valid JSON (not HTML error page)
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type or response.text.strip().startswith('<!'):
                    raise YouTubeServiceError("YouTube returned error page instead of subtitles - may be rate limited")

                if not response.text.strip():
                    raise YouTubeServiceError("YouTube returned empty subtitle response")

                try:
                    subtitle_data = response.json()
                except Exception as json_err:
                    # Log first 200 chars to debug
                    print(f"[YouTube] Invalid JSON response: {response.text[:200]}")
                    raise YouTubeServiceError(f"Invalid subtitle data from YouTube: {str(json_err)}")

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

        try:
            return self._execute_with_retry(_fetch_transcript)
        except YouTubeServiceError:
            raise
        except Exception as e:
            raise YouTubeServiceError(f"Failed to fetch transcript: {str(e)}")

    def process_video_url(self, url: str, language: str = "en") -> Dict[str, Any]:
        """
        Complete workflow: extract video ID, fetch metadata and transcript.
        """
        video_id = self.extract_video_id(url)
        metadata = self.get_video_metadata(video_id)
        transcript = self.get_transcript(video_id, language)

        return {
            "video_id": video_id,
            "metadata": metadata,
            "transcript": transcript
        }
