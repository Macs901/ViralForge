"""Add Style Cloning tables.

Revision ID: 20251228_002
Revises: 20251228_001
Create Date: 2025-12-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251228_002"
down_revision: Union[str, None] = "20251228_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create style tables."""

    # ===================
    # STYLE PROFILES TABLE
    # ===================
    op.create_table(
        "style_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_default", sa.Boolean(), default=False),

        # Tom de voz
        sa.Column("primary_tone", sa.String(50), default="casual"),
        sa.Column("secondary_tones", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("vocabulary_level", sa.String(20), default="medium"),
        sa.Column("use_emoji", sa.Boolean(), default=True),
        sa.Column("emoji_frequency", sa.String(20), default="moderate"),
        sa.Column("sentence_length", sa.String(20), default="medium"),
        sa.Column("uses_slang", sa.Boolean(), default=False),
        sa.Column("uses_questions", sa.Boolean(), default=True),
        sa.Column("uses_cta", sa.Boolean(), default=True),

        # Visual
        sa.Column("color_palette", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("dominant_colors", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("contrast_level", sa.String(20), default="medium"),
        sa.Column("saturation_preference", sa.String(20), default="medium"),
        sa.Column("filter_style", sa.String(50)),

        # Video structure
        sa.Column("avg_duration_seconds", sa.Numeric(10, 2)),
        sa.Column("preferred_duration_range", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("content_rhythm", sa.String(20), default="medium"),
        sa.Column("avg_cuts_per_minute", sa.Numeric(5, 2)),
        sa.Column("uses_transitions", sa.Boolean(), default=True),
        sa.Column("transition_styles", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("hook_style", sa.String(50)),
        sa.Column("middle_structure", sa.String(50)),
        sa.Column("ending_style", sa.String(50)),

        # Audio
        sa.Column("uses_voiceover", sa.Boolean(), default=True),
        sa.Column("uses_background_music", sa.Boolean(), default=True),
        sa.Column("music_genres", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("music_energy", sa.String(20), default="medium"),
        sa.Column("voice_characteristics", postgresql.JSONB(astext_type=sa.Text()), default=dict),

        # Captions
        sa.Column("caption_length", sa.String(20), default="medium"),
        sa.Column("caption_structure", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("signature_phrases", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("hashtag_strategy", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("favorite_hashtags", postgresql.JSONB(astext_type=sa.Text()), default=list),

        # Posting patterns
        sa.Column("preferred_posting_times", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("posting_frequency", postgresql.JSONB(astext_type=sa.Text()), default=dict),
        sa.Column("content_mix", postgresql.JSONB(astext_type=sa.Text()), default=dict),

        # Engagement
        sa.Column("response_style", sa.String(50)),
        sa.Column("engagement_techniques", postgresql.JSONB(astext_type=sa.Text()), default=list),

        # Analytics
        sa.Column("sample_count", sa.Integer(), default=0),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column("last_analysis_at", sa.DateTime()),
        sa.Column("raw_analysis", postgresql.JSONB(astext_type=sa.Text()), default=dict),

        # Timestamps
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ===================
    # STYLE ANALYSES TABLE
    # ===================
    op.create_table(
        "style_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer()),
        sa.Column("source_url", sa.Text()),
        sa.Column("source_platform", sa.String(50)),

        # Extracted data
        sa.Column("tone_detected", sa.String(50)),
        sa.Column("vocabulary_score", sa.Numeric(5, 4)),
        sa.Column("emoji_count", sa.Integer(), default=0),
        sa.Column("word_count", sa.Integer(), default=0),
        sa.Column("sentence_count", sa.Integer(), default=0),
        sa.Column("question_count", sa.Integer(), default=0),
        sa.Column("cta_detected", sa.Boolean(), default=False),

        # Visual
        sa.Column("colors_extracted", postgresql.JSONB(astext_type=sa.Text()), default=list),
        sa.Column("duration_seconds", sa.Numeric(10, 2)),
        sa.Column("cuts_detected", sa.Integer(), default=0),

        # Raw
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), default=dict),

        # Timestamps
        sa.Column("analyzed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Indexes
    op.create_index("ix_style_profiles_name", "style_profiles", ["name"])
    op.create_index("ix_style_profiles_active", "style_profiles", ["is_active"])


def downgrade() -> None:
    """Drop style tables."""
    op.drop_index("ix_style_profiles_active", table_name="style_profiles")
    op.drop_index("ix_style_profiles_name", table_name="style_profiles")
    op.drop_table("style_analyses")
    op.drop_table("style_profiles")
