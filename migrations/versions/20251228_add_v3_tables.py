"""Add ViralForge v3 tables - Trends, Content Queue, Performance, Competitors, Instagram.

Revision ID: 20251228_001
Revises: 20251225_001
Create Date: 2025-12-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251228_001"
down_revision: Union[str, None] = "20251225_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all v3 tables."""

    # ===================
    # TRENDS TABLE
    # ===================
    op.create_table(
        "trends",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trend_type", sa.Enum("audio", "format", "topic", "hashtag", "challenge", "effect", name="trendtype"), nullable=False, index=True),
        sa.Column("platform", sa.Enum("instagram", "tiktok", "youtube", "all", name="platform"), nullable=False, index=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("external_id", sa.String(100)),
        sa.Column("external_url", sa.Text()),
        sa.Column("current_score", sa.Numeric(10, 4), default=0, index=True),
        sa.Column("velocity", sa.Numeric(10, 4), default=0),
        sa.Column("volume", sa.Integer(), default=0),
        sa.Column("engagement_avg", sa.Numeric(12, 2)),
        sa.Column("status", sa.Enum("emerging", "rising", "peak", "declining", "dead", name="trendstatus"), default="emerging"),
        sa.Column("is_actionable", sa.Boolean(), default=False),
        sa.Column("related_hashtags", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("related_audios", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("example_videos", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("score_history", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("first_detected_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("peak_at", sa.DateTime()),
        sa.Column("last_updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ===================
    # CONTENT QUEUE TABLE
    # ===================
    op.create_table(
        "content_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("generated_strategies.id", ondelete="SET NULL")),
        sa.Column("production_id", sa.Integer(), sa.ForeignKey("produced_videos.id", ondelete="SET NULL")),
        sa.Column("trend_id", sa.Integer(), sa.ForeignKey("trends.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("content_type", sa.String(50), default="reel"),
        sa.Column("target_platforms", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("video_path", sa.Text()),
        sa.Column("thumbnail_path", sa.Text()),
        sa.Column("caption", sa.Text()),
        sa.Column("hashtags", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("scheduled_at", sa.DateTime(), index=True),
        sa.Column("optimal_time_used", sa.Boolean(), default=False),
        sa.Column("status", sa.Enum("draft", "scheduled", "processing", "ready", "published", "failed", "cancelled", name="contentstatus"), default="draft", index=True),
        sa.Column("priority", sa.Integer(), default=1),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("published_urls", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("post_metrics", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("error_message", sa.Text()),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ===================
    # PERFORMANCE METRICS TABLE
    # ===================
    op.create_table(
        "performance_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_queue.id", ondelete="CASCADE")),
        sa.Column("production_id", sa.Integer(), sa.ForeignKey("produced_videos.id", ondelete="SET NULL")),
        sa.Column("platform", sa.Enum("instagram", "tiktok", "youtube", "all", name="platform"), nullable=False),
        sa.Column("post_id", sa.String(100)),
        sa.Column("post_url", sa.Text()),
        sa.Column("views", sa.Integer(), default=0),
        sa.Column("impressions", sa.Integer(), default=0),
        sa.Column("reach", sa.Integer(), default=0),
        sa.Column("likes", sa.Integer(), default=0),
        sa.Column("comments", sa.Integer(), default=0),
        sa.Column("shares", sa.Integer(), default=0),
        sa.Column("saves", sa.Integer(), default=0),
        sa.Column("engagement_rate", sa.Numeric(5, 4)),
        sa.Column("viral_score", sa.Numeric(5, 4)),
        sa.Column("avg_watch_time", sa.Numeric(10, 2)),
        sa.Column("watch_through_rate", sa.Numeric(5, 4)),
        sa.Column("profile_visits", sa.Integer(), default=0),
        sa.Column("follows", sa.Integer(), default=0),
        sa.Column("link_clicks", sa.Integer(), default=0),
        sa.Column("audience_demographics", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("metric_history", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("measured_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ===================
    # COMPETITORS TABLE
    # ===================
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.Enum("instagram", "tiktok", "youtube", "all", name="platform"), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200)),
        sa.Column("profile_url", sa.Text()),
        sa.Column("niche", sa.String(100)),
        sa.Column("tier", sa.String(20), default="similar"),
        sa.Column("priority", sa.Integer(), default=1),
        sa.Column("notes", sa.Text()),
        sa.Column("follower_count", sa.Integer(), default=0),
        sa.Column("following_count", sa.Integer(), default=0),
        sa.Column("post_count", sa.Integer(), default=0),
        sa.Column("avg_views", sa.Numeric(12, 2)),
        sa.Column("avg_likes", sa.Numeric(12, 2)),
        sa.Column("avg_comments", sa.Numeric(12, 2)),
        sa.Column("avg_engagement_rate", sa.Numeric(5, 4)),
        sa.Column("posting_frequency", sa.Numeric(5, 2)),
        sa.Column("top_content_types", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("top_hashtags", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("top_topics", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("best_posting_times", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_scraped_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ===================
    # COMPETITOR ANALYSES TABLE
    # ===================
    op.create_table(
        "competitor_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("posts_count", sa.Integer(), default=0),
        sa.Column("total_views", sa.Integer(), default=0),
        sa.Column("total_likes", sa.Integer(), default=0),
        sa.Column("total_comments", sa.Integer(), default=0),
        sa.Column("follower_change", sa.Integer(), default=0),
        sa.Column("avg_engagement_rate", sa.Numeric(5, 4)),
        sa.Column("growth_rate", sa.Numeric(5, 4)),
        sa.Column("top_posts", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("insights", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("analyzed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ===================
    # INSTAGRAM PROFILES TABLE
    # ===================
    op.create_table(
        "instagram_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(200)),
        sa.Column("biography", sa.Text()),
        sa.Column("profile_pic_url", sa.Text()),
        sa.Column("external_url", sa.Text()),
        sa.Column("is_business", sa.Boolean(), default=False),
        sa.Column("is_verified", sa.Boolean(), default=False),
        sa.Column("follower_count", sa.Integer(), default=0),
        sa.Column("following_count", sa.Integer(), default=0),
        sa.Column("media_count", sa.Integer(), default=0),
        sa.Column("is_monitored", sa.Boolean(), default=False),
        sa.Column("last_scraped_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ===================
    # INSTAGRAM STORIES TABLE
    # ===================
    op.create_table(
        "instagram_stories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("instagram_profiles.id", ondelete="CASCADE")),
        sa.Column("story_pk", sa.String(100), unique=True, index=True),
        sa.Column("media_type", sa.Integer()),
        sa.Column("video_url", sa.Text()),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("duration", sa.Numeric(10, 2)),
        sa.Column("mentions", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("hashtags", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("stickers", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("taken_at", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("is_analyzed", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ===================
    # INSTAGRAM CAROUSELS TABLE
    # ===================
    op.create_table(
        "instagram_carousels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("instagram_profiles.id", ondelete="CASCADE")),
        sa.Column("post_pk", sa.String(100), unique=True, index=True),
        sa.Column("caption", sa.Text()),
        sa.Column("media_count", sa.Integer(), default=0),
        sa.Column("media_items", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("likes_count", sa.Integer(), default=0),
        sa.Column("comments_count", sa.Integer(), default=0),
        sa.Column("views_count", sa.Integer(), default=0),
        sa.Column("hashtags", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("mentions", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("taken_at", sa.DateTime()),
        sa.Column("is_analyzed", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ===================
    # INSTAGRAM COMMENTS TABLE
    # ===================
    op.create_table(
        "instagram_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_pk", sa.String(100), index=True),
        sa.Column("comment_pk", sa.String(100), unique=True),
        sa.Column("username", sa.String(100)),
        sa.Column("text", sa.Text()),
        sa.Column("likes_count", sa.Integer(), default=0),
        sa.Column("is_reply", sa.Boolean(), default=False),
        sa.Column("parent_pk", sa.String(100)),
        sa.Column("sentiment", sa.String(20)),
        sa.Column("created_at_platform", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ===================
    # INSTAGRAM HASHTAGS TABLE
    # ===================
    op.create_table(
        "instagram_hashtags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("media_count", sa.Integer(), default=0),
        sa.Column("category", sa.String(100)),
        sa.Column("related_hashtags", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("usage_trend", sa.String(20)),
        sa.Column("last_scraped_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ===================
    # INSTAGRAM AUDIOS TABLE
    # ===================
    op.create_table(
        "instagram_audios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audio_pk", sa.String(100), unique=True, index=True),
        sa.Column("title", sa.String(300)),
        sa.Column("artist", sa.String(200)),
        sa.Column("duration", sa.Numeric(10, 2)),
        sa.Column("is_original", sa.Boolean(), default=False),
        sa.Column("usage_count", sa.Integer(), default=0),
        sa.Column("is_trending", sa.Boolean(), default=False),
        sa.Column("trend_score", sa.Numeric(10, 4)),
        sa.Column("preview_url", sa.Text()),
        sa.Column("last_scraped_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index("ix_trends_name", "trends", ["name"])
    op.create_index("ix_trends_status", "trends", ["status"])
    op.create_index("ix_content_queue_scheduled", "content_queue", ["scheduled_at", "status"])
    op.create_index("ix_competitors_platform_username", "competitors", ["platform", "username"])


def downgrade() -> None:
    """Drop all v3 tables."""
    # Drop indexes
    op.drop_index("ix_competitors_platform_username", table_name="competitors")
    op.drop_index("ix_content_queue_scheduled", table_name="content_queue")
    op.drop_index("ix_trends_status", table_name="trends")
    op.drop_index("ix_trends_name", table_name="trends")

    # Drop tables in reverse order
    op.drop_table("instagram_audios")
    op.drop_table("instagram_hashtags")
    op.drop_table("instagram_comments")
    op.drop_table("instagram_carousels")
    op.drop_table("instagram_stories")
    op.drop_table("instagram_profiles")
    op.drop_table("competitor_analyses")
    op.drop_table("competitors")
    op.drop_table("performance_metrics")
    op.drop_table("content_queue")
    op.drop_table("trends")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS contentstatus")
    op.execute("DROP TYPE IF EXISTS trendstatus")
    op.execute("DROP TYPE IF EXISTS trendtype")
    op.execute("DROP TYPE IF EXISTS platform")
