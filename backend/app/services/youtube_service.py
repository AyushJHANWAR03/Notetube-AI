"""
YouTube service for fetching video metadata and transcripts.

Uses YouTube Data API v3 for metadata and Supadata.ai for transcripts.
"""
import re
import os
from typing import Dict, Any

import requests

from app.core.config import settings


# YouTube Data API v3 configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '') or getattr(settings, 'YOUTUBE_API_KEY', '') or ''
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3/videos"

# Supadata.ai configuration (transcript provider)
SUPADATA_API_KEY = os.environ.get('SUPADATA_API_KEY', '')
SUPADATA_BASE_URL = "https://api.supadata.ai/v1/youtube/transcript"


class YouTubeServiceError(Exception):
    """Custom exception for YouTube service errors."""
    pass


def _parse_iso8601_duration(duration: str) -> int:
    """
    Parse ISO 8601 duration string (e.g., PT1H2M3S) to seconds.
    """
    import re
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


class YouTubeService:
    """Service for interacting with YouTube videos."""

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

    def _get_metadata_youtube_api(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch video metadata using YouTube Data API v3.
        Returns title, duration, thumbnail, and channel name.
        """
        if not YOUTUBE_API_KEY:
            print("[YouTube] No API key configured, falling back to oEmbed")
            return None

        params = {
            'id': video_id,
            'part': 'snippet,contentDetails',
            'key': YOUTUBE_API_KEY
        }

        try:
            print(f"[YouTube] Fetching metadata via YouTube Data API for {video_id}")
            response = requests.get(YOUTUBE_API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get('items', [])
            if not items:
                print(f"[YouTube] Video not found: {video_id}")
                return None

            video_data = items[0]
            snippet = video_data.get('snippet', {})
            content_details = video_data.get('contentDetails', {})

            # Parse duration from ISO 8601 format
            duration_iso = content_details.get('duration', 'PT0S')
            duration_seconds = _parse_iso8601_duration(duration_iso)

            # Get best thumbnail
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = (
                thumbnails.get('maxres', {}).get('url') or
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or
                thumbnails.get('default', {}).get('url') or
                f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            )

            title = snippet.get('title', 'Unknown')
            channel = snippet.get('channelTitle', 'Unknown')

            print(f"[YouTube] API success: {title} ({duration_seconds}s)")

            return {
                "video_id": video_id,
                "title": title,
                "duration_seconds": duration_seconds,
                "thumbnail_url": thumbnail_url,
                "channel": channel
            }

        except requests.exceptions.RequestException as e:
            print(f"[YouTube] API request failed: {str(e)}")
            return None
        except Exception as e:
            print(f"[YouTube] API error: {str(e)}")
            return None

    def _get_metadata_oembed(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch basic metadata using YouTube's oEmbed API (fallback).
        Returns title, thumbnail, and channel name (no duration).
        """
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"

        try:
            print(f"[YouTube] Fetching metadata via oEmbed for {video_id}")
            response = requests.get(oembed_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            title = data.get('title', 'Unknown')
            print(f"[YouTube] oEmbed success: {title}")

            return {
                "video_id": video_id,
                "title": title,
                "duration_seconds": 0,  # oEmbed doesn't provide duration
                "thumbnail_url": data.get('thumbnail_url', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                "channel": data.get('author_name', 'Unknown')
            }
        except Exception as e:
            print(f"[YouTube] oEmbed failed: {str(e)}")
            return None

    def get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch video metadata. Tries YouTube Data API first, falls back to oEmbed.
        """
        # Try YouTube Data API first (has duration)
        result = self._get_metadata_youtube_api(video_id)
        if result:
            return result

        # Fall back to oEmbed (no duration but reliable)
        result = self._get_metadata_oembed(video_id)
        if result:
            return result

        raise YouTubeServiceError(f"Failed to fetch video metadata for {video_id}")

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

            # Check for errors - provide user-friendly messages
            if 'error' in data:
                error_type = data.get('error', '')
                if error_type == 'transcript-unavailable' or 'unavailable' in error_type.lower():
                    raise YouTubeServiceError(
                        "This video doesn't have captions/subtitles available. "
                        "NoteTube can only process videos with captions enabled."
                    )
                raise YouTubeServiceError(f"Supadata error: {data.get('message', data.get('error'))}")

            content = data.get('content', [])

            if not content:
                raise YouTubeServiceError(
                    "This video doesn't have captions/subtitles available. "
                    "NoteTube can only process videos with captions enabled."
                )

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

    def get_transcript(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch video transcript using Supadata.ai.
        """
        return self._get_transcript_supadata(video_id, language)

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
