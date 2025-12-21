"""Model para perfis monitorados no Instagram."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.db.models.video import ViralVideo


class MonitoredProfile(Base):
    """Perfil do Instagram sendo monitorado para coleta de videos virais."""

    __tablename__ = "monitored_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(20), default="instagram")
    niche: Mapped[Optional[str]] = mapped_column(String(100))
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Configuracoes de nicho para calculo do viral score
    niche_avg_views: Mapped[int] = mapped_column(Integer, default=50000)
    niche_avg_likes: Mapped[int] = mapped_column(Integer, default=5000)
    niche_avg_comments: Mapped[int] = mapped_column(Integer, default=500)

    # Estatisticas
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_videos_collected: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    videos: Mapped[list["ViralVideo"]] = relationship(
        "ViralVideo",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MonitoredProfile(id={self.id}, username='{self.username}', niche='{self.niche}')>"

    @property
    def priority_label(self) -> str:
        """Retorna label de prioridade."""
        labels = {1: "baixa", 2: "media", 3: "alta", 4: "urgente", 5: "critica"}
        return labels.get(self.priority, "desconhecida")
