"""Tests for database models."""

import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select

from src.db.models import (
    MonitoredProfile,
    ViralVideo,
    VideoAnalysis,
    GeneratedStrategy,
    ProducedVideo,
    Trend,
    ContentQueue,
    StyleProfile,
)


class TestMonitoredProfile:
    """Tests for MonitoredProfile model."""

    @pytest.mark.asyncio
    async def test_create_profile(self, db_session):
        """Test creating a monitored profile."""
        profile = MonitoredProfile(
            username="test_profile",
            platform="instagram",
            niche="humor",
            priority=3,
            is_active=True,
        )
        db_session.add(profile)
        await db_session.commit()

        result = await db_session.execute(
            select(MonitoredProfile).where(MonitoredProfile.username == "test_profile")
        )
        saved_profile = result.scalar_one()

        assert saved_profile.username == "test_profile"
        assert saved_profile.platform == "instagram"
        assert saved_profile.niche == "humor"
        assert saved_profile.priority == 3
        assert saved_profile.is_active is True

    @pytest.mark.asyncio
    async def test_profile_defaults(self, db_session):
        """Test default values for profile."""
        profile = MonitoredProfile(username="default_test")
        db_session.add(profile)
        await db_session.commit()

        result = await db_session.execute(
            select(MonitoredProfile).where(MonitoredProfile.username == "default_test")
        )
        saved_profile = result.scalar_one()

        assert saved_profile.is_active is True
        assert saved_profile.priority == 1
        assert saved_profile.platform == "instagram"
        assert saved_profile.total_videos_collected == 0

    @pytest.mark.asyncio
    async def test_priority_label(self, db_session):
        """Test priority label property."""
        profile = MonitoredProfile(username="priority_test", priority=5)
        db_session.add(profile)
        await db_session.commit()

        assert profile.priority_label == "critica"


class TestViralVideo:
    """Tests for ViralVideo model."""

    @pytest.mark.asyncio
    async def test_create_video(self, db_session):
        """Test creating a viral video."""
        video = ViralVideo(
            platform_id="ABC123XYZ",
            source_url="https://instagram.com/reel/ABC123XYZ",
            views_count=500000,
            likes_count=25000,
            comments_count=1500,
            caption="Test video caption #viral",
            duration_seconds=45,
        )
        db_session.add(video)
        await db_session.commit()

        result = await db_session.execute(
            select(ViralVideo).where(ViralVideo.platform_id == "ABC123XYZ")
        )
        saved_video = result.scalar_one()

        assert saved_video.platform_id == "ABC123XYZ"
        assert saved_video.views_count == 500000
        assert saved_video.likes_count == 25000

    @pytest.mark.asyncio
    async def test_video_with_profile(self, db_session):
        """Test video associated with a profile."""
        profile = MonitoredProfile(username="video_owner", niche="entertainment")
        db_session.add(profile)
        await db_session.flush()

        video = ViralVideo(
            platform_id="VIDEO123",
            source_url="https://instagram.com/reel/VIDEO123",
            profile_id=profile.id,
        )
        db_session.add(video)
        await db_session.commit()

        result = await db_session.execute(
            select(ViralVideo).where(ViralVideo.profile_id == profile.id)
        )
        saved_video = result.scalar_one()

        assert saved_video.profile_id == profile.id

    @pytest.mark.asyncio
    async def test_total_engagement_property(self, db_session):
        """Test total engagement calculation."""
        video = ViralVideo(
            platform_id="ENGAGE123",
            source_url="https://instagram.com/reel/ENGAGE123",
            likes_count=10000,
            comments_count=500,
            shares_count=200,
            saves_count=300,
        )
        db_session.add(video)
        await db_session.commit()

        assert video.total_engagement == 11000

    @pytest.mark.asyncio
    async def test_is_ready_for_analysis(self, db_session):
        """Test ready for analysis check."""
        video = ViralVideo(
            platform_id="READY123",
            source_url="https://instagram.com/reel/READY123",
            passes_prefilter=True,
            is_downloaded=True,
            is_transcribed=True,
            is_analyzed=False,
        )
        db_session.add(video)
        await db_session.commit()

        assert video.is_ready_for_analysis is True

        # Not ready if already analyzed
        video.is_analyzed = True
        assert video.is_ready_for_analysis is False


