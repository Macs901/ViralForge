"""Model para videos virais coletados."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.db.models.analysis import VideoAnalysis
    from src.db.models.profile import MonitoredProfile
    from src.db.models.strategy import GeneratedStrategy


class ViralVideo(Base):
    """Video viral coletado do Instagram."""

    __tablename__ = "viral_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitored_profiles.id", ondelete="SET NULL")
    )

    # Identificadores unicos
    platform_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    shortcode: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Metricas de engajamento
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)
    saves_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Viral Score Estatistico (pre-filtro)
    statistical_viral_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    recency_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    normalized_views: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    normalized_engagement: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    passes_prefilter: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Conteudo original
    caption: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    mentions: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    first_comment: Mapped[Optional[str]] = mapped_column(Text)

    # Metadados do video
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(10))

    # Arquivos locais (caminhos no MinIO)
    video_file_path: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text)
    audio_file_path: Mapped[Optional[str]] = mapped_column(Text)

    # Transcricao
    transcription: Mapped[Optional[str]] = mapped_column(Text)
    transcription_language: Mapped[Optional[str]] = mapped_column(String(10))
    transcription_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))

    # Timestamps
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Status de processamento
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_transcribed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processing_error: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    profile: Mapped[Optional["MonitoredProfile"]] = relationship(
        "MonitoredProfile", back_populates="videos"
    )
    analysis: Mapped[Optional["VideoAnalysis"]] = relationship(
        "VideoAnalysis", back_populates="video", uselist=False
    )
    strategies: Mapped[list["GeneratedStrategy"]] = relationship(
        "GeneratedStrategy", back_populates="source_video"
    )

    def __repr__(self) -> str:
        return f"<ViralVideo(id={self.id}, platform_id='{self.platform_id}', views={self.views_count})>"

    @property
    def is_ready_for_analysis(self) -> bool:
        """Verifica se o video esta pronto para analise."""
        return (
            self.passes_prefilter
            and self.is_downloaded
            and self.is_transcribed
            and not self.is_analyzed
        )

    @property
    def total_engagement(self) -> int:
        """Retorna total de engajamento."""
        return self.likes_count + self.comments_count + self.shares_count + self.saves_count
