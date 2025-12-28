"""Models para Style Cloning - Aprendizado de estilo unico."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ToneType(str, Enum):
    """Tipos de tom de voz."""
    FORMAL = "formal"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"
    PROVOCATIVE = "provocative"
    STORYTELLING = "storytelling"


class ContentRhythm(str, Enum):
    """Ritmo do conteudo."""
    FAST = "fast"           # Cortes rapidos, energia alta
    MEDIUM = "medium"       # Ritmo moderado
    SLOW = "slow"           # Calmo, contemplativo
    DYNAMIC = "dynamic"     # Varia ao longo do video


class StyleProfile(Base):
    """Perfil de estilo aprendido pelo sistema."""

    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identificacao
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # === TOM DE VOZ ===
    primary_tone: Mapped[ToneType] = mapped_column(
        String(50), default=ToneType.CASUAL.value
    )
    secondary_tones: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # ["humorous", "educational"]

    # Caracteristicas do texto
    vocabulary_level: Mapped[str] = mapped_column(String(20), default="medium")
    # simple, medium, advanced
    use_emoji: Mapped[bool] = mapped_column(Boolean, default=True)
    emoji_frequency: Mapped[str] = mapped_column(String(20), default="moderate")
    # none, sparse, moderate, heavy
    sentence_length: Mapped[str] = mapped_column(String(20), default="medium")
    # short, medium, long, mixed
    uses_slang: Mapped[bool] = mapped_column(Boolean, default=False)
    uses_questions: Mapped[bool] = mapped_column(Boolean, default=True)
    uses_cta: Mapped[bool] = mapped_column(Boolean, default=True)

    # === VISUAL ===
    color_palette: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # ["#FF5733", "#33FF57", "#3357FF"]
    dominant_colors: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    contrast_level: Mapped[str] = mapped_column(String(20), default="medium")
    # low, medium, high
    saturation_preference: Mapped[str] = mapped_column(String(20), default="medium")
    # desaturated, medium, vibrant
    filter_style: Mapped[Optional[str]] = mapped_column(String(50))
    # none, vintage, modern, cinematic

    # === ESTRUTURA DE VIDEO ===
    avg_duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    preferred_duration_range: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"min": 15, "max": 60}
    content_rhythm: Mapped[ContentRhythm] = mapped_column(
        String(20), default=ContentRhythm.MEDIUM.value
    )
    avg_cuts_per_minute: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    uses_transitions: Mapped[bool] = mapped_column(Boolean, default=True)
    transition_styles: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # ["fade", "cut", "zoom"]

    # Estrutura narrativa
    hook_style: Mapped[Optional[str]] = mapped_column(String(50))
    # question, statement, shock, visual
    middle_structure: Mapped[Optional[str]] = mapped_column(String(50))
    # educational, entertaining, demonstration
    ending_style: Mapped[Optional[str]] = mapped_column(String(50))
    # cta, punchline, cliffhanger, summary

    # === AUDIO ===
    uses_voiceover: Mapped[bool] = mapped_column(Boolean, default=True)
    uses_background_music: Mapped[bool] = mapped_column(Boolean, default=True)
    music_genres: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # ["pop", "electronic", "lo-fi"]
    music_energy: Mapped[str] = mapped_column(String(20), default="medium")
    # calm, medium, energetic
    voice_characteristics: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"speed": "fast", "pitch": "normal", "enthusiasm": "high"}

    # === CAPTIONS ===
    caption_length: Mapped[str] = mapped_column(String(20), default="medium")
    # short (<50 chars), medium (50-150), long (>150)
    caption_structure: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"hook_line": true, "body_paragraphs": 2, "cta_line": true}
    signature_phrases: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # ["Bora la!", "Se liga nessa dica"]
    hashtag_strategy: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"count": 10, "mix": {"branded": 2, "niche": 5, "viral": 3}}
    favorite_hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # === POSTING PATTERNS ===
    preferred_posting_times: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # [{"day": "monday", "times": ["09:00", "18:00"]}]
    posting_frequency: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"daily": 2, "weekly": 14}
    content_mix: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"reels": 70, "stories": 20, "posts": 10}

    # === ENGAGEMENT STYLE ===
    response_style: Mapped[Optional[str]] = mapped_column(String(50))
    # friendly, professional, playful
    engagement_techniques: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # ["ask_questions", "polls", "challenges"]

    # === ANALYTICS ===
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    # Quantos posts foram analisados
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    # 0.0 a 1.0 - confianca no perfil
    last_analysis_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Raw data for ML
    raw_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # Dados brutos da analise para uso em ML

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<StyleProfile(name='{self.name}', tone={self.primary_tone}, confidence={self.confidence_score})>"


class StyleAnalysis(Base):
    """Analise individual de um post/video para extração de estilo."""

    __tablename__ = "style_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Referencias
    profile_id: Mapped[Optional[int]] = mapped_column(Integer)  # StyleProfile
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_platform: Mapped[Optional[str]] = mapped_column(String(50))

    # Dados extraidos
    tone_detected: Mapped[Optional[str]] = mapped_column(String(50))
    vocabulary_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    emoji_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    sentence_count: Mapped[int] = mapped_column(Integer, default=0)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    cta_detected: Mapped[bool] = mapped_column(Boolean, default=False)

    # Visual
    colors_extracted: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    cuts_detected: Mapped[int] = mapped_column(Integer, default=0)

    # Raw data
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<StyleAnalysis(source={self.source_platform}, tone={self.tone_detected})>"
