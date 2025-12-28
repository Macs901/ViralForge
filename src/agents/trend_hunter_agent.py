"""Trend Hunter Agent - Detecta tendencias em tempo real."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models.trends import Trend, TrendStatus, TrendType, Platform

settings = get_settings()


@dataclass
class DetectedTrend:
    """Tendencia detectada."""
    name: str
    trend_type: TrendType
    platform: Platform
    score: float
    velocity: float  # Taxa de crescimento
    volume: int  # Quantidade de posts
    description: Optional[str] = None
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    related_hashtags: list[str] = field(default_factory=list)
    example_videos: list[dict] = field(default_factory=list)


@dataclass
class TrendHunterResult:
    """Resultado da caca de tendencias."""
    run_id: str
    trends_detected: int
    trends_by_type: dict[str, int] = field(default_factory=dict)
    trends_by_platform: dict[str, int] = field(default_factory=dict)
    top_trends: list[DetectedTrend] = field(default_factory=list)
    duration_seconds: float = 0.0


class TrendHunterAgent:
    """Agent que detecta tendencias em multiplas plataformas."""

    def __init__(self):
        """Inicializa o agent."""
        self.run_id = str(uuid4())

    def hunt_all(
        self,
        platforms: Optional[list[Platform]] = None,
        limit_per_platform: int = 20,
    ) -> TrendHunterResult:
        """Busca tendencias em todas as plataformas.

        Args:
            platforms: Plataformas para buscar (None = todas)
            limit_per_platform: Limite por plataforma

        Returns:
            TrendHunterResult
        """
        start_time = datetime.now()
        platforms = platforms or [Platform.INSTAGRAM, Platform.TIKTOK, Platform.YOUTUBE]

        all_trends = []

        for platform in platforms:
            print(f"[TrendHunter] Buscando tendencias em {platform.value}...")
            try:
                if platform == Platform.INSTAGRAM:
                    trends = self._hunt_instagram(limit_per_platform)
                elif platform == Platform.TIKTOK:
                    trends = self._hunt_tiktok(limit_per_platform)
                elif platform == Platform.YOUTUBE:
                    trends = self._hunt_youtube(limit_per_platform)
                else:
                    trends = []

                all_trends.extend(trends)
            except Exception as e:
                print(f"[TrendHunter] Erro em {platform.value}: {e}")

        # Salva no banco
        saved = self._save_trends(all_trends)

        # Agrupa por tipo e plataforma
        by_type = {}
        by_platform = {}
        for t in all_trends:
            by_type[t.trend_type.value] = by_type.get(t.trend_type.value, 0) + 1
            by_platform[t.platform.value] = by_platform.get(t.platform.value, 0) + 1

        # Top trends por score
        top_trends = sorted(all_trends, key=lambda t: t.score, reverse=True)[:10]

        return TrendHunterResult(
            run_id=self.run_id,
            trends_detected=len(all_trends),
            trends_by_type=by_type,
            trends_by_platform=by_platform,
            top_trends=top_trends,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

    def _hunt_instagram(self, limit: int) -> list[DetectedTrend]:
        """Busca tendencias no Instagram."""
        trends = []

        try:
            from src.tools.instagram_scraper import instagram_scraper

            # 1. Busca hashtags populares
            for hashtag in ["viral", "reels", "trending", "fyp"]:
                try:
                    result = instagram_scraper.scrape_hashtag(hashtag, max_posts=50)

                    # Analisa videos para extrair padroes
                    audios = {}
                    hashtags_count = {}

                    for video in result.videos[:30]:
                        # Conta audios
                        music = video.get("musicInfo", {})
                        if music:
                            audio_id = music.get("audio_id", "")
                            if audio_id:
                                if audio_id not in audios:
                                    audios[audio_id] = {
                                        "name": music.get("title", "Unknown"),
                                        "artist": music.get("artist_name"),
                                        "count": 0,
                                        "total_views": 0,
                                    }
                                audios[audio_id]["count"] += 1
                                audios[audio_id]["total_views"] += video.get("views_count", 0)

                        # Conta hashtags
                        for tag in video.get("hashtags", []):
                            hashtags_count[tag] = hashtags_count.get(tag, 0) + 1

                    # Cria trends de audios populares
                    for audio_id, data in sorted(audios.items(), key=lambda x: x[1]["count"], reverse=True)[:5]:
                        if data["count"] >= 3:  # Minimo 3 videos usando
                            trends.append(DetectedTrend(
                                name=data["name"],
                                trend_type=TrendType.AUDIO,
                                platform=Platform.INSTAGRAM,
                                score=data["count"] * 10 + data["total_views"] / 10000,
                                velocity=data["count"] / 50,  # % de videos usando
                                volume=data["count"],
                                external_id=audio_id,
                            ))

                    # Cria trends de hashtags
                    for tag, count in sorted(hashtags_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                        if count >= 5 and tag not in ["viral", "reels", "trending", "fyp"]:
                            trends.append(DetectedTrend(
                                name=f"#{tag}",
                                trend_type=TrendType.HASHTAG,
                                platform=Platform.INSTAGRAM,
                                score=count * 5,
                                velocity=count / 50,
                                volume=count,
                            ))

                except Exception as e:
                    print(f"[TrendHunter] Erro ao processar #{hashtag}: {e}")

        except ImportError:
            print("[TrendHunter] instagram_scraper nao disponivel")

        return trends[:limit]

    def _hunt_tiktok(self, limit: int) -> list[DetectedTrend]:
        """Busca tendencias no TikTok."""
        trends = []

        try:
            from src.tools.tiktok_scraper import tiktok_scraper

            # 1. Busca sons trending
            sounds = tiktok_scraper.scrape_trending_sounds(limit=30)
            for sound in sounds[:10]:
                trends.append(DetectedTrend(
                    name=sound.title or "Unknown Sound",
                    trend_type=TrendType.AUDIO,
                    platform=Platform.TIKTOK,
                    score=sound.video_count * 10,
                    velocity=0.5,  # Placeholder
                    volume=sound.video_count,
                    external_id=sound.sound_id,
                    description=f"Por {sound.author}" if sound.author else None,
                ))

            # 2. Busca hashtags trending
            for hashtag in ["fyp", "viral", "trending"]:
                try:
                    result = tiktok_scraper.scrape_hashtag(hashtag, max_videos=30)

                    hashtags_count = {}
                    for video in result.videos:
                        for tag in video.hashtags:
                            if tag.lower() not in ["fyp", "viral", "trending", "foryou", "foryoupage"]:
                                hashtags_count[tag] = hashtags_count.get(tag, 0) + 1

                    for tag, count in sorted(hashtags_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                        if count >= 3:
                            trends.append(DetectedTrend(
                                name=f"#{tag}",
                                trend_type=TrendType.HASHTAG,
                                platform=Platform.TIKTOK,
                                score=count * 5,
                                velocity=count / 30,
                                volume=count,
                            ))

                except Exception as e:
                    print(f"[TrendHunter] Erro TikTok #{hashtag}: {e}")

        except ImportError:
            print("[TrendHunter] tiktok_scraper nao disponivel")

        return trends[:limit]

    def _hunt_youtube(self, limit: int) -> list[DetectedTrend]:
        """Busca tendencias no YouTube."""
        trends = []

        try:
            from src.tools.youtube_scraper import youtube_scraper

            # 1. Busca Shorts trending
            shorts = youtube_scraper.scrape_trending_shorts(limit=30)

            # Analisa padroes
            hashtags_count = {}
            categories = {}

            for short in shorts:
                for tag in short.hashtags:
                    if tag.lower() not in ["shorts", "short", "viral"]:
                        hashtags_count[tag] = hashtags_count.get(tag, 0) + 1

                if short.category_name:
                    categories[short.category_name] = categories.get(short.category_name, 0) + 1

            # Trends de hashtags
            for tag, count in sorted(hashtags_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                if count >= 2:
                    trends.append(DetectedTrend(
                        name=f"#{tag}",
                        trend_type=TrendType.HASHTAG,
                        platform=Platform.YOUTUBE,
                        score=count * 5,
                        velocity=count / 30,
                        volume=count,
                    ))

            # Trends de categorias/topicos
            for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]:
                trends.append(DetectedTrend(
                    name=category,
                    trend_type=TrendType.TOPIC,
                    platform=Platform.YOUTUBE,
                    score=count * 10,
                    velocity=count / 30,
                    volume=count,
                ))

        except ImportError:
            print("[TrendHunter] youtube_scraper nao disponivel")

        return trends[:limit]

    def _save_trends(self, trends: list[DetectedTrend]) -> int:
        """Salva tendencias no banco."""
        db = get_sync_db()
        saved = 0

        try:
            for trend in trends:
                # Verifica se ja existe
                existing = db.execute(
                    select(Trend).where(
                        Trend.name == trend.name,
                        Trend.platform == trend.platform,
                        Trend.trend_type == trend.trend_type,
                    )
                ).scalar_one_or_none()

                if existing:
                    # Atualiza score e historico
                    existing.current_score = Decimal(str(trend.score))
                    existing.velocity = Decimal(str(trend.velocity))
                    existing.volume = trend.volume
                    existing.last_updated_at = datetime.now()

                    # Adiciona ao historico
                    history = existing.score_history or []
                    history.append({
                        "date": datetime.now().isoformat(),
                        "score": trend.score,
                        "volume": trend.volume,
                    })
                    existing.score_history = history[-30:]  # Mantem ultimos 30

                    # Atualiza status baseado na velocidade
                    if trend.velocity > 0.3:
                        existing.status = TrendStatus.RISING
                    elif trend.velocity > 0.1:
                        existing.status = TrendStatus.PEAK
                    elif trend.velocity < 0:
                        existing.status = TrendStatus.DECLINING

                else:
                    # Cria novo
                    new_trend = Trend(
                        name=trend.name,
                        trend_type=trend.trend_type,
                        platform=trend.platform,
                        description=trend.description,
                        external_id=trend.external_id,
                        external_url=trend.external_url,
                        current_score=Decimal(str(trend.score)),
                        velocity=Decimal(str(trend.velocity)),
                        volume=trend.volume,
                        status=TrendStatus.EMERGING,
                        is_actionable=trend.score > 50,
                        related_hashtags=trend.related_hashtags,
                        example_videos=trend.example_videos,
                        score_history=[{
                            "date": datetime.now().isoformat(),
                            "score": trend.score,
                            "volume": trend.volume,
                        }],
                    )
                    db.add(new_trend)
                    saved += 1

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[TrendHunter] Erro ao salvar: {e}")
        finally:
            db.close()

        return saved

    def get_actionable_trends(
        self,
        platform: Optional[Platform] = None,
        trend_type: Optional[TrendType] = None,
        limit: int = 10,
    ) -> list[Trend]:
        """Retorna tendencias acionaveis (que podem ser replicadas).

        Args:
            platform: Filtrar por plataforma
            trend_type: Filtrar por tipo
            limit: Maximo de resultados

        Returns:
            Lista de Trend do banco
        """
        db = get_sync_db()
        try:
            query = select(Trend).where(
                Trend.is_actionable == True,
                Trend.status.in_([TrendStatus.EMERGING, TrendStatus.RISING, TrendStatus.PEAK])
            )

            if platform:
                query = query.where(Trend.platform == platform)
            if trend_type:
                query = query.where(Trend.trend_type == trend_type)

            query = query.order_by(Trend.current_score.desc()).limit(limit)

            return list(db.execute(query).scalars().all())
        finally:
            db.close()


# Factory function
def get_trend_hunter() -> TrendHunterAgent:
    """Retorna instancia do TrendHunterAgent."""
    return TrendHunterAgent()
