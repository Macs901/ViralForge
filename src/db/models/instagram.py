"""Models completos para dados do Instagram."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.db.models.profile import MonitoredProfile
    from src.db.models.video import ViralVideo


class ContentType(str, Enum):
    """Tipos de conteudo do Instagram."""
    REEL = "reel"
    POST = "post"
    STORY = "story"
    CAROUSEL = "carousel"
    IGTV = "igtv"
    LIVE = "live"


class InstagramProfile(Base):
    """Dados completos de um perfil do Instagram."""

    __tablename__ = "instagram_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitored_profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitored_profiles.id", ondelete="SET NULL")
    )

    # Identificadores
    instagram_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Info do perfil
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    biography: Mapped[Optional[str]] = mapped_column(Text)
    external_url: Mapped[Optional[str]] = mapped_column(Text)
    profile_pic_url: Mapped[Optional[str]] = mapped_column(Text)
    profile_pic_url_hd: Mapped[Optional[str]] = mapped_column(Text)

    # Contadores
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    media_count: Mapped[int] = mapped_column(Integer, default=0)
    igtv_count: Mapped[int] = mapped_column(Integer, default=0)
    reels_count: Mapped[int] = mapped_column(Integer, default=0)

    # Status da conta
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_business: Mapped[bool] = mapped_column(Boolean, default=False)
    business_category: Mapped[Optional[str]] = mapped_column(String(100))
    business_email: Mapped[Optional[str]] = mapped_column(String(200))
    business_phone: Mapped[Optional[str]] = mapped_column(String(50))

    # Metricas calculadas
    avg_likes_per_post: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    avg_comments_per_post: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    avg_views_per_reel: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    engagement_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    posting_frequency: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # posts per day

    # Analise de conteudo
    top_hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    content_types_distribution: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    best_posting_times: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # Timestamps
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    stories: Mapped[list["InstagramStory"]] = relationship("InstagramStory", back_populates="profile")
    carousels: Mapped[list["InstagramCarousel"]] = relationship("InstagramCarousel", back_populates="profile")

    def __repr__(self) -> str:
        return f"<InstagramProfile(username='{self.username}', followers={self.follower_count})>"


class InstagramStory(Base):
    """Story do Instagram (conteudo efemero 24h)."""

    __tablename__ = "instagram_stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("instagram_profiles.id", ondelete="CASCADE")
    )

    # Identificadores
    story_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    story_pk: Mapped[Optional[str]] = mapped_column(String(50))

    # Tipo de media
    media_type: Mapped[str] = mapped_column(String(20))  # image, video
    is_video: Mapped[bool] = mapped_column(Boolean, default=False)

    # URLs
    media_url: Mapped[Optional[str]] = mapped_column(Text)
    video_url: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)

    # Dimensoes
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))

    # Interacoes
    has_audio: Mapped[bool] = mapped_column(Boolean, default=False)
    has_music: Mapped[bool] = mapped_column(Boolean, default=False)
    music_info: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Stickers e elementos interativos
    has_poll: Mapped[bool] = mapped_column(Boolean, default=False)
    has_question: Mapped[bool] = mapped_column(Boolean, default=False)
    has_quiz: Mapped[bool] = mapped_column(Boolean, default=False)
    has_countdown: Mapped[bool] = mapped_column(Boolean, default=False)
    has_link: Mapped[bool] = mapped_column(Boolean, default=False)
    link_url: Mapped[Optional[str]] = mapped_column(Text)
    stickers: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    mentions: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # Arquivos locais
    local_file_path: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expiring_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationship
    profile: Mapped[Optional["InstagramProfile"]] = relationship("InstagramProfile", back_populates="stories")

    def __repr__(self) -> str:
        return f"<InstagramStory(id={self.id}, story_id='{self.story_id}')>"


class InstagramCarousel(Base):
    """Carrossel do Instagram (post com multiplas midias)."""

    __tablename__ = "instagram_carousels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("instagram_profiles.id", ondelete="CASCADE")
    )
    viral_video_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("viral_videos.id", ondelete="SET NULL")
    )

    # Identificadores
    carousel_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    shortcode: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Metricas
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    saves_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)

    # Conteudo
    caption: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    mentions: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # Slides
    slide_count: Mapped[int] = mapped_column(Integer, default=0)
    slides: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    # Cada slide: {index, type, url, thumbnail_url, is_video, duration, width, height}

    # Arquivos locais
    local_folder_path: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    profile: Mapped[Optional["InstagramProfile"]] = relationship("InstagramProfile", back_populates="carousels")

    def __repr__(self) -> str:
        return f"<InstagramCarousel(shortcode='{self.shortcode}', slides={self.slide_count})>"


class InstagramComment(Base):
    """Comentario em post/reel do Instagram."""

    __tablename__ = "instagram_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    viral_video_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("viral_videos.id", ondelete="CASCADE")
    )
    carousel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("instagram_carousels.id", ondelete="CASCADE")
    )
    parent_comment_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("instagram_comments.id", ondelete="CASCADE")
    )

    # Identificadores
    comment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    comment_pk: Mapped[Optional[str]] = mapped_column(String(50))

    # Autor
    author_id: Mapped[Optional[str]] = mapped_column(String(50))
    author_username: Mapped[str] = mapped_column(String(100), nullable=False)
    author_full_name: Mapped[Optional[str]] = mapped_column(String(200))
    author_profile_pic: Mapped[Optional[str]] = mapped_column(Text)
    is_author_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Conteudo
    text: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    hashtags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # Metricas
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    replies_count: Mapped[int] = mapped_column(Integer, default=0)

    # Analise de sentimento (preenchido depois)
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))  # -1 a 1
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20))  # positive, negative, neutral

    # Flags
    is_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_from_creator: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at_ig: Mapped[Optional[datetime]] = mapped_column(DateTime)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Self-referential relationship for replies
    replies: Mapped[list["InstagramComment"]] = relationship(
        "InstagramComment",
        backref="parent_comment",
        remote_side=[id],
        cascade="all, delete-orphan",
        single_parent=True
    )

    def __repr__(self) -> str:
        return f"<InstagramComment(author='{self.author_username}', likes={self.likes_count})>"


class InstagramHashtag(Base):
    """Hashtag monitorada do Instagram."""

    __tablename__ = "instagram_hashtags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identificadores
    hashtag_id: Mapped[Optional[str]] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Metricas
    media_count: Mapped[int] = mapped_column(Integer, default=0)
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False)

    # Configuracao de monitoramento
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False)
    scrape_frequency_hours: Mapped[int] = mapped_column(Integer, default=24)

    # Timestamps
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<InstagramHashtag(name='#{self.name}', posts={self.media_count})>"


class InstagramAudio(Base):
    """Audio/musica usada em Reels."""

    __tablename__ = "instagram_audios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identificadores
    audio_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    audio_cluster_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Info do audio
    title: Mapped[Optional[str]] = mapped_column(String(300))
    artist_name: Mapped[Optional[str]] = mapped_column(String(200))
    artist_username: Mapped[Optional[str]] = mapped_column(String(100))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    cover_art_url: Mapped[Optional[str]] = mapped_column(Text)

    # Metricas
    reels_count: Mapped[int] = mapped_column(Integer, default=0)  # quantos reels usam
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_original: Mapped[bool] = mapped_column(Boolean, default=False)  # audio original vs musica
    is_explicit: Mapped[bool] = mapped_column(Boolean, default=False)

    # Arquivo local
    local_file_path: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<InstagramAudio(title='{self.title}', reels={self.reels_count})>"