class TestVideoAnalysis:
    """Tests for VideoAnalysis model."""

    @pytest.mark.asyncio
    async def test_create_analysis(self, db_session):
        """Test creating a video analysis."""
        video = ViralVideo(
            platform_id="ANALYSIS123",
            source_url="https://instagram.com/reel/ANALYSIS123",
        )
        db_session.add(video)
        await db_session.flush()

        analysis = VideoAnalysis(
            video_id=video.id,
            hook_score=Decimal("8.5"),
            narrative_structure="hook-problem-solution",
            emotional_triggers=["curiosity", "surprise"],
            key_moments=[{"time": 0, "type": "hook"}],
        )
        db_session.add(analysis)
        await db_session.commit()

        result = await db_session.execute(
            select(VideoAnalysis).where(VideoAnalysis.video_id == video.id)
        )
        saved_analysis = result.scalar_one()

        assert saved_analysis.hook_score == Decimal("8.5")
        assert saved_analysis.narrative_structure == "hook-problem-solution"
        assert "curiosity" in saved_analysis.emotional_triggers


class TestGeneratedStrategy:
    """Tests for GeneratedStrategy model."""

    @pytest.mark.asyncio
    async def test_create_strategy(self, db_session):
        """Test creating a generated strategy."""
        video = ViralVideo(
            platform_id="STRAT123",
            source_url="https://instagram.com/reel/STRAT123",
        )
        db_session.add(video)
        await db_session.flush()

        strategy = GeneratedStrategy(
            source_video_id=video.id,
            title="Viral Hook Strategy",
            roteiro="Script content here",
            target_niche="humor",
        )
        db_session.add(strategy)
        await db_session.commit()

        result = await db_session.execute(
            select(GeneratedStrategy).where(GeneratedStrategy.source_video_id == video.id)
        )
        saved_strategy = result.scalar_one()

        assert saved_strategy.title == "Viral Hook Strategy"
        assert saved_strategy.target_niche == "humor"


class TestTrend:
    """Tests for Trend model."""

    @pytest.mark.asyncio
    async def test_create_trend(self, db_session):
        """Test creating a trend."""
        trend = Trend(
            name="Dance Challenge",
            platform="tiktok",
            trend_type="challenge",
            description="Viral dance trend",
            virality_score=Decimal("9.2"),
        )
        db_session.add(trend)
        await db_session.commit()

        result = await db_session.execute(
            select(Trend).where(Trend.name == "Dance Challenge")
        )
        saved_trend = result.scalar_one()

        assert saved_trend.platform == "tiktok"
        assert saved_trend.virality_score == Decimal("9.2")


class TestContentQueue:
    """Tests for ContentQueue model."""

    @pytest.mark.asyncio
    async def test_create_queue_item(self, db_session):
        """Test creating a queue item."""
        queue_item = ContentQueue(
            title="Scheduled Post",
            platform="instagram",
            scheduled_for=datetime(2025, 1, 15, 18, 0),
            status="pending",
        )
        db_session.add(queue_item)
        await db_session.commit()

        result = await db_session.execute(
            select(ContentQueue).where(ContentQueue.title == "Scheduled Post")
        )
        saved_item = result.scalar_one()

        assert saved_item.platform == "instagram"
        assert saved_item.status == "pending"


class TestStyleProfile:
    """Tests for StyleProfile model."""

    @pytest.mark.asyncio
    async def test_create_style_profile(self, db_session):
        """Test creating a style profile."""
        style = StyleProfile(
            name="Comedic Style",
            tone_type="humorous",
            emoji_density=Decimal("0.15"),
            avg_hashtags=5,
        )
        db_session.add(style)
        await db_session.commit()

        result = await db_session.execute(
            select(StyleProfile).where(StyleProfile.name == "Comedic Style")
        )
        saved_style = result.scalar_one()

        assert saved_style.tone_type == "humorous"
        assert saved_style.avg_hashtags == 5
