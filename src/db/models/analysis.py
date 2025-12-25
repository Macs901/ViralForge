"""Model para analises de video."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.db.models.video import ViralVideo


class PromptVersion(Base):
    """Versao de prompt para rastreabilidade."""

    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Performance tracking
    total_uses: Mapped[int] = mapped_column(Integer, default=0)
    avg_quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    analyses: Mapped[list["VideoAnalysis"]] = relationship(
        "VideoAnalysis", back_populates="prompt_version"
    )

    def __repr__(self) -> str:
        return f"<PromptVersion(type='{self.prompt_type}', version='{self.version}')>"


class VideoAnalysis(Base):
    """Analise de video feita pelo Gemini."""

    __tablename__ = "video_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("viral_videos.id", ondelete="CASCADE"), unique=True
    )
    prompt_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("prompt_versions.id")
    )

    # Analise do Hook (0-3 segundos)
    hook_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Analise do Desenvolvimento
    development: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Analise do CTA
    cta_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Fatores de Viralizacao
    viral_factors: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Elementos Visuais
    visual_elements: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Elementos de Audio
    audio_elements: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Elementos de Performance
    performance_elements: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Guia de Replicacao
    replication_guide: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Sugestao de Roteiro
    script_suggestion: Mapped[Optional[str]] = mapped_column(Text)

    # Scores calculados (0.00 a 1.00)
    virality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), index=True)
    replicability_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    production_quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))

    # Validacao do output
    is_valid_json: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_errors: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Resposta raw do Gemini (backup)
    raw_gemini_response: Mapped[Optional[str]] = mapped_column(Text)

    # Metadados
    model_used: Mapped[str] = mapped_column(String(50), default="gemini-1.5-pro")
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    analysis_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    video: Mapped["ViralVideo"] = relationship("ViralVideo", back_populates="analysis")
    prompt_version: Mapped[Optional["PromptVersion"]] = relationship(
        "PromptVersion", back_populates="analyses"
    )

    def __repr__(self) -> str:
        return f"<VideoAnalysis(id={self.id}, video_id={self.video_id}, virality={self.virality_score})>"

    @property
    def is_high_quality(self) -> bool:
        """Verifica se a analise indica um video de alta qualidade."""
        return (
            self.is_valid_json
            and self.virality_score is not None
            and float(self.virality_score) >= 0.7
            and self.replicability_score is not None
            and float(self.replicability_score) >= 0.6
        )
