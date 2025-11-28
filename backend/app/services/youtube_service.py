"""
YouTube service for fetching video metadata and transcripts.

Uses Supadata.ai for transcripts (handles rate limits) and yt-dlp for metadata/fallback.
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

# Supadata.ai configuration (primary transcript provider)
SUPADATA_API_KEY = os.environ.get('SUPADATA_API_KEY', '')
SUPADATA_BASE_URL = "https://api.supadata.ai/v1/youtube/transcript"

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# Proxy configuration (for fallback yt-dlp method)
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
                print(f"[YouTube] Using proxy for metadata: {proxy[:30]}...")

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

    def _get_transcript_supadata(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch transcript using Supadata.ai - handles rate limits automatically.
        This is the PRIMARY method for fetching transcripts.
        Cost: 1 credit per transcript ($17/month for 3000 credits)
        """
        print(f"[YouTube] Fetching transcript via Supadata.ai for {video_id}")

        params = {
            'videoId': video_id,
            'lang': language,
            'text': 'false'  # Get segments with timestamps
        }

        headers = {
            'x-api-key': SUPADATA_API_KEY
        }

        try:
            response = requests.get(SUPADATA_BASE_URL, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if 'error' in data:
                raise YouTubeServiceError(f"Supadata error: {data.get('message', data.get('error'))}")

            content = data.get('content', [])

            if not content:
                raise YouTubeServiceError("No transcripts available for this video")

            # Build segments and raw text
            segments = []
            raw_text_parts = []

            for item in content:
                text = item.get('text', '').strip()
                if text:
                    # Supadata returns offset in milliseconds, convert to seconds
                    start_ms = item.get('offset', 0)
                    duration_ms = item.get('duration', 0)
                    segments.append({
                        "text": text,
                        "start": start_ms / 1000.0,
                        "duration": duration_ms / 1000.0
                    })
                    raw_text_parts.append(text)

            if not segments:
                raise YouTubeServiceError("Transcript is empty")

            raw_text = " ".join(raw_text_parts)
            actual_language = data.get('lang', language)

            print(f"[YouTube] Supadata.ai success: {len(segments)} segments")

            return {
                "language_code": actual_language,
                "provider": "supadata",
                "raw_text": raw_text,
                "segments": segments
            }

        except requests.exceptions.RequestException as e:
            raise YouTubeServiceError(f"Supadata request failed: {str(e)}")
        except Exception as e:
            if isinstance(e, YouTubeServiceError):
                raise
            raise YouTubeServiceError(f"Supadata error: {str(e)}")

    def _get_transcript_ytdlp(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch transcript using yt-dlp - FALLBACK method.
        Only used if SearchAPI.io fails.
        """
        print(f"[YouTube] Fallback: Fetching transcript via yt-dlp for {video_id}")

        def _fetch_transcript():
            url = f"https://www.youtube.com/watch?v={video_id}"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language, 'en', 'hi', 'es', 'fr', 'de', 'pt'],
                'user_agent': self._get_random_user_agent(),
                'ignore_no_formats_error': True,
                'source_address': '0.0.0.0',
            }

            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                ydl_opts['proxy'] = proxy
                print(f"[YouTube] Using proxy for transcript: {proxy[:30]}...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                automatic_captions = info.get('automatic_captions', {})
                subtitles = info.get('subtitles', {})

                caption_list = None
                provider = "youtube_auto"
                actual_language = language

                # Priority 1: Manual subtitles
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

                # Fetch subtitles
                headers = {'User-Agent': self._get_random_user_agent()}
                proxies = None
                if PROXY_LIST:
                    proxy = random.choice(PROXY_LIST)
                    proxies = {'http': proxy, 'https': proxy}
                response = requests.get(subtitle_url, timeout=30, headers=headers, proxies=proxies)
                response.raise_for_status()

                # Validate response
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type or response.text.strip().startswith('<!'):
                    raise YouTubeServiceError("YouTube returned error page - may be rate limited")

                if not response.text.strip():
                    raise YouTubeServiceError("YouTube returned empty subtitle response")

                try:
                    subtitle_data = response.json()
                except Exception as json_err:
                    print(f"[YouTube] Invalid JSON: {response.text[:200]}")
                    raise YouTubeServiceError(f"Invalid subtitle data: {str(json_err)}")

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

    def get_transcript(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch video transcript - uses Supadata.ai as primary, yt-dlp as fallback.
        """
        # Try Supadata.ai first (handles rate limits, $17/month for 3000 transcripts)
        try:
            return self._get_transcript_supadata(video_id, language)
        except YouTubeServiceError as e:
            print(f"[YouTube] Supadata.ai failed: {e}, trying yt-dlp fallback...")

        # Fallback to yt-dlp
        return self._get_transcript_ytdlp(video_id, language)

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
