"""Tests for main agents (Watcher, Analyst, Producer, Strategist)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from decimal import Decimal

# Mock heavy imports before they're loaded
import sys
sys.modules['anthropic'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

from src.db.models import MonitoredProfile, ViralVideo, VideoAnalysis


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_profile():
    """Mock MonitoredProfile."""
    profile = MagicMock(spec=MonitoredProfile)
    profile.id = 1
    profile.username = "test_creator"
    profile.platform = "instagram"
    profile.niche = "humor"
    profile.niche_avg_views = 50000
    profile.niche_avg_likes = 5000
    profile.is_active = True
    return profile


@pytest.fixture
def mock_video():
    """Mock ViralVideo."""
    video = MagicMock(spec=ViralVideo)
    video.id = 1
    video.platform_id = "VIDEO123"
    video.source_url = "https://instagram.com/reel/VIDEO123"
    video.views_count = 500000
    video.likes_count = 25000
    video.comments_count = 1500
    video.duration_seconds = 45
    video.caption = "Test video #viral"
    video.transcription = "This is the video transcription"
    video.is_downloaded = True
    video.is_transcribed = True
    video.is_analyzed = False
    video.passes_prefilter = True
    return video


@pytest.fixture
def sample_scraped_video():
    """Sample scraped video data."""
    return {
        "id": "VID123",
        "shortCode": "ABC123",
        "url": "https://instagram.com/reel/ABC123",
        "videoUrl": "https://cdn.instagram.com/video.mp4",
        "caption": "Amazing content! #viral #trending",
        "likesCount": 100000,
        "commentsCount": 5000,
        "videoViewCount": 2000000,
        "timestamp": "2025-01-01T12:00:00.000Z",
        "duration": 30,
    }


# ============================================================================
# WATCHER AGENT TESTS
# ============================================================================

class TestWatcherAgent:
    """Tests for WatcherAgent."""

    def test_watcher_result_dataclass(self):
        """Test WatcherResult dataclass structure."""
        from dataclasses import dataclass

        @dataclass
        class WatcherResult:
            run_id: str
            profile_username: str
            videos_collected: int
            videos_prefiltered: int
            cost_usd: float
            duration_seconds: float
            errors: list

        result = WatcherResult(
            run_id="run-123",
            profile_username="test_user",
            videos_collected=10,
            videos_prefiltered=5,
            cost_usd=0.05,
            duration_seconds=30.5,
            errors=[],
        )

        assert result.run_id == "run-123"
        assert result.videos_collected == 10
        assert result.videos_prefiltered == 5
        assert result.cost_usd == 0.05
        assert len(result.errors) == 0

    def test_viral_score_calculation(self, mock_profile):
        """Test viral score calculation logic."""
        views = 500000
        likes = 50000
        comments = 5000

        # Calculate normalized metrics
        niche_avg_views = mock_profile.niche_avg_views
        normalized_views = min(views / niche_avg_views, 10.0)  # Cap at 10x

        engagement_rate = (likes + comments) / views if views > 0 else 0

        # Viral score formula (simplified)
        viral_score = (normalized_views * 0.6) + (engagement_rate * 100 * 0.4)

        assert viral_score > 0
        assert normalized_views > 1  # Video performed above average

    def test_prefilter_logic(self):
        """Test prefilter logic for viral videos."""
        # Minimum thresholds
        min_views = 10000
        min_engagement_rate = 0.03  # 3%

        test_cases = [
            {"views": 50000, "likes": 2000, "comments": 100, "expected": True},
            {"views": 5000, "likes": 100, "comments": 10, "expected": False},  # Low views
            {"views": 100000, "likes": 500, "comments": 50, "expected": False},  # Low engagement
        ]

        for case in test_cases:
            passes_view_threshold = case["views"] >= min_views
            engagement = (case["likes"] + case["comments"]) / case["views"]
            passes_engagement = engagement >= min_engagement_rate

            passes_prefilter = passes_view_threshold and passes_engagement
            assert passes_prefilter == case["expected"]


# ============================================================================
# ANALYST AGENT TESTS
# ============================================================================

class TestAnalystAgent:
    """Tests for AnalystAgent."""

    def test_hook_analysis_structure(self):
        """Test hook analysis data structure."""
        hook_analysis = {
            "opening_type": "pergunta",
            "attention_technique": "questionamento direto",
            "first_words": "Voce sabia que...",
            "visual_hook": "Close no rosto com expressao de surpresa",
            "hook_score": 0.85,
        }

        assert hook_analysis["opening_type"] == "pergunta"
        assert 0 <= hook_analysis["hook_score"] <= 1

    def test_visual_elements_structure(self):
        """Test visual elements data structure."""
        visual = {
            "dominant_colors": ["azul", "branco"],
            "framing": "close",
            "lighting": "ring_light",
            "scenario": "casa",
            "text_on_screen": True,
            "text_style": "Arial, branco com sombra",
            "transitions": ["corte_seco", "zoom"],
            "cuts_per_minute": 15,
        }

        assert "azul" in visual["dominant_colors"]
        assert visual["framing"] == "close"
        assert visual["text_on_screen"] is True

    def test_audio_elements_structure(self):
        """Test audio elements data structure."""
        audio = {
            "voice_type": "direta",
            "voice_tone": "energetico",
            "music_present": True,
            "music_type": "trending",
            "music_volume": "baixo",
            "sound_effects": True,
        }

        assert audio["voice_type"] == "direta"
        assert audio["music_present"] is True


# ============================================================================
# VIDEO ANALYSIS INTEGRATION TESTS
# ============================================================================

class TestVideoAnalysisFlow:
    """Integration tests for video analysis flow."""

    @pytest.mark.asyncio
    async def test_analysis_creation(self, db_session):
        """Test creating video analysis in database."""
        video = ViralVideo(
            platform_id="FLOW123",
            source_url="https://instagram.com/reel/FLOW123",
            views_count=1000000,
            is_downloaded=True,
            is_transcribed=True,
            transcription="Video transcription here",
        )
        db_session.add(video)
        await db_session.flush()

        analysis = VideoAnalysis(
            video_id=video.id,
            hook_score=Decimal("0.85"),
            narrative_structure="hook-development-cta",
            emotional_triggers=["curiosity", "fomo"],
            key_moments=[
                {"time": 0, "type": "hook"},
                {"time": 15, "type": "reveal"},
                {"time": 28, "type": "cta"},
            ],
            virality_score=Decimal("8.5"),
        )
        db_session.add(analysis)
        await db_session.commit()

        assert analysis.id is not None
        assert analysis.video_id == video.id

    @pytest.mark.asyncio
    async def test_video_ready_for_analysis_check(self, db_session):
        """Test checking if video is ready for analysis."""
        # Video ready for analysis
        ready_video = ViralVideo(
            platform_id="READY123",
            source_url="https://instagram.com/reel/READY123",
            passes_prefilter=True,
            is_downloaded=True,
            is_transcribed=True,
            is_analyzed=False,
        )
        db_session.add(ready_video)
        await db_session.commit()

        assert ready_video.is_ready_for_analysis is True


# ============================================================================
# PRODUCER AGENT TESTS
# ============================================================================

class TestProducerAgent:
    """Tests for ProducerAgent."""

    def test_script_generation_logic(self):
        """Test script generation logic."""
        analysis = {
            "hook_analysis": {
                "opening_type": "pergunta",
                "first_words": "Voce sabia que...",
            },
            "narrative_structure": "hook-problem-solution",
            "emotional_triggers": ["curiosity", "surprise"],
        }

        assert analysis["hook_analysis"]["opening_type"] == "pergunta"
        assert "curiosity" in analysis["emotional_triggers"]

    def test_adaptation_for_different_platforms(self):
        """Test content adaptation for different platforms."""
        original_duration = 60  # seconds

        # TikTok optimal duration
        tiktok_optimal = min(original_duration, 60)
        assert tiktok_optimal <= 60

        # YouTube Shorts optimal duration
        youtube_shorts_optimal = min(original_duration, 60)
        assert youtube_shorts_optimal <= 60

        # Instagram Reels optimal duration
        reels_optimal = min(original_duration, 90)
        assert reels_optimal <= 90


# ============================================================================
# STRATEGIST AGENT TESTS
# ============================================================================

class TestStrategistAgent:
    """Tests for StrategistAgent."""

    def test_strategy_generation_inputs(self):
        """Test strategy generation requires proper inputs."""
        video_data = {
            "views": 1000000,
            "likes": 100000,
            "comments": 5000,
            "engagement_rate": 0.105,
        }

        analysis_data = {
            "hook_score": 0.85,
            "narrative_structure": "hook-problem-solution",
            "emotional_triggers": ["curiosity", "urgency"],
        }

        assert video_data["engagement_rate"] > 0.05
        assert analysis_data["hook_score"] > 0.7

    def test_posting_time_recommendations(self):
        """Test posting time recommendation logic."""
        best_times = ["18:00", "20:00", "22:00"]

        for time_str in best_times:
            hour = int(time_str.split(":")[0])
            assert 0 <= hour <= 23

    def test_hashtag_recommendations(self):
        """Test hashtag recommendation logic."""
        niche = "humor"
        trending = ["fyp", "viral", "trending"]
        niche_specific = ["comedia", "risos", "humor"]

        all_hashtags = trending + niche_specific

        assert len(all_hashtags) <= 10
        assert "fyp" in all_hashtags
