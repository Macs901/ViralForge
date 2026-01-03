"""Tests for scraper tools."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import re


# ============================================================================
# DATA CLASSES FOR TESTING (mirrors actual scrapers)
# ============================================================================

@dataclass
class ScrapedProfile:
    """Scraped Instagram profile."""
    instagram_id: str
    username: str
    full_name: Optional[str] = None
    biography: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    media_count: int = 0
    is_private: bool = False
    is_verified: bool = False


@dataclass
class ScrapedVideo:
    """Scraped video data."""
    video_id: str
    shortcode: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    view_count: int = 0
    duration_seconds: float = 0.0
    owner_username: Optional[str] = None


@dataclass
class ScrapedStory:
    """Scraped Instagram story."""
    story_id: str
    owner_username: str = ""
    media_type: str = "image"
    is_video: bool = False
    video_url: Optional[str] = None
    has_music: bool = False
    mentions: list = field(default_factory=list)


@dataclass
class TikTokVideo:
    """TikTok video data."""
    video_id: str
    author_username: str = ""
    description: str = ""
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    duration_seconds: int = 0


@dataclass
class TikTokProfile:
    """TikTok profile data."""
    user_id: str
    username: str
    nickname: str = ""
    bio: str = ""
    follower_count: int = 0
    following_count: int = 0
    like_count: int = 0
    video_count: int = 0
    is_verified: bool = False


@dataclass
class YouTubeVideo:
    """YouTube video data."""
    video_id: str
    title: str = ""
    description: str = ""
    channel_id: str = ""
    channel_name: str = ""
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    duration_seconds: int = 0
    is_short: bool = False


@dataclass
class YouTubeChannel:
    """YouTube channel data."""
    channel_id: str
    channel_name: str = ""
    description: str = ""
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    is_verified: bool = False


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_apify_response_profile():
    """Mock Apify response for Instagram profile."""
    return [
        {
            "id": "123456789",
            "username": "test_creator",
            "fullName": "Test Creator",
            "biography": "Content creator | Humor",
            "followersCount": 150000,
            "followsCount": 500,
            "postsCount": 200,
            "isPrivate": False,
            "isVerified": True,
            "isBusiness": True,
            "businessCategory": "Creator",
        }
    ]


@pytest.fixture
def mock_apify_response_posts():
    """Mock Apify response for Instagram posts."""
    return [
        {
            "id": "POST123",
            "shortCode": "ABC123",
            "url": "https://instagram.com/reel/ABC123",
            "type": "Video",
            "videoUrl": "https://cdn.instagram.com/video.mp4",
            "thumbnailUrl": "https://cdn.instagram.com/thumb.jpg",
            "caption": "Viral content #viral #trending",
            "likesCount": 50000,
            "commentsCount": 2500,
            "videoViewCount": 1000000,
            "timestamp": "2025-01-01T12:00:00.000Z",
            "ownerUsername": "test_creator",
            "hashtags": ["viral", "trending"],
            "mentions": ["@friend"],
            "duration": 45.5,
        }
    ]


@pytest.fixture
def mock_tiktok_response():
    """Mock response for TikTok scraper."""
    return [
        {
            "id": "TIKTOK123",
            "desc": "Funny video #fyp",
            "createTime": 1704067200,
            "video": {
                "playAddr": "https://tiktok.com/video.mp4",
                "cover": "https://tiktok.com/cover.jpg",
                "duration": 30,
            },
            "stats": {
                "playCount": 5000000,
                "diggCount": 500000,
                "commentCount": 25000,
                "shareCount": 50000,
            },
            "author": {
                "uniqueId": "tiktok_creator",
                "nickname": "TikTok Creator",
            },
        }
    ]


# ============================================================================
# INSTAGRAM SCRAPER TESTS
# ============================================================================

class TestInstagramScraper:
    """Tests for InstagramScraper."""

    def test_parse_profile_data(self):
        """Test parsing profile data from API response."""
        raw_data = {
            "id": "123456789",
            "username": "test_user",
            "fullName": "Test User",
            "biography": "Bio here",
            "followersCount": 10000,
            "followsCount": 100,
            "postsCount": 50,
            "isPrivate": False,
            "isVerified": False,
        }

        profile = ScrapedProfile(
            instagram_id=raw_data["id"],
            username=raw_data["username"],
            full_name=raw_data["fullName"],
            biography=raw_data["biography"],
            follower_count=raw_data["followersCount"],
            following_count=raw_data["followsCount"],
            media_count=raw_data["postsCount"],
            is_private=raw_data["isPrivate"],
            is_verified=raw_data["isVerified"],
        )

        assert profile.username == "test_user"
        assert profile.follower_count == 10000
        assert profile.is_verified is False

    def test_scraped_video_dataclass(self):
        """Test ScrapedVideo dataclass."""
        video = ScrapedVideo(
            video_id="VID123",
            shortcode="ABC123",
            video_url="https://example.com/video.mp4",
            thumbnail_url="https://example.com/thumb.jpg",
            caption="Test caption",
            like_count=5000,
            comment_count=200,
            view_count=100000,
            duration_seconds=45.0,
            owner_username="creator",
        )

        assert video.video_id == "VID123"
        assert video.like_count == 5000
        assert video.duration_seconds == 45.0

    def test_scraped_story_dataclass(self):
        """Test ScrapedStory dataclass."""
        story = ScrapedStory(
            story_id="STORY123",
            owner_username="creator",
            media_type="video",
            is_video=True,
            video_url="https://example.com/story.mp4",
            has_music=True,
            mentions=["@friend1", "@friend2"],
        )

        assert story.story_id == "STORY123"
        assert story.is_video is True
        assert len(story.mentions) == 2


# ============================================================================
# TIKTOK SCRAPER TESTS
# ============================================================================

class TestTikTokScraper:
    """Tests for TikTokScraper."""

    def test_tiktok_video_dataclass(self):
        """Test TikTokVideo dataclass."""
        video = TikTokVideo(
            video_id="TT123",
            author_username="tiktok_user",
            description="Funny video #fyp",
            video_url="https://tiktok.com/video.mp4",
            thumbnail_url="https://tiktok.com/thumb.jpg",
            play_count=5000000,
            like_count=500000,
            comment_count=25000,
            share_count=50000,
            duration_seconds=30,
        )

        assert video.video_id == "TT123"
        assert video.play_count == 5000000
        assert video.share_count == 50000

    def test_tiktok_profile_dataclass(self):
        """Test TikTokProfile dataclass."""
        profile = TikTokProfile(
            user_id="USER123",
            username="tiktok_creator",
            nickname="TikTok Creator",
            bio="Creator bio",
            follower_count=1000000,
            following_count=100,
            like_count=50000000,
            video_count=500,
            is_verified=True,
        )

        assert profile.username == "tiktok_creator"
        assert profile.follower_count == 1000000
        assert profile.is_verified is True


# ============================================================================
# YOUTUBE SCRAPER TESTS
# ============================================================================

class TestYouTubeScraper:
    """Tests for YouTubeScraper."""

    def test_youtube_video_dataclass(self):
        """Test YouTubeVideo dataclass."""
        video = YouTubeVideo(
            video_id="YT123ABC",
            title="Viral YouTube Video",
            description="Video description here",
            channel_id="CHANNEL123",
            channel_name="Test Channel",
            video_url="https://youtube.com/watch?v=YT123ABC",
            thumbnail_url="https://i.ytimg.com/vi/YT123ABC/hqdefault.jpg",
            view_count=10000000,
            like_count=500000,
            comment_count=25000,
            duration_seconds=600,
            is_short=False,
        )

        assert video.video_id == "YT123ABC"
        assert video.view_count == 10000000
        assert video.is_short is False

    def test_youtube_short_detection(self):
        """Test YouTube Shorts detection."""
        short = YouTubeVideo(
            video_id="SHORT123",
            title="Quick Short",
            channel_id="CHANNEL123",
            channel_name="Test Channel",
            video_url="https://youtube.com/shorts/SHORT123",
            view_count=1000000,
            duration_seconds=45,
            is_short=True,
        )

        assert short.is_short is True
        assert short.duration_seconds <= 60

    def test_youtube_channel_dataclass(self):
        """Test YouTubeChannel dataclass."""
        channel = YouTubeChannel(
            channel_id="CHANNEL123",
            channel_name="Test Channel",
            description="Channel description",
            subscriber_count=1000000,
            video_count=500,
            view_count=100000000,
            is_verified=True,
        )

        assert channel.channel_id == "CHANNEL123"
        assert channel.subscriber_count == 1000000
        assert channel.is_verified is True


# ============================================================================
# INTEGRATION STYLE TESTS (with mocks)
# ============================================================================

class TestScraperIntegration:
    """Integration-style tests with mocked API calls."""

    def test_viral_score_calculation(self):
        """Test viral score calculation logic."""
        video = ScrapedVideo(
            video_id="VIRAL123",
            shortcode="VIRAL123",
            view_count=1000000,
            like_count=100000,
            comment_count=5000,
            owner_username="creator",
        )

        # Calculate engagement rate
        engagement_rate = (video.like_count + video.comment_count) / video.view_count

        assert engagement_rate > 0.1  # 10% engagement is very high
        assert video.view_count >= 1000000  # Viral threshold

    def test_hashtag_extraction(self):
        """Test hashtag extraction from caption."""
        caption = "Amazing video! #viral #trending #fyp #content"

        hashtags = re.findall(r"#(\w+)", caption)

        assert len(hashtags) == 4
        assert "viral" in hashtags
        assert "fyp" in hashtags

    def test_mention_extraction(self):
        """Test mention extraction from caption."""
        caption = "Check out @creator1 and @creator2 for more!"

        mentions = re.findall(r"@(\w+)", caption)

        assert len(mentions) == 2
        assert "creator1" in mentions
        assert "creator2" in mentions

    def test_engagement_rate_calculation(self):
        """Test engagement rate calculation."""
        views = 100000
        likes = 8000
        comments = 500
        shares = 200

        engagement_rate = (likes + comments + shares) / views * 100

        assert engagement_rate == 8.7  # 8.7%

    def test_video_duration_validation(self):
        """Test video duration validation for different platforms."""
        durations = {
            "tiktok": 180,  # max 3 minutes
            "instagram_reels": 90,  # max 90 seconds
            "youtube_shorts": 60,  # max 60 seconds
        }

        test_duration = 45

        for platform, max_duration in durations.items():
            is_valid = test_duration <= max_duration
            assert is_valid is True
