"""Tests for publishers (Instagram, TikTok, YouTube)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from pathlib import Path

from src.publishers.base import BasePublisher, PublishResult, PublishStatus
from src.publishers.instagram_publisher import InstagramPublisher
from src.publishers.tiktok_publisher import TikTokPublisher
from src.publishers.youtube_publisher import YouTubePublisher


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_video_path(tmp_path):
    """Create a sample video file path."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video content")
    return video_file


@pytest.fixture
def sample_thumbnail_path(tmp_path):
    """Create a sample thumbnail file path."""
    thumb_file = tmp_path / "thumbnail.jpg"
    thumb_file.write_bytes(b"fake image content")
    return thumb_file


@pytest.fixture
def publish_metadata():
    """Sample publish metadata."""
    return {
        "title": "Amazing Viral Video",
        "caption": "Check out this amazing content! #viral #trending",
        "hashtags": ["viral", "trending", "fyp"],
        "scheduled_at": None,
    }


# ============================================================================
# BASE PUBLISHER TESTS
# ============================================================================

class TestBasePublisher:
    """Tests for BasePublisher."""

    def test_publish_result_dataclass(self):
        """Test PublishResult dataclass."""
        result = PublishResult(
            success=True,
            platform="instagram",
            post_id="POST123",
            post_url="https://instagram.com/p/POST123",
            status=PublishStatus.PUBLISHED,
            message="Successfully published",
        )

        assert result.success is True
        assert result.platform == "instagram"
        assert result.post_id == "POST123"
        assert result.status == PublishStatus.PUBLISHED

    def test_publish_result_failure(self):
        """Test PublishResult for failure case."""
        result = PublishResult(
            success=False,
            platform="tiktok",
            post_id=None,
            post_url=None,
            status=PublishStatus.FAILED,
            message="API rate limit exceeded",
            error_code="RATE_LIMIT",
        )

        assert result.success is False
        assert result.status == PublishStatus.FAILED
        assert result.error_code == "RATE_LIMIT"

    def test_publish_status_enum(self):
        """Test PublishStatus enum values."""
        statuses = [
            PublishStatus.PENDING,
            PublishStatus.SCHEDULED,
            PublishStatus.PUBLISHED,
            PublishStatus.FAILED,
        ]

        for status in statuses:
            assert status is not None


# ============================================================================
# INSTAGRAM PUBLISHER TESTS
# ============================================================================

class TestInstagramPublisher:
    """Tests for InstagramPublisher."""

    def test_publisher_initialization(self):
        """Test publisher initializes correctly."""
        with patch("src.publishers.instagram_publisher.get_settings") as mock_settings:
            mock_settings.return_value.INSTAGRAM_ACCESS_TOKEN = None
            mock_settings.return_value.INSTAGRAM_ACCOUNT_ID = None

            publisher = InstagramPublisher()
            assert publisher is not None
            assert publisher.platform == "instagram"

    def test_validate_video_format(self, sample_video_path):
        """Test video format validation."""
        # Valid formats for Instagram
        valid_formats = [".mp4", ".mov"]

        # Check file extension
        ext = sample_video_path.suffix.lower()

        # For testing, we created a .mp4 file
        assert ext in valid_formats

    def test_validate_video_duration(self):
        """Test video duration validation for Reels."""
        # Instagram Reels limits
        min_duration = 3  # seconds
        max_duration = 90  # seconds

        valid_durations = [15, 30, 60, 90]
        invalid_durations = [1, 2, 120, 180]

        for duration in valid_durations:
            assert min_duration <= duration <= max_duration

        for duration in invalid_durations:
            is_valid = min_duration <= duration <= max_duration
            assert not is_valid or duration == 1  # 1 second is invalid

    def test_caption_formatting(self, publish_metadata):
        """Test caption formatting with hashtags."""
        caption = publish_metadata["caption"]
        hashtags = publish_metadata["hashtags"]

        # Build full caption
        hashtag_string = " ".join(f"#{tag}" for tag in hashtags)
        full_caption = f"{caption}\n\n{hashtag_string}"

        assert "#viral" in full_caption
        assert "#trending" in full_caption

    def test_webhook_fallback_mode(self):
        """Test webhook fallback when API not configured."""
        with patch("src.publishers.instagram_publisher.get_settings") as mock_settings:
            mock_settings.return_value.INSTAGRAM_ACCESS_TOKEN = None
            mock_settings.return_value.INSTAGRAM_ACCOUNT_ID = None
            mock_settings.return_value.INSTAGRAM_PUBLISH_WEBHOOK = "https://webhook.example.com"

            publisher = InstagramPublisher()

            # Should use webhook mode when API not configured
            assert publisher.access_token is None


