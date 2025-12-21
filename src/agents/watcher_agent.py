"""Watcher Agent - Responsavel por scraping e pre-filtro de videos virais."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models import MonitoredProfile, RunMetrics, RunStatus, ViralVideo
from src.tools import budget_tools, scraping_tools

settings = get_settings()


@dataclass
class WatcherResult:
    """Resultado de uma execucao do Watcher."""

    run_id: str
    profile_username: str
    videos_collected: int
    videos_prefiltered: int
    cost_usd: float
    duration_seconds: float
    errors: list[str]


class WatcherAgent:
    """Agent responsavel por monitorar perfis e coletar videos virais.

    Pipeline:
    1. Scraping de videos via Apify
    2. Pre-filtro estatistico (Viral Score)
    3. Armazenamento no banco
    """

    def __init__(self):
        """Inicializa Watcher Agent."""
        self.scraping = scraping_tools
        self.budget = budget_tools

    def run(
        self,
        profile_id: Optional[int] = None,
        username: Optional[str] = None,
        max_videos: int = 50,
    ) -> WatcherResult:
        """Executa scraping e pre-filtro para um perfil.

        Args:
            profile_id: ID do perfil no banco (opcional)
            username: Username do perfil (se profile_id nao informado)
            max_videos: Maximo de videos a coletar

        Returns:
            WatcherResult com estatisticas da execucao
        """
        run_id = str(uuid4())
        errors = []
        start_time = datetime.now()

        db = get_sync_db()
        try:
            # Obtem perfil
            profile = self._get_profile(db, profile_id, username)
            if not profile:
                raise ValueError("Perfil nao encontrado")

            # Cria metrica de run
            run_metric = RunMetrics(
                run_id=run_id,
                task_name="watcher_scraping",
                agent_name="watcher",
            )
            db.add(run_metric)
            db.commit()

            # Verifica budget
            can_run, cost, msg = self.budget.check_budget("apify", max_videos)
            if not can_run:
                raise RuntimeError(f"Budget insuficiente: {msg}")

            # Executa scraping
            print(f"[Watcher] Iniciando scraping de @{profile.username}...")
            result = self.scraping.scrape_profile_videos(
                username=profile.username,
                max_videos=max_videos,
                min_views=settings.min_views_threshold,
                min_likes=settings.min_likes_threshold,
            )

            # Processa videos coletados
            videos_saved = 0
            videos_prefiltered = 0

            for scraped_video in result.videos:
                try:
                    # Verifica se video ja existe
                    existing = db.execute(
                        select(ViralVideo).where(
                            ViralVideo.platform_id == scraped_video.platform_id
                        )
                    ).scalar_one_or_none()

                    if existing:
                        continue

                    # Cria novo video
                    video = ViralVideo(
                        profile_id=profile.id,
                        platform_id=scraped_video.platform_id,
                        shortcode=scraped_video.shortcode,
                        source_url=scraped_video.source_url,
                        views_count=scraped_video.views_count,
                        likes_count=scraped_video.likes_count,
                        comments_count=scraped_video.comments_count,
                        shares_count=scraped_video.shares_count,
                        caption=scraped_video.caption,
                        hashtags=scraped_video.hashtags,
                        mentions=scraped_video.mentions,
                        duration_seconds=scraped_video.duration_seconds,
                        posted_at=scraped_video.posted_at,
                    )

                    # Calcula viral score estatistico
                    self._calculate_viral_score(video, profile)

                    db.add(video)
                    videos_saved += 1

                    if video.passes_prefilter:
                        videos_prefiltered += 1

                except Exception as e:
                    errors.append(f"Erro ao salvar video {scraped_video.platform_id}: {e}")

            # Atualiza perfil
            profile.last_scraped_at = datetime.now()
            profile.total_videos_collected += videos_saved

            # Registra custo
            self.budget.register_cost("apify", Decimal(str(result.cost_usd)), videos_saved, db)
            self.budget.increment_counter("scraping_runs", 1, db)
            self.budget.increment_counter("videos_collected", videos_saved, db)

            # Finaliza metrica
            run_metric.items_input = len(result.videos)
            run_metric.items_processed = videos_saved
            run_metric.items_failed = len(errors)
            run_metric.actual_cost_usd = Decimal(str(result.cost_usd))
            run_metric.complete(success=len(errors) == 0)

            db.commit()

            duration = (datetime.now() - start_time).total_seconds()

            print(f"[Watcher] Concluido: {videos_saved} salvos, {videos_prefiltered} pre-filtrados")

            return WatcherResult(
                run_id=run_id,
                profile_username=profile.username,
                videos_collected=videos_saved,
                videos_prefiltered=videos_prefiltered,
                cost_usd=result.cost_usd,
                duration_seconds=duration,
                errors=errors,
            )

        except Exception as e:
            # Registra falha
            if "run_metric" in locals():
                run_metric.complete(success=False, error=str(e))
                db.commit()
            raise
        finally:
            db.close()

    def run_all_active_profiles(self, max_videos_per_profile: int = 30) -> list[WatcherResult]:
        """Executa scraping para todos os perfis ativos.

        Args:
            max_videos_per_profile: Maximo de videos por perfil

        Returns:
            Lista de WatcherResult
        """
        db = get_sync_db()
        try:
            # Busca perfis ativos ordenados por prioridade
            stmt = (
                select(MonitoredProfile)
                .where(MonitoredProfile.is_active == True)
                .order_by(MonitoredProfile.priority.desc())
                .limit(settings.max_daily_scraping_profiles)
            )
            profiles = db.execute(stmt).scalars().all()

            results = []
            for profile in profiles:
                try:
                    # Verifica budget antes de cada perfil
                    status = self.budget.get_daily_status()
                    if status["budget"]["exceeded"]:
                        print("[Watcher] Budget diario excedido, parando scraping")
                        break

                    result = self.run(
                        profile_id=profile.id,
                        max_videos=max_videos_per_profile,
                    )
                    results.append(result)

                except Exception as e:
                    print(f"[Watcher] Erro no perfil @{profile.username}: {e}")

            return results
        finally:
            db.close()

    def _get_profile(
        self,
        db: Session,
        profile_id: Optional[int],
        username: Optional[str],
    ) -> Optional[MonitoredProfile]:
        """Busca perfil por ID ou username."""
        if profile_id:
            return db.get(MonitoredProfile, profile_id)
        elif username:
            stmt = select(MonitoredProfile).where(
                MonitoredProfile.username == username.lower().replace("@", "")
            )
            return db.execute(stmt).scalar_one_or_none()
        return None

    def _calculate_viral_score(self, video: ViralVideo, profile: MonitoredProfile) -> None:
        """Calcula viral score estatistico do video.

        Formula:
        - 40% normalized_views
        - 40% normalized_engagement
        - 20% recency_score
        """
        # Normaliza views (0-1, cap em 2x a media do nicho)
        avg_views = profile.niche_avg_views or 50000
        video.normalized_views = Decimal(
            str(min(video.views_count / (avg_views * 2), 1.0))
        )

        # Normaliza engagement
        avg_engagement = (profile.niche_avg_likes or 5000) + (profile.niche_avg_comments or 500)
        total_engagement = video.likes_count + video.comments_count
        video.normalized_engagement = Decimal(
            str(min(total_engagement / (avg_engagement * 2), 1.0))
        )

        # Calcula recency (decai ao longo de 7 dias)
        if video.posted_at:
            days_old = (datetime.now() - video.posted_at).days
            video.recency_score = Decimal(str(max(1.0 - (days_old / 7.0), 0.0)))
        else:
            video.recency_score = Decimal("0.5")

        # Score final
        video.statistical_viral_score = (
            video.normalized_views * Decimal("0.4")
            + video.normalized_engagement * Decimal("0.4")
            + video.recency_score * Decimal("0.2")
        )

        # Define se passa no pre-filtro
        video.passes_prefilter = float(video.statistical_viral_score) >= settings.min_statistical_score

    def add_profile(
        self,
        username: str,
        niche: str,
        priority: int = 1,
        niche_avg_views: int = 50000,
        niche_avg_likes: int = 5000,
        niche_avg_comments: int = 500,
    ) -> MonitoredProfile:
        """Adiciona novo perfil para monitoramento.

        Args:
            username: Username do Instagram (sem @)
            niche: Categoria/nicho do perfil
            priority: Prioridade (1-5)
            niche_avg_views: Media de views do nicho
            niche_avg_likes: Media de likes do nicho
            niche_avg_comments: Media de comentarios do nicho

        Returns:
            MonitoredProfile criado
        """
        db = get_sync_db()
        try:
            # Normaliza username
            username = username.lower().replace("@", "").strip()

            # Verifica se ja existe
            existing = db.execute(
                select(MonitoredProfile).where(MonitoredProfile.username == username)
            ).scalar_one_or_none()

            if existing:
                raise ValueError(f"Perfil @{username} ja existe")

            profile = MonitoredProfile(
                username=username,
                niche=niche,
                priority=priority,
                niche_avg_views=niche_avg_views,
                niche_avg_likes=niche_avg_likes,
                niche_avg_comments=niche_avg_comments,
            )

            db.add(profile)
            db.commit()
            db.refresh(profile)

            print(f"[Watcher] Perfil @{username} adicionado com sucesso!")
            return profile
        finally:
            db.close()


# Singleton para uso global
watcher_agent = WatcherAgent()
