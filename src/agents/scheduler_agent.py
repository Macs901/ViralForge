"""Content Scheduler Agent - Agenda e publica conteudo."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models.trends import ContentQueue, ContentStatus, Platform

settings = get_settings()


@dataclass
class ScheduleResult:
    """Resultado de agendamento."""
    content_id: int
    scheduled_at: datetime
    platforms: list[str]
    optimal_time_used: bool


@dataclass
class PublishResult:
    """Resultado de publicacao."""
    content_id: int
    success: bool
    published_urls: dict[str, str]
    error: Optional[str] = None


class ContentScheduler:
    """Agent que agenda e publica conteudo."""

    # Melhores horarios por plataforma (baseado em estudos gerais)
    OPTIMAL_TIMES = {
        Platform.INSTAGRAM: [
            {"day": 0, "hours": [11, 14, 19]},  # Segunda
            {"day": 1, "hours": [10, 14, 19]},  # Terca
            {"day": 2, "hours": [11, 13, 19]},  # Quarta
            {"day": 3, "hours": [10, 14, 20]},  # Quinta
            {"day": 4, "hours": [10, 13, 15]},  # Sexta
            {"day": 5, "hours": [10, 12, 14]},  # Sabado
            {"day": 6, "hours": [10, 12, 19]},  # Domingo
        ],
        Platform.TIKTOK: [
            {"day": 0, "hours": [12, 16, 21]},
            {"day": 1, "hours": [9, 15, 21]},
            {"day": 2, "hours": [12, 17, 21]},
            {"day": 3, "hours": [15, 18, 21]},
            {"day": 4, "hours": [11, 17, 21]},
            {"day": 5, "hours": [11, 19, 21]},
            {"day": 6, "hours": [9, 12, 19]},
        ],
        Platform.YOUTUBE: [
            {"day": 0, "hours": [14, 16, 21]},
            {"day": 1, "hours": [14, 16, 21]},
            {"day": 2, "hours": [14, 16, 21]},
            {"day": 3, "hours": [12, 15, 20]},
            {"day": 4, "hours": [12, 15, 17]},
            {"day": 5, "hours": [9, 11, 15]},
            {"day": 6, "hours": [9, 11, 15]},
        ],
    }

    def schedule_content(
        self,
        title: str,
        video_path: str,
        platforms: list[Platform],
        caption: Optional[str] = None,
        hashtags: Optional[list[str]] = None,
        scheduled_at: Optional[datetime] = None,
        use_optimal_time: bool = True,
        priority: int = 1,
        strategy_id: Optional[int] = None,
        production_id: Optional[int] = None,
        trend_id: Optional[int] = None,
    ) -> ScheduleResult:
        """Agenda conteudo para publicacao.

        Args:
            title: Titulo do conteudo
            video_path: Caminho do video
            platforms: Plataformas alvo
            caption: Legenda
            hashtags: Hashtags
            scheduled_at: Data/hora agendada (None = proximo horario otimo)
            use_optimal_time: Usar horario otimo se scheduled_at nao fornecido
            priority: Prioridade (1-5)
            strategy_id: ID da estrategia relacionada
            production_id: ID da producao relacionada
            trend_id: ID da tendencia relacionada

        Returns:
            ScheduleResult
        """
        db = get_sync_db()

        try:
            # Determina horario
            optimal_used = False
            if not scheduled_at:
                if use_optimal_time:
                    scheduled_at = self._get_next_optimal_time(platforms[0] if platforms else Platform.INSTAGRAM)
                    optimal_used = True
                else:
                    scheduled_at = datetime.now() + timedelta(hours=1)

            # Cria registro
            content = ContentQueue(
                title=title,
                video_path=video_path,
                caption=caption,
                hashtags=hashtags or [],
                target_platforms=[p.value for p in platforms],
                scheduled_at=scheduled_at,
                optimal_time_used=optimal_used,
                priority=priority,
                status=ContentStatus.SCHEDULED,
                strategy_id=strategy_id,
                production_id=production_id,
                trend_id=trend_id,
            )

            db.add(content)
            db.commit()
            db.refresh(content)

            return ScheduleResult(
                content_id=content.id,
                scheduled_at=scheduled_at,
                platforms=[p.value for p in platforms],
                optimal_time_used=optimal_used,
            )

        finally:
            db.close()

    def _get_next_optimal_time(self, platform: Platform) -> datetime:
        """Retorna proximo horario otimo para a plataforma."""
        now = datetime.now()
        times = self.OPTIMAL_TIMES.get(platform, self.OPTIMAL_TIMES[Platform.INSTAGRAM])

        # Procura proximo horario
        for days_ahead in range(7):
            check_date = now + timedelta(days=days_ahead)
            day_of_week = check_date.weekday()

            day_times = next((t for t in times if t["day"] == day_of_week), None)
            if not day_times:
                continue

            for hour in day_times["hours"]:
                scheduled = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                if scheduled > now + timedelta(minutes=30):  # Pelo menos 30min no futuro
                    return scheduled

        # Fallback: amanha ao meio-dia
        return (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

    def get_optimal_times(
        self,
        platform: Platform,
        days_ahead: int = 7,
    ) -> list[dict]:
        """Retorna melhores horarios para os proximos dias.

        Args:
            platform: Plataforma
            days_ahead: Quantos dias a frente

        Returns:
            Lista de {date, times}
        """
        now = datetime.now()
        times = self.OPTIMAL_TIMES.get(platform, self.OPTIMAL_TIMES[Platform.INSTAGRAM])
        result = []

        for days in range(days_ahead):
            check_date = now + timedelta(days=days)
            day_of_week = check_date.weekday()

            day_times = next((t for t in times if t["day"] == day_of_week), None)
            if day_times:
                result.append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "day_name": check_date.strftime("%A"),
                    "times": [f"{h:02d}:00" for h in day_times["hours"]],
                })

        return result

    def list_scheduled(
        self,
        status: Optional[ContentStatus] = None,
        platform: Optional[Platform] = None,
        limit: int = 20,
    ) -> list[ContentQueue]:
        """Lista conteudos agendados.

        Args:
            status: Filtrar por status
            platform: Filtrar por plataforma
            limit: Maximo de resultados

        Returns:
            Lista de ContentQueue
        """
        db = get_sync_db()
        try:
            query = select(ContentQueue)

            if status:
                query = query.where(ContentQueue.status == status)
            else:
                query = query.where(ContentQueue.status.in_([
                    ContentStatus.SCHEDULED,
                    ContentStatus.PROCESSING,
                    ContentStatus.READY,
                ]))

            if platform:
                # JSONB contains
                query = query.where(ContentQueue.target_platforms.contains([platform.value]))

            query = query.order_by(ContentQueue.scheduled_at).limit(limit)

            return list(db.execute(query).scalars().all())
        finally:
            db.close()

    def get_due_content(self) -> list[ContentQueue]:
        """Retorna conteudos prontos para publicar (horario passou).

        Returns:
            Lista de ContentQueue
        """
        db = get_sync_db()
        try:
            query = select(ContentQueue).where(
                ContentQueue.status == ContentStatus.SCHEDULED,
                ContentQueue.scheduled_at <= datetime.now(),
            ).order_by(ContentQueue.priority.desc(), ContentQueue.scheduled_at)

            return list(db.execute(query).scalars().all())
        finally:
            db.close()

    def publish_content(self, content_id: int) -> PublishResult:
        """Publica conteudo imediatamente.

        Args:
            content_id: ID do conteudo

        Returns:
            PublishResult
        """
        db = get_sync_db()
        try:
            content = db.get(ContentQueue, content_id)
            if not content:
                return PublishResult(
                    content_id=content_id,
                    success=False,
                    published_urls={},
                    error="Conteudo nao encontrado",
                )

            # Atualiza status
            content.status = ContentStatus.PROCESSING
            db.commit()

            published_urls = {}
            errors = []

            # Publica em cada plataforma
            for platform_str in content.target_platforms:
                try:
                    platform = Platform(platform_str)
                    url = self._publish_to_platform(content, platform)
                    if url:
                        published_urls[platform_str] = url
                except Exception as e:
                    errors.append(f"{platform_str}: {e}")

            # Atualiza registro
            if published_urls:
                content.status = ContentStatus.PUBLISHED
                content.published_at = datetime.now()
                content.published_urls = published_urls
            else:
                content.status = ContentStatus.FAILED
                content.error_message = "; ".join(errors)
                content.retry_count += 1

            db.commit()

            return PublishResult(
                content_id=content_id,
                success=bool(published_urls),
                published_urls=published_urls,
                error="; ".join(errors) if errors else None,
            )

        finally:
            db.close()

    def _publish_to_platform(self, content: ContentQueue, platform: Platform) -> Optional[str]:
        """Publica em uma plataforma especifica.

        NOTA: Implementacao real requer APIs de cada plataforma.
        Por enquanto, simula publicacao.
        """
        # TODO: Implementar integracao real com APIs
        # - Instagram: Meta Graph API (requer Business Account)
        # - TikTok: TikTok API for Business
        # - YouTube: YouTube Data API

        print(f"[Scheduler] Publicando em {platform.value}...")
        print(f"  - Video: {content.video_path}")
        print(f"  - Caption: {content.caption[:50] if content.caption else 'N/A'}...")

        # Simula URL publicada (em producao, seria a URL real do post)
        fake_id = uuid4().hex[:8]
        if platform == Platform.INSTAGRAM:
            return f"https://www.instagram.com/reel/{fake_id}/"
        elif platform == Platform.TIKTOK:
            return f"https://www.tiktok.com/@user/video/{fake_id}"
        elif platform == Platform.YOUTUBE:
            return f"https://youtube.com/shorts/{fake_id}"

        return None

    def cancel_scheduled(self, content_id: int) -> bool:
        """Cancela conteudo agendado.

        Args:
            content_id: ID do conteudo

        Returns:
            True se cancelado com sucesso
        """
        db = get_sync_db()
        try:
            content = db.get(ContentQueue, content_id)
            if content and content.status == ContentStatus.SCHEDULED:
                content.status = ContentStatus.CANCELLED
                db.commit()
                return True
            return False
        finally:
            db.close()

    def reschedule(self, content_id: int, new_time: datetime) -> bool:
        """Reagenda conteudo.

        Args:
            content_id: ID do conteudo
            new_time: Nova data/hora

        Returns:
            True se reagendado com sucesso
        """
        db = get_sync_db()
        try:
            content = db.get(ContentQueue, content_id)
            if content and content.status in [ContentStatus.SCHEDULED, ContentStatus.FAILED]:
                content.scheduled_at = new_time
                content.status = ContentStatus.SCHEDULED
                content.optimal_time_used = False
                db.commit()
                return True
            return False
        finally:
            db.close()


# Factory function
def get_scheduler() -> ContentScheduler:
    """Retorna instancia do ContentScheduler."""
    return ContentScheduler()