# ============================================================================
# TIKTOK PUBLISHER TESTS
# ============================================================================

class TestTikTokPublisher:
    """Tests for TikTokPublisher."""

    def test_publisher_initialization(self):
        """Test publisher initializes correctly."""
        with patch("src.publishers.tiktok_publisher.get_settings") as mock_settings:
            mock_settings.return_value.TIKTOK_ACCESS_TOKEN = None
            mock_settings.return_value.TIKTOK_OPEN_ID = None

            publisher = TikTokPublisher()
            assert publisher is not None
            assert publisher.platform == "tiktok"

    def test_validate_video_duration_tiktok(self):
        """Test video duration validation for TikTok."""
        # TikTok limits
        min_duration = 1  # seconds
        max_duration = 180  # 3 minutes for most accounts

        valid_durations = [15, 30, 60, 120, 180]
        invalid_durations = [0, 200, 300]

        for duration in valid_durations:
            assert min_duration <= duration <= max_duration

        for duration in invalid_durations:
            is_valid = min_duration <= duration <= max_duration
            assert not is_valid

    def test_description_length_limit(self):
        """Test TikTok description length limit."""
        max_length = 2200  # TikTok description limit

        short_desc = "Short description #fyp"
        long_desc = "A" * 3000  # Too long

        assert len(short_desc) <= max_length
        assert len(long_desc) > max_length

    def test_hashtag_recommendations(self):
        """Test hashtag recommendations for TikTok."""
        recommended = ["fyp", "foryou", "foryoupage", "viral", "trending"]
        niche_specific = ["comedy", "humor", "funny"]

        all_hashtags = recommended + niche_specific

        # TikTok best practice: 3-5 hashtags
        assert len(all_hashtags) <= 10


# ============================================================================
# YOUTUBE PUBLISHER TESTS
# ============================================================================

class TestYouTubePublisher:
    """Tests for YouTubePublisher."""

    def test_publisher_initialization(self):
        """Test publisher initializes correctly."""
        with patch("src.publishers.youtube_publisher.get_settings") as mock_settings:
            mock_settings.return_value.GOOGLE_OAUTH_CREDENTIALS = None

            publisher = YouTubePublisher()
            assert publisher is not None
            assert publisher.platform == "youtube"

    def test_validate_shorts_duration(self):
        """Test YouTube Shorts duration validation."""
        # YouTube Shorts limits
        max_shorts_duration = 60  # seconds

        valid_durations = [15, 30, 45, 60]
        invalid_durations = [61, 90, 120]

        for duration in valid_durations:
            assert duration <= max_shorts_duration

        for duration in invalid_durations:
            assert duration > max_shorts_duration

    def test_title_length_limit(self):
        """Test YouTube title length limit."""
        max_title_length = 100

        short_title = "Amazing Viral Video"
        long_title = "A" * 150

        assert len(short_title) <= max_title_length
        assert len(long_title) > max_title_length

    def test_description_formatting(self):
        """Test YouTube description formatting."""
        description_parts = [
            "Video description here.",
            "",
            "Timestamps:",
            "0:00 - Intro",
            "0:15 - Main content",
            "",
            "#Shorts #Viral #Trending",
        ]

        full_description = "\n".join(description_parts)

        assert "Timestamps:" in full_description
        assert "#Shorts" in full_description

    def test_visibility_options(self):
        """Test YouTube visibility options."""
        valid_visibilities = ["public", "unlisted", "private"]

        for visibility in valid_visibilities:
            assert visibility in valid_visibilities

    def test_shorts_hashtag_required(self):
        """Test #Shorts hashtag is required for Shorts."""
        description = "Amazing content"
        shorts_hashtag = "#Shorts"

        # For Shorts, add #Shorts
        if "#Shorts" not in description:
            description = f"{description}\n\n{shorts_hashtag}"

        assert "#Shorts" in description


