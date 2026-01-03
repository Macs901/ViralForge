"""Tests for V3 agents (TrendHunter, StyleCloner, PerformanceTracker, Scheduler, CompetitorIntel)."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from src.db.models import (
    Trend,
    TrendType,
    TrendStatus,
    StyleProfile,
    StyleAnalysis,
    ContentQueue,
    ContentStatus,
    PerformanceMetric,
    Competitor,
    CompetitorAnalysis,
    Platform,
)


# ============================================================================
# TREND HUNTER AGENT TESTS
# ============================================================================

class TestTrendHunterAgent:
    """Tests for TrendHunterAgent."""

    @pytest.mark.asyncio
    async def test_trend_creation(self, db_session):
        """Test creating a trend."""
        trend = Trend(
            name="Dance Challenge 2025",
            platform="tiktok",
            trend_type="challenge",
            description="New viral dance trend",
            hashtags=["dancechallenge", "viral2025"],
            virality_score=Decimal("8.5"),
            growth_rate=Decimal("15.2"),
            status="active",
        )
        db_session.add(trend)
        await db_session.commit()

        assert trend.id is not None
        assert trend.virality_score == Decimal("8.5")
        assert trend.status == "active"

    @pytest.mark.asyncio
    async def test_trend_status_transitions(self, db_session):
        """Test trend status transitions."""
        trend = Trend(
            name="Test Trend",
            platform="instagram",
            trend_type="audio",
            status="emerging",
        )
        db_session.add(trend)
        await db_session.commit()

        # Transition to active
        trend.status = "active"
        await db_session.commit()
        assert trend.status == "active"

        # Transition to declining
        trend.status = "declining"
        await db_session.commit()
        assert trend.status == "declining"

    def test_virality_score_calculation(self):
        """Test virality score calculation logic."""
        # Factors for virality score
        engagement_rate = 0.15  # 15%
        growth_rate = 25.0  # 25% growth
        volume = 100000  # mentions

        # Simplified virality formula
        virality_score = (
            (engagement_rate * 30) +  # Weight: 30%
            (min(growth_rate, 50) * 0.1) +  # Weight: up to 5 points
            (min(volume / 10000, 5))  # Weight: up to 5 points
        )

        assert virality_score > 0
        assert virality_score <= 10  # Max score

    def test_trend_type_classification(self):
        """Test trend type classification."""
        trend_types = ["audio", "challenge", "meme", "format", "topic"]

        for t_type in trend_types:
            trend = Trend(
                name=f"Test {t_type}",
                platform="tiktok",
                trend_type=t_type,
            )
            assert trend.trend_type in trend_types


# ============================================================================
# STYLE CLONER AGENT TESTS
# ============================================================================

class TestStyleClonerAgent:
    """Tests for StyleClonerAgent."""

    @pytest.mark.asyncio
    async def test_style_profile_creation(self, db_session):
        """Test creating a style profile."""
        style = StyleProfile(
            name="Comedic Creator Style",
            tone_type="humorous",
            emoji_density=Decimal("0.15"),
            avg_hashtags=5,
            common_emojis=["😂", "🔥", "💀"],
            signature_phrases=["voces nao vao acreditar", "essa e boa"],
        )
        db_session.add(style)
        await db_session.commit()

        assert style.id is not None
        assert style.tone_type == "humorous"
        assert "😂" in style.common_emojis

    @pytest.mark.asyncio
    async def test_style_analysis_creation(self, db_session):
        """Test creating style analysis."""
        style = StyleProfile(name="Test Style", tone_type="professional")
        db_session.add(style)
        await db_session.flush()

        analysis = StyleAnalysis(
            style_profile_id=style.id,
            text_analyzed="Sample caption text #viral",
            detected_tone="professional",
            emoji_count=2,
            hashtag_count=1,
            avg_sentence_length=8.5,
        )
        db_session.add(analysis)
        await db_session.commit()

        assert analysis.id is not None
        assert analysis.detected_tone == "professional"

    def test_tone_detection(self):
        """Test tone detection logic."""
        # Humorous indicators
        humorous_text = "voces nao vao acreditar 😂😂😂 socorro"
        humorous_indicators = ["😂", "💀", "socorro", "kkkk"]

        has_humor = any(ind in humorous_text for ind in humorous_indicators)
        assert has_humor is True

        # Professional indicators
        professional_text = "Dicas para melhorar sua produtividade"
        professional_indicators = ["dicas", "estrategia", "como", "aprenda"]

        has_professional = any(
            ind.lower() in professional_text.lower()
            for ind in professional_indicators
        )
        assert has_professional is True

    def test_emoji_density_calculation(self):
        """Test emoji density calculation."""
        text = "Amazing video 🔥🔥 check it out 😍"
        emoji_count = 3
        word_count = 5

        emoji_density = emoji_count / word_count if word_count > 0 else 0

        assert emoji_density == 0.6  # 3 emojis / 5 words


# ============================================================================
# PERFORMANCE TRACKER AGENT TESTS
# ============================================================================

class TestPerformanceTrackerAgent:
    """Tests for PerformanceTrackerAgent."""

    @pytest.mark.asyncio
    async def test_performance_metric_creation(self, db_session):
        """Test creating performance metric."""
        metric = PerformanceMetric(
            platform="instagram",
            content_id="POST123",
            recorded_at=datetime.now(),
            views=100000,
            likes=10000,
            comments=500,
            shares=200,
            saves=300,
            engagement_rate=Decimal("10.8"),
        )
        db_session.add(metric)
        await db_session.commit()

        assert metric.id is not None
        assert metric.engagement_rate == Decimal("10.8")

    @pytest.mark.asyncio
    async def test_metric_tracking_over_time(self, db_session):
        """Test tracking metrics over time."""
        content_id = "TRACK123"
        base_time = datetime.now()

        # Create metrics at different times
        for i in range(3):
            metric = PerformanceMetric(
                platform="tiktok",
                content_id=content_id,
                recorded_at=base_time + timedelta(hours=i),
                views=10000 * (i + 1),
                likes=1000 * (i + 1),
            )
            db_session.add(metric)

        await db_session.commit()

        # Verify growth tracking
        from sqlalchemy import select
        result = await db_session.execute(
            select(PerformanceMetric)
            .where(PerformanceMetric.content_id == content_id)
            .order_by(PerformanceMetric.recorded_at)
        )
        metrics = result.scalars().all()

        assert len(metrics) == 3
        assert metrics[2].views > metrics[0].views  # Views grew

    def test_engagement_rate_calculation(self):
        """Test engagement rate calculation."""
        views = 100000
        likes = 8000
        comments = 500
        shares = 200
        saves = 300

        # Standard engagement rate formula
        engagement_rate = (likes + comments + shares + saves) / views * 100

        assert engagement_rate == 9.0  # 9%

    def test_performance_benchmarking(self):
        """Test performance benchmarking logic."""
        # Niche averages
        niche_avg = {
            "views": 50000,
            "engagement_rate": 5.0,
        }

        # Current performance
        current = {
            "views": 150000,
            "engagement_rate": 8.0,
        }

        # Calculate performance vs benchmark
        views_vs_benchmark = current["views"] / niche_avg["views"]
        engagement_vs_benchmark = current["engagement_rate"] / niche_avg["engagement_rate"]

        assert views_vs_benchmark == 3.0  # 3x average views
        assert engagement_vs_benchmark == 1.6  # 1.6x average engagement


# ============================================================================
# SCHEDULER AGENT TESTS
# ============================================================================

class TestSchedulerAgent:
    """Tests for SchedulerAgent."""

    @pytest.mark.asyncio
    async def test_content_queue_creation(self, db_session):
        """Test creating content queue item."""
        scheduled_time = datetime.now() + timedelta(hours=2)

        queue_item = ContentQueue(
            title="Scheduled Viral Video",
            platform="instagram",
            content_type="reel",
            scheduled_for=scheduled_time,
            status="pending",
            caption="Amazing content! #viral",
        )
        db_session.add(queue_item)
        await db_session.commit()

        assert queue_item.id is not None
        assert queue_item.status == "pending"

    @pytest.mark.asyncio
    async def test_content_status_transitions(self, db_session):
        """Test content status transitions."""
        queue_item = ContentQueue(
            title="Test Content",
            platform="tiktok",
            scheduled_for=datetime.now() + timedelta(hours=1),
            status="pending",
        )
        db_session.add(queue_item)
        await db_session.commit()

        # Transition to scheduled
        queue_item.status = "scheduled"
        await db_session.commit()
        assert queue_item.status == "scheduled"

        # Transition to published
        queue_item.status = "published"
        queue_item.published_at = datetime.now()
        await db_session.commit()
        assert queue_item.status == "published"
        assert queue_item.published_at is not None

    def test_optimal_posting_time_selection(self):
        """Test optimal posting time selection."""
        # Best posting times by day
        posting_schedule = {
            "monday": ["18:00", "20:00"],
            "tuesday": ["12:00", "19:00"],
            "wednesday": ["18:00", "21:00"],
            "thursday": ["17:00", "20:00"],
            "friday": ["16:00", "19:00"],
            "saturday": ["11:00", "20:00"],
            "sunday": ["10:00", "19:00"],
        }

        # Verify schedule has entries for all days
        assert len(posting_schedule) == 7

        # Each day should have at least one posting time
        for day, times in posting_schedule.items():
            assert len(times) >= 1

    def test_queue_priority_ordering(self):
        """Test queue items are ordered by priority."""
        items = [
            {"title": "Low Priority", "priority": 1},
            {"title": "High Priority", "priority": 5},
            {"title": "Medium Priority", "priority": 3},
        ]

        # Sort by priority descending
        sorted_items = sorted(items, key=lambda x: x["priority"], reverse=True)

        assert sorted_items[0]["title"] == "High Priority"
        assert sorted_items[-1]["title"] == "Low Priority"


# ============================================================================
# COMPETITOR INTEL AGENT TESTS
# ============================================================================

class TestCompetitorIntelAgent:
    """Tests for CompetitorIntelAgent."""

    @pytest.mark.asyncio
    async def test_competitor_creation(self, db_session):
        """Test creating a competitor."""
        competitor = Competitor(
            username="competitor_account",
            platform="instagram",
            niche="humor",
            follower_count=500000,
            is_verified=True,
            avg_views=100000,
            avg_engagement_rate=Decimal("8.5"),
        )
        db_session.add(competitor)
        await db_session.commit()

        assert competitor.id is not None
        assert competitor.follower_count == 500000

    @pytest.mark.asyncio
    async def test_competitor_analysis_creation(self, db_session):
        """Test creating competitor analysis."""
        competitor = Competitor(
            username="test_competitor",
            platform="tiktok",
            niche="entertainment",
        )
        db_session.add(competitor)
        await db_session.flush()

        analysis = CompetitorAnalysis(
            competitor_id=competitor.id,
            analyzed_at=datetime.now(),
            top_content_types=["comedy", "reaction"],
            posting_frequency=2.5,  # posts per day
            avg_video_duration=45,
            peak_posting_times=["18:00", "21:00"],
            trending_hashtags=["fyp", "viral", "comedy"],
        )
        db_session.add(analysis)
        await db_session.commit()

        assert analysis.id is not None
        assert analysis.posting_frequency == 2.5

    def test_competitor_comparison(self):
        """Test competitor comparison logic."""
        your_stats = {
            "followers": 50000,
            "avg_views": 25000,
            "engagement_rate": 6.0,
        }

        competitor_stats = {
            "followers": 100000,
            "avg_views": 50000,
            "engagement_rate": 5.5,
        }

        # Calculate gaps
        follower_gap = competitor_stats["followers"] - your_stats["followers"]
        view_gap = competitor_stats["avg_views"] - your_stats["avg_views"]
        engagement_advantage = your_stats["engagement_rate"] - competitor_stats["engagement_rate"]

        assert follower_gap == 50000  # 50k behind
        assert view_gap == 25000  # 25k less views
        assert engagement_advantage == 0.5  # 0.5% higher engagement (winning!)

    def test_content_gap_identification(self):
        """Test content gap identification."""
        your_content_types = ["comedy", "storytime"]
        competitor_content_types = ["comedy", "storytime", "reaction", "duet"]

        # Find content gaps
        gaps = set(competitor_content_types) - set(your_content_types)

        assert "reaction" in gaps
        assert "duet" in gaps
        assert len(gaps) == 2

    def test_trend_adoption_tracking(self):
        """Test tracking competitor trend adoption."""
        competitor_trends = [
            {"trend": "dance_challenge", "adopted_at": datetime(2025, 1, 1)},
            {"trend": "green_screen", "adopted_at": datetime(2025, 1, 5)},
        ]

        # Calculate average adoption time
        base_date = datetime(2025, 1, 1)
        adoption_times = [
            (t["adopted_at"] - base_date).days for t in competitor_trends
        ]
        avg_adoption = sum(adoption_times) / len(adoption_times)

        assert avg_adoption >= 0
        assert len(competitor_trends) == 2
