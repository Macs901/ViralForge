"""Models para deteccao de tendencias e agendamento de conteudo."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class TrendType(str, Enum):
    """Tipos de tendencia."""
    AUDIO = "audio"
    FORMAT = "format"
    TOPIC = "topic"
    HASHTAG = "hashtag"
    CHALLENGE = "challenge"
    EFFECT = "effect"


class TrendStatus(str, Enum):
    """Status de tendencia."""
    EMERGING = "emerging"      # Comecando a crescer
    RISING = "rising"          # Crescendo rapido
    PEAK = "peak"              # No auge
    DECLINING = "declining"    # Caindo
    DEAD = "dead"              # Morta


class Platform(str, Enum):
    """Plataformas suportadas."""
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    ALL = "all"


class Trend(Base):
    """Tendencia detectada pelo sistema."""

    __tablename__ = "trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identificacao
    trend_type: Mapped[TrendType] = mapped_column(SQLEnum(TrendType), nullable=False, index=True)
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Identificadores externos
    external_id: Mapped[Optional[str]] = mapped_column(String(100))  # ID na plataforma
    external_url: Mapped[Optional[str]] = mapped_column(Text)

    # Metricas
    current_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, index=True)
    velocity: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)  # Velocidade de crescimento
    volume: Mapped[int] = mapped_column(Integer, default=0)  # Quantidade de posts
    engagement_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))

    # Status
    status: Mapped[TrendStatus] = mapped_column(SQLEnum(TrendStatus), default=TrendStatus.EMERGING)
    is_actionable: Mapped[bool] = mapped_column(Boolean, default=False)  # Pode ser replicado

    # Dados extras
    related_hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    related_audios: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    example_videos: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Historico de scores
    score_history: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # [{date, score, volume}, ...]

    # Timestamps
    first_detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    peak_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Trend(name='{self.name}', type={self.trend_type}, score={self.current_score})>"


class ContentStatus(str, Enum):
    """Status de conteudo na fila."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    READY = "ready"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentQueue(Base):
    """Fila de conteudo para publicacao."""

    __tablename__ = "content_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Referencias
    strategy_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("generated_strategies.id", ondelete="SET NULL")
    )
    production_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("produced_videos.id", ondelete="SET NULL")
    )
    trend_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("trends.id", ondelete="SET NULL")
    )

    # Conteudo
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(50), default="reel")  # reel, story, carousel, post

    # Plataformas alvo
    target_platforms: Mapped[list] = mapped_column(JSONB, default=list)  # ["instagram", "tiktok"]

    # Arquivos
    video_path: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text)
    caption: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # Agendamento
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    optimal_time_used: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    status: Mapped[ContentStatus] = mapped_column(SQLEnum(ContentStatus), default=ContentStatus.DRAFT, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1-5

    # Publicacao
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    published_urls: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"instagram": "url", "tiktok": "url"}

    # Metricas pos-publicacao
    post_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"views": 0, "likes": 0, "comments": 0, "shares": 0}

    # Erro
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ContentQueue(title='{self.title[:30]}...', status={self.status})>"


class PerformanceMetric(Base):
    """Metricas de performance de conteudo publicado."""

    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Referencias
    content_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("content_queue.id", ondelete="CASCADE")
    )
    production_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("produced_videos.id", ondelete="SET NULL")
    )

    # Identificacao
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False)
    post_id: Mapped[Optional[str]] = mapped_column(String(100))
    post_url: Mapped[Optional[str]] = mapped_column(Text)

    # Metricas de alcance
    views: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)

    # Metricas de engajamento
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)

    # Metricas calculadas
    engagement_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    viral_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))

    # Metricas de retencao (para videos)
    avg_watch_time: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # segundos
    watch_through_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))  # % que assistiu ate o fim

    # Metricas de conversao
    profile_visits: Mapped[int] = mapped_column(Integer, default=0)
    follows: Mapped[int] = mapped_column(Integer, default=0)
    link_clicks: Mapped[int] = mapped_column(Integer, default=0)

    # Dados demograficos
    audience_demographics: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"age": {"18-24": 30, ...}, "gender": {"M": 60, ...}, "location": {...}}

    # Historico (para tracking ao longo do tempo)
    metric_history: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # [{timestamp, views, likes, ...}, ...]

    # Timestamps
    measured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<PerformanceMetric(platform={self.platform}, views={self.views}, engagement={self.engagement_rate})>"

    @property
    def total_engagement(self) -> int:
        """Total de engajamento."""
        return self.likes + self.comments + self.shares + self.saves


class Competitor(Base):
    """Concorrente monitorado."""

    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identificacao
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(200))
    profile_url: Mapped[Optional[str]] = mapped_column(Text)

    # Classificacao
    niche: Mapped[Optional[str]] = mapped_column(String(100))
    tier: Mapped[str] = mapped_column(String(20), default="similar")  # bigger, similar, smaller
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Metricas do perfil
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metricas de performance
    avg_views: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    avg_likes: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    avg_comments: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    avg_engagement_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    posting_frequency: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # posts per day

    # Analise de conteudo
    top_content_types: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"reel": 60, "carousel": 30, "post": 10}
    top_hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    top_topics: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    best_posting_times: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    analyses: Mapped[list["CompetitorAnalysis"]] = relationship(
        "CompetitorAnalysis", back_populates="competitor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Competitor(username='{self.username}', platform={self.platform}, followers={self.follower_count})>"


class CompetitorAnalysis(Base):
    """Analise periodica de um concorrente."""

    __tablename__ = "competitor_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )

    # Periodo da analise
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Metricas do periodo
    posts_count: Mapped[int] = mapped_column(Integer, default=0)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_likes: Mapped[int] = mapped_column(Integer, default=0)
    total_comments: Mapped[int] = mapped_column(Integer, default=0)
    follower_change: Mapped[int] = mapped_column(Integer, default=0)

    # Metricas calculadas
    avg_engagement_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    growth_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))

    # Top posts do periodo
    top_posts: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # [{url, views, likes, caption}, ...]

    # Insights
    insights: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"trending_topics": [], "new_formats": [], "recommendations": []}

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationship
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<CompetitorAnalysis(competitor_id={self.competitor_id}, period={self.period_start.date()})>"