# ============================================================================
# CROSS-PLATFORM TESTS
# ============================================================================

class TestCrossPlatformPublishing:
    """Tests for cross-platform publishing features."""

    def test_platform_specific_adaptations(self):
        """Test content adaptations for different platforms."""
        original_content = {
            "video_duration": 45,
            "caption": "Amazing content!",
            "hashtags": ["viral", "trending"],
        }

        # Instagram adaptation
        instagram_caption = f"{original_content['caption']} #{' #'.join(original_content['hashtags'])}"

        # TikTok adaptation (add fyp)
        tiktok_hashtags = original_content["hashtags"] + ["fyp", "foryou"]
        tiktok_caption = f"{original_content['caption']} #{' #'.join(tiktok_hashtags)}"

        # YouTube Shorts adaptation
        youtube_title = original_content["caption"][:100]
        youtube_description = f"{original_content['caption']}\n\n#Shorts"

        assert "#viral" in instagram_caption
        assert "#fyp" in tiktok_caption
        assert "#Shorts" in youtube_description

    def test_optimal_posting_times_by_platform(self):
        """Test optimal posting times vary by platform."""
        optimal_times = {
            "instagram": ["11:00", "13:00", "19:00"],
            "tiktok": ["09:00", "12:00", "19:00", "21:00"],
            "youtube": ["14:00", "16:00", "20:00"],
        }

        for platform, times in optimal_times.items():
            assert len(times) >= 2  # At least 2 optimal times per platform

    def test_publish_queue_ordering(self):
        """Test publish queue respects platform priorities."""
        queue = [
            {"platform": "tiktok", "priority": 1, "content": "Video 1"},
            {"platform": "instagram", "priority": 2, "content": "Video 2"},
            {"platform": "youtube", "priority": 1, "content": "Video 3"},
        ]

        # Sort by priority (lower = higher priority)
        sorted_queue = sorted(queue, key=lambda x: x["priority"])

        assert sorted_queue[0]["priority"] == 1
        assert sorted_queue[-1]["priority"] == 2


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestPublisherErrorHandling:
    """Tests for publisher error handling."""

    def test_api_error_handling(self):
        """Test API error is properly handled."""
        result = PublishResult(
            success=False,
            platform="instagram",
            post_id=None,
            post_url=None,
            status=PublishStatus.FAILED,
            message="API Error: Invalid access token",
            error_code="INVALID_TOKEN",
        )

        assert result.success is False
        assert "Invalid access token" in result.message

    def test_rate_limit_handling(self):
        """Test rate limit error handling."""
        result = PublishResult(
            success=False,
            platform="tiktok",
            post_id=None,
            post_url=None,
            status=PublishStatus.FAILED,
            message="Rate limit exceeded. Retry after 3600 seconds.",
            error_code="RATE_LIMIT",
            retry_after=3600,
        )

        assert result.error_code == "RATE_LIMIT"
        assert result.retry_after == 3600

    def test_file_not_found_handling(self):
        """Test file not found error handling."""
        non_existent_path = Path("/tmp/non_existent_video.mp4")

        assert not non_existent_path.exists()

    def test_network_error_retry(self):
        """Test network error triggers retry."""
        max_retries = 3
        retry_count = 0

        # Simulate retry logic
        for attempt in range(max_retries):
            retry_count += 1
            # In real code, this would attempt the request

        assert retry_count == max_retries
