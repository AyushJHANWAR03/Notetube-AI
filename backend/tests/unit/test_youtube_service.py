"""
Unit tests for YouTubeService.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.youtube_service import YouTubeService, YouTubeServiceError


class TestYouTubeServiceURLValidation:
    """Test YouTube URL validation and video ID extraction."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = YouTubeService()

    def test_extract_video_id_from_watch_url(self):
        """Should extract video ID from standard watch URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = self.service.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_from_short_url(self):
        """Should extract video ID from short youtu.be URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = self.service.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_with_timestamp(self):
        """Should extract video ID from URL with timestamp."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"
        video_id = self.service.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_with_playlist(self):
        """Should extract video ID from URL with playlist parameter."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        video_id = self.service.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_from_embed_url(self):
        """Should extract video ID from embed URL."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = self.service.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_invalid_url_raises_error(self):
        """Should raise error for invalid YouTube URL."""
        url = "https://vimeo.com/123456"
        with pytest.raises(YouTubeServiceError, match="Invalid YouTube URL"):
            self.service.extract_video_id(url)

    def test_empty_url_raises_error(self):
        """Should raise error for empty URL."""
        with pytest.raises(YouTubeServiceError, match="Invalid YouTube URL"):
            self.service.extract_video_id("")

    def test_malformed_url_raises_error(self):
        """Should raise error for malformed URL."""
        url = "not a url at all"
        with pytest.raises(YouTubeServiceError, match="Invalid YouTube URL"):
            self.service.extract_video_id(url)


class TestYouTubeServiceMetadata:
    """Test fetching video metadata from YouTube."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = YouTubeService()

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_get_video_metadata_success(self, mock_ydl_class):
        """Should fetch video metadata successfully."""
        # Mock yt-dlp response
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            'title': 'System Design Interview',
            'duration': 3245,  # 54 minutes
            'thumbnail': 'https://i.ytimg.com/vi/test/maxresdefault.jpg',
            'uploader': 'Tech Interviews'
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        metadata = self.service.get_video_metadata("dQw4w9WgXcQ")

        assert metadata["video_id"] == "dQw4w9WgXcQ"
        assert metadata["title"] == "System Design Interview"
        assert metadata["duration_seconds"] == 3245
        assert metadata["thumbnail_url"] == "https://i.ytimg.com/vi/test/maxresdefault.jpg"
        assert metadata["channel"] == "Tech Interviews"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_video_too_long_raises_error(self, mock_ydl_class):
        """Should raise error if video exceeds 2 hour limit."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            'duration': 7300  # 2 hours 1 minute 40 seconds
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(YouTubeServiceError, match="Video duration exceeds maximum"):
            self.service.get_video_metadata("dQw4w9WgXcQ")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_video_not_found_raises_error(self, mock_ydl_class):
        """Should raise error if video does not exist."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Video unavailable")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(YouTubeServiceError, match="Failed to fetch video metadata"):
            self.service.get_video_metadata("invalidvid")


class TestYouTubeServiceTranscript:
    """Test fetching video transcript."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = YouTubeService()

    @patch('app.services.youtube_service.requests.get')
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_get_transcript_success(self, mock_ydl_class, mock_requests_get):
        """Should fetch transcript successfully."""
        # Mock yt-dlp to return subtitle URLs
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            'automatic_captions': {
                'en': [
                    {'ext': 'json3', 'url': 'https://youtube.com/api/timedtext?test'}
                ]
            },
            'subtitles': {}
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Mock requests to return json3 format
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'events': [
                {'segs': [{'utf8': 'Hello everyone'}], 'tStartMs': 500, 'dDurationMs': 2000},
                {'segs': [{'utf8': "Today we'll discuss"}], 'tStartMs': 2500, 'dDurationMs': 1800},
                {'segs': [{'utf8': 'system design'}], 'tStartMs': 4300, 'dDurationMs': 1500}
            ]
        }
        mock_requests_get.return_value = mock_response

        result = self.service.get_transcript("dQw4w9WgXcQ")

        assert result["language_code"] == "en"
        assert result["provider"] == "youtube_auto"
        assert "Hello everyone" in result["raw_text"]
        assert "system design" in result["raw_text"]
        assert len(result["segments"]) == 3
        assert result["segments"][0]["text"] == "Hello everyone"
        assert result["segments"][0]["start"] == 0.5

    @patch('app.services.youtube_service.requests.get')
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_get_transcript_multiple_languages(self, mock_ydl_class, mock_requests_get):
        """Should fetch transcript in available language."""
        # Mock yt-dlp to return Spanish subtitles
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            'automatic_captions': {
                'es': [
                    {'ext': 'json3', 'url': 'https://youtube.com/api/timedtext?test'}
                ]
            },
            'subtitles': {}
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Mock requests to return json3 format
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'events': [
                {'segs': [{'utf8': 'Hola a todos'}], 'tStartMs': 500, 'dDurationMs': 2000}
            ]
        }
        mock_requests_get.return_value = mock_response

        result = self.service.get_transcript("dQw4w9WgXcQ", language="es")

        assert result["language_code"] == "es"
        assert "Hola a todos" in result["raw_text"]

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_transcript_not_available_raises_error(self, mock_ydl_class):
        """Should raise error if transcript not available."""
        # Mock yt-dlp to return no captions
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            'automatic_captions': {},
            'subtitles': {}
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(YouTubeServiceError, match="No captions/subtitles available"):
            self.service.get_transcript("novideo")

    @patch('app.services.youtube_service.requests.get')
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_empty_transcript_raises_error(self, mock_ydl_class, mock_requests_get):
        """Should raise error if transcript is empty."""
        # Mock yt-dlp to return subtitle URLs
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            'automatic_captions': {
                'en': [
                    {'ext': 'json3', 'url': 'https://youtube.com/api/timedtext?test'}
                ]
            },
            'subtitles': {}
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Mock requests to return empty events
        mock_response = MagicMock()
        mock_response.json.return_value = {'events': []}
        mock_requests_get.return_value = mock_response

        with pytest.raises(YouTubeServiceError, match="Transcript is empty"):
            self.service.get_transcript("dQw4w9WgXcQ")


class TestYouTubeServiceIntegration:
    """Test complete video processing workflow."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = YouTubeService()

    @patch('app.services.youtube_service.requests.get')
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_process_video_url_success(self, mock_ydl_class, mock_requests_get):
        """Should process complete YouTube URL successfully."""
        # Mock yt-dlp for both metadata and transcript fetching
        mock_ydl = MagicMock()

        # First call is for metadata
        # Second call is for transcript
        mock_ydl.extract_info.side_effect = [
            {
                'title': 'Test Video',
                'duration': 600,
                'thumbnail': 'https://test.jpg',
                'uploader': 'Test Channel'
            },
            {
                'automatic_captions': {
                    'en': [
                        {'ext': 'json3', 'url': 'https://youtube.com/api/timedtext?test'}
                    ]
                },
                'subtitles': {}
            }
        ]
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Mock requests to return json3 format
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'events': [
                {'segs': [{'utf8': 'Test content'}], 'tStartMs': 0, 'dDurationMs': 1000}
            ]
        }
        mock_requests_get.return_value = mock_response

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = self.service.process_video_url(url)

        assert result["video_id"] == "dQw4w9WgXcQ"
        assert result["metadata"]["title"] == "Test Video"
        assert result["metadata"]["duration_seconds"] == 600
        assert result["transcript"]["language_code"] == "en"
        assert "Test content" in result["transcript"]["raw_text"]
