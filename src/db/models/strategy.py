"""Model para estrategias de conteudo geradas."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.db.models.production import ProducedVideo
    from src.db.models.video import ViralVideo


class StrategyStatus(str, Enum):
    """Status possiveis de uma estrategia."""

    DRAFT = "draft"
    APPROVED = "approved"
    IN_PRODUCTION = "in_production"
    PRODUCED = "produced"
    PUBLISHED = "published"
    REJECTED = "rejected"


class GeneratedStrategy(Base):
    """Estrategia de conteudo gerada pelo GPT-4o."""

    __tablename__ = "generated_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_video_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("viral_videos.id", ondelete="SET NULL")
    )
    prompt_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("prompt_versions.id")
    )

    # Identificacao
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    concept: Mapped[Optional[str]] = mapped_column(Text)
    target_niche: Mapped[Optional[str]] = mapped_column(String(100))

    # Roteiro completo
    hook_script: Mapped[Optional[str]] = mapped_column(Text)
    hook_duration: Mapped[str] = mapped_column(String(10), default="0-3s")
    development_script: Mapped[Optional[str]] = mapped_column(Text)
    development_duration: Mapped[str] = mapped_column(String(10), default="3-25s")
    cta_script: Mapped[Optional[str]] = mapped_column(Text)
    cta_duration: Mapped[str] = mapped_column(String(10), default="25-30s")
    full_script: Mapped[Optional[str]] = mapped_column(Text)

    # Configuracao de TTS
    tts_config: Mapped[dict] = mapped_column(
        JSONB,
        default={
            "provider": "edge-tts",
            "voice": "pt-BR-FranciscaNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
        },
    )

    # Musica de fundo
    music_track: Mapped[Optional[str]] = mapped_column(String(100))
    music_volume: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.20"))

    # Prompts para Veo 3.1
    veo_prompts: Mapped[Optional[list]] = mapped_column(JSONB)

    # Metadados de publicacao
    suggested_hashtags: Mapped[Optional[list]] = mapped_column(JSONB)
    suggested_caption: Mapped[Optional[str]] = mapped_column(Text)
    best_posting_time: Mapped[Optional[str]] = mapped_column(String(50))
    suggested_music: Mapped[Optional[str]] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(20), default=StrategyStatus.DRAFT.value, index=True)

    # Custos
    estimated_production_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # Validacao
    is_valid_json: Mapped[bool] = mapped_column(default=True)
    validation_errors: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Metadados
    model_used: Mapped[str] = mapped_column(String(50), default="gpt-4o")
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    generation_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    source_video: Mapped[Optional["ViralVideo"]] = relationship(
        "ViralVideo", back_populates="strategies"
    )
    productions: Mapped[list["ProducedVideo"]] = relationship(
        "ProducedVideo", back_populates="strategy"
    )

    def __repr__(self) -> str:
        return f"<GeneratedStrategy(id={self.id}, title='{self.title[:30]}...', status='{self.status}')>"

    @property
    def is_ready_for_production(self) -> bool:
        """Verifica se a estrategia esta pronta para producao."""
        return (
            self.status == StrategyStatus.APPROVED.value
            and self.is_valid_json
            and self.veo_prompts is not None
            and len(self.veo_prompts) >= 3
        )

    @property
    def total_script_length(self) -> int:
        """Retorna o tamanho total do roteiro em caracteres."""
        scripts = [self.hook_script, self.development_script, self.cta_script]
        return sum(len(s) for s in scripts if s)

    @property
    def scene_count(self) -> int:
        """Retorna numero de cenas Veo."""
        return len(self.veo_prompts) if self.veo_prompts else 0
