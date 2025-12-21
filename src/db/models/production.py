"""Model para videos produzidos."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.db.models.strategy import GeneratedStrategy


class ProductionStatus(str, Enum):
    """Status possiveis de uma producao."""

    PENDING = "pending"
    GENERATING_TTS = "generating_tts"
    GENERATING_VIDEO = "generating_video"
    MIXING = "mixing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProducedVideo(Base):
    """Video produzido a partir de uma estrategia."""

    __tablename__ = "produced_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("generated_strategies.id", ondelete="SET NULL")
    )
    production_batch_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), default=lambda: str(uuid4())
    )

    # Arquivos de audio
    tts_file_path: Mapped[Optional[str]] = mapped_column(Text)
    tts_provider: Mapped[Optional[str]] = mapped_column(String(20))
    narration_duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))

    # Jobs do Fal.ai (Veo)
    veo_jobs: Mapped[Optional[list]] = mapped_column(JSONB)

    # Arquivos finais (MinIO)
    clips_paths: Mapped[Optional[list]] = mapped_column(JSONB)
    concatenated_video_path: Mapped[Optional[str]] = mapped_column(Text)
    final_video_path: Mapped[Optional[str]] = mapped_column(Text)

    # Metadados de mixagem
    music_track_used: Mapped[Optional[str]] = mapped_column(String(100))
    music_volume_used: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))

    # Metadados do video final
    final_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    final_resolution: Mapped[Optional[str]] = mapped_column(String(20))
    final_file_size_mb: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    # Custos detalhados
    tts_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    veo_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    total_production_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # Publicacao
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_platform: Mapped[Optional[str]] = mapped_column(String(20))
    published_url: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Metricas pos-publicacao
    post_views: Mapped[int] = mapped_column(Integer, default=0)
    post_likes: Mapped[int] = mapped_column(Integer, default=0)
    post_comments: Mapped[int] = mapped_column(Integer, default=0)
    post_shares: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default=ProductionStatus.PENDING.value, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    strategy: Mapped[Optional["GeneratedStrategy"]] = relationship(
        "GeneratedStrategy", back_populates="productions"
    )

    def __repr__(self) -> str:
        return f"<ProducedVideo(id={self.id}, status='{self.status}', cost=${self.total_production_cost_usd})>"

    @property
    def is_complete(self) -> bool:
        """Verifica se a producao foi concluida com sucesso."""
        return self.status == ProductionStatus.COMPLETED.value and self.final_video_path is not None

    @property
    def post_engagement(self) -> int:
        """Retorna total de engajamento pos-publicacao."""
        return self.post_likes + self.post_comments + self.post_shares

    def calculate_total_cost(self) -> Decimal:
        """Calcula e atualiza o custo total de producao."""
        tts = self.tts_cost_usd or Decimal("0")
        veo = self.veo_cost_usd or Decimal("0")
        self.total_production_cost_usd = tts + veo
        return self.total_production_cost_usd
