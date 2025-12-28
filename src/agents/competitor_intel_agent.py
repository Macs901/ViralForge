"""Competitor Intel Agent - Monitora e analisa concorrentes."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models.trends import Competitor, CompetitorAnalysis, Platform

settings = get_settings()


@dataclass
class CompetitorInsight:
    """Insight sobre um concorrente."""
    category: str  # content, timing, growth, strategy
    title: str
    description: str
    competitor_username: str
    action: Optional[str] = None
    data: dict = field(default_factory=dict)


@dataclass
class CompetitorSnapshot:
    """Snapshot de um concorrente."""
    username: str
    platform: str
    followers: int
    posts: int
    avg_views: float
    avg_likes: float
    avg_engagement_rate: float
    posting_frequency: float  # posts per day
    top_hashtags: list[str] = field(default_factory=list)
    top_content_types: dict = field(default_factory=dict)
    best_posting_times: list[str] = field(default_factory=list)
    recent_top_posts: list[dict] = field(default_factory=list)


@dataclass
class CompetitorBenchmark:
    """Benchmarking contra concorrentes."""
    your_followers: int
    your_avg_engagement: float
    competitor_avg_followers: int
    competitor_avg_engagement: float
    your_ranking: int  # Sua posicao no ranking
    total_competitors: int
    gap_to_leader: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class CompetitorIntelResult:
    """Resultado do Competitor Intel."""
    run_id: str
    competitors_analyzed: int
    insights_found: int
    duration_seconds: float
    snapshots: list[CompetitorSnapshot] = field(default_factory=list)
    insights: list[CompetitorInsight] = field(default_factory=list)
    benchmark: Optional[CompetitorBenchmark] = None


class CompetitorIntelAgent:
    """Agent que monitora e analisa concorrentes."""

    def __init__(self):
        """Inicializa o agent."""
        self.run_id = str(uuid4())

    def add_competitor(
        self,
        username: str,
        platform: Platform,
        niche: Optional[str] = None,
        tier: str = "similar",
        notes: Optional[str] = None,
    ) -> int:
        """Adiciona um novo concorrente para monitorar.

        Args:
            username: Username do concorrente
            platform: Plataforma
            niche: Nicho do concorrente
            tier: Tier (bigger, similar, smaller)
            notes: Notas adicionais

        Returns:
            ID do concorrente criado
        """
        db = get_sync_db()
        try:
            # Verifica se ja existe
            existing = db.execute(
                select(Competitor).where(
                    Competitor.username == username,
                    Competitor.platform == platform,
                )
            ).scalar_one_or_none()

            if existing:
                return existing.id

            competitor = Competitor(
                username=username,
                platform=platform,
                niche=niche,
                tier=tier,
                notes=notes,
                is_active=True,
            )
            db.add(competitor)
            db.commit()
            db.refresh(competitor)
            return competitor.id

        finally:
            db.close()

    def analyze_competitor(
        self,
        username: str,
        platform: Platform,
        max_posts: int = 30,
    ) -> Optional[CompetitorSnapshot]:
        """Analisa um concorrente especifico.

        Args:
            username: Username do concorrente
            platform: Plataforma
            max_posts: Maximo de posts para analisar

        Returns:
            CompetitorSnapshot ou None
        """
        try:
            if platform == Platform.INSTAGRAM:
                return self._analyze_instagram_competitor(username, max_posts)
            elif platform == Platform.TIKTOK:
                return self._analyze_tiktok_competitor(username, max_posts)
            elif platform == Platform.YOUTUBE:
                return self._analyze_youtube_competitor(username, max_posts)
        except Exception as e:
            print(f"[CompetitorIntel] Erro analisando {username}: {e}")

        return None

    def _analyze_instagram_competitor(
        self,
        username: str,
        max_posts: int,
    ) -> Optional[CompetitorSnapshot]:
        """Analisa concorrente do Instagram."""
        try:
            from src.tools.instagram_scraper import instagram_scraper

            # Busca perfil
            profile = instagram_scraper.scrape_profile(username)

            if not profile:
                return None

            # Busca posts recentes
            posts_result = instagram_scraper.scrape_profile_posts(username, max_posts=max_posts)
            posts = posts_result.posts if posts_result else []

            # Calcula metricas
            total_views = 0
            total_likes = 0
            total_comments = 0
            hashtags_count = {}
            content_types = {}
            posting_times = []

            for post in posts:
                views = post.get("views_count", 0)
                likes = post.get("likes_count", 0)
                comments = post.get("comments_count", 0)

                total_views += views
                total_likes += likes
                total_comments += comments

                # Content type
                media_type = post.get("media_type", "unknown")
                content_types[media_type] = content_types.get(media_type, 0) + 1

                # Hashtags
                for tag in post.get("hashtags", []):
                    hashtags_count[tag] = hashtags_count.get(tag, 0) + 1

                # Posting time
                taken_at = post.get("taken_at")
                if taken_at:
                    posting_times.append(taken_at)

            n = len(posts) if posts else 1

            # Top hashtags
            top_hashtags = [
                h for h, _ in sorted(hashtags_count.items(), key=lambda x: x[1], reverse=True)[:10]
            ]

            # Frequencia de postagem
            if len(posting_times) >= 2:
                dates = sorted(posting_times)
                days = (dates[-1] - dates[0]).days or 1
                posting_frequency = len(posts) / days
            else:
                posting_frequency = 0

            # Best posting times
            hours = {}
            for t in posting_times:
                h = t.hour
                hours[h] = hours.get(h, 0) + 1
            best_hours = sorted(hours.keys(), key=lambda x: hours[x], reverse=True)[:3]
            best_posting_times = [f"{h}:00" for h in best_hours]

            # Top posts
            recent_top_posts = sorted(
                posts,
                key=lambda x: x.get("likes_count", 0),
                reverse=True
            )[:5]

            return CompetitorSnapshot(
                username=username,
                platform="instagram",
                followers=profile.get("follower_count", 0),
                posts=profile.get("media_count", 0),
                avg_views=total_views / n,
                avg_likes=total_likes / n,
                avg_engagement_rate=(total_likes + total_comments) / (total_views or 1),
                posting_frequency=posting_frequency,
                top_hashtags=top_hashtags,
                top_content_types=content_types,
                best_posting_times=best_posting_times,
                recent_top_posts=[
                    {
                        "url": p.get("url"),
                        "likes": p.get("likes_count"),
                        "comments": p.get("comments_count"),
                        "caption": (p.get("caption", "") or "")[:100],
                    }
                    for p in recent_top_posts
                ],
            )

        except ImportError:
            print("[CompetitorIntel] instagram_scraper nao disponivel")
        except Exception as e:
            print(f"[CompetitorIntel] Erro Instagram: {e}")

        return None

    def _analyze_tiktok_competitor(
        self,
        username: str,
        max_posts: int,
    ) -> Optional[CompetitorSnapshot]:
        """Analisa concorrente do TikTok."""
        try:
            from src.tools.tiktok_scraper import tiktok_scraper

            # Busca perfil e videos
            result = tiktok_scraper.scrape_profile(username, max_videos=max_posts)

            if not result:
                return None

            videos = result.videos or []

            # Calcula metricas
            total_views = sum(v.views for v in videos)
            total_likes = sum(v.likes for v in videos)
            total_comments = sum(v.comments for v in videos)
            n = len(videos) if videos else 1

            # Hashtags
            hashtags_count = {}
            for v in videos:
                for tag in v.hashtags:
                    hashtags_count[tag] = hashtags_count.get(tag, 0) + 1

            top_hashtags = [
                h for h, _ in sorted(hashtags_count.items(), key=lambda x: x[1], reverse=True)[:10]
            ]

            # Top posts
            recent_top_posts = sorted(videos, key=lambda x: x.views, reverse=True)[:5]

            return CompetitorSnapshot(
                username=username,
                platform="tiktok",
                followers=result.followers,
                posts=len(videos),
                avg_views=total_views / n,
                avg_likes=total_likes / n,
                avg_engagement_rate=(total_likes + total_comments) / (total_views or 1),
                posting_frequency=0,  # TikTok nao da timestamps
                top_hashtags=top_hashtags,
                top_content_types={"video": len(videos)},
                best_posting_times=[],
                recent_top_posts=[
                    {
                        "url": v.url,
                        "views": v.views,
                        "likes": v.likes,
                        "caption": (v.caption or "")[:100],
                    }
                    for v in recent_top_posts
                ],
            )

        except ImportError:
            print("[CompetitorIntel] tiktok_scraper nao disponivel")
        except Exception as e:
            print(f"[CompetitorIntel] Erro TikTok: {e}")

        return None

    def _analyze_youtube_competitor(
        self,
        username: str,
        max_posts: int,
    ) -> Optional[CompetitorSnapshot]:
        """Analisa concorrente do YouTube."""
        try:
            from src.tools.youtube_scraper import youtube_scraper

            # Busca shorts
            shorts = youtube_scraper.scrape_channel_shorts(username, max_shorts=max_posts)

            if not shorts:
                return None

            # Calcula metricas
            total_views = sum(s.views for s in shorts)
            total_likes = sum(s.likes for s in shorts)
            n = len(shorts) if shorts else 1

            # Hashtags
            hashtags_count = {}
            for s in shorts:
                for tag in s.hashtags:
                    hashtags_count[tag] = hashtags_count.get(tag, 0) + 1

            top_hashtags = [
                h for h, _ in sorted(hashtags_count.items(), key=lambda x: x[1], reverse=True)[:10]
            ]

            # Top posts
            recent_top_posts = sorted(shorts, key=lambda x: x.views, reverse=True)[:5]

            return CompetitorSnapshot(
                username=username,
                platform="youtube",
                followers=0,  # YouTube nao retorna diretamente
                posts=len(shorts),
                avg_views=total_views / n,
                avg_likes=total_likes / n,
                avg_engagement_rate=total_likes / (total_views or 1),
                posting_frequency=0,
                top_hashtags=top_hashtags,
                top_content_types={"short": len(shorts)},
                best_posting_times=[],
                recent_top_posts=[
                    {
                        "url": s.url,
                        "views": s.views,
                        "likes": s.likes,
                        "title": (s.title or "")[:100],
                    }
                    for s in recent_top_posts
                ],
            )

        except ImportError:
            print("[CompetitorIntel] youtube_scraper nao disponivel")
        except Exception as e:
            print(f"[CompetitorIntel] Erro YouTube: {e}")

        return None

    def run_intel(
        self,
        platform: Optional[Platform] = None,
        max_posts_per_competitor: int = 20,
    ) -> CompetitorIntelResult:
        """Executa analise completa de todos os concorrentes.

        Args:
            platform: Plataforma especifica ou None para todas
            max_posts_per_competitor: Maximo de posts por concorrente

        Returns:
            CompetitorIntelResult
        """
        start_time = datetime.now()
        snapshots = []
        insights = []

        db = get_sync_db()
        try:
            # Busca concorrentes ativos
            query = select(Competitor).where(Competitor.is_active == True)
            if platform:
                query = query.where(Competitor.platform == platform)

            competitors = list(db.execute(query).scalars().all())

            print(f"[CompetitorIntel] Analisando {len(competitors)} concorrentes...")

            for competitor in competitors:
                print(f"[CompetitorIntel] Analisando {competitor.username}...")

                snapshot = self.analyze_competitor(
                    competitor.username,
                    competitor.platform,
                    max_posts_per_competitor,
                )

                if snapshot:
                    snapshots.append(snapshot)

                    # Atualiza dados do concorrente no banco
                    competitor.follower_count = snapshot.followers
                    competitor.avg_views = Decimal(str(snapshot.avg_views))
                    competitor.avg_likes = Decimal(str(snapshot.avg_likes))
                    competitor.avg_engagement_rate = Decimal(str(snapshot.avg_engagement_rate))
                    competitor.posting_frequency = Decimal(str(snapshot.posting_frequency))
                    competitor.top_hashtags = snapshot.top_hashtags
                    competitor.top_content_types = snapshot.top_content_types
                    competitor.best_posting_times = snapshot.best_posting_times
                    competitor.last_scraped_at = datetime.now()

                    # Gera insights
                    comp_insights = self._generate_competitor_insights(competitor, snapshot)
                    insights.extend(comp_insights)

            db.commit()

            # Gera benchmark
            benchmark = self._generate_benchmark(snapshots) if snapshots else None

        finally:
            db.close()

        return CompetitorIntelResult(
            run_id=self.run_id,
            competitors_analyzed=len(snapshots),
            insights_found=len(insights),
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            snapshots=snapshots,
            insights=insights,
            benchmark=benchmark,
        )

    def _generate_competitor_insights(
        self,
        competitor: Competitor,
        snapshot: CompetitorSnapshot,
    ) -> list[CompetitorInsight]:
        """Gera insights sobre um concorrente."""
        insights = []

        # Insight de engajamento
        if snapshot.avg_engagement_rate > 0.05:
            insights.append(CompetitorInsight(
                category="engagement",
                title="Alto engajamento",
                description=f"{competitor.username} tem taxa de engajamento de {snapshot.avg_engagement_rate:.1%}",
                competitor_username=competitor.username,
                action="Analise os hooks e CTAs deste perfil",
                data={"engagement_rate": snapshot.avg_engagement_rate},
            ))

        # Insight de hashtags
        if snapshot.top_hashtags:
            insights.append(CompetitorInsight(
                category="strategy",
                title="Hashtags do concorrente",
                description=f"Top hashtags: {', '.join(snapshot.top_hashtags[:5])}",
                competitor_username=competitor.username,
                action="Considere usar hashtags similares",
                data={"hashtags": snapshot.top_hashtags},
            ))

        # Insight de frequencia
        if snapshot.posting_frequency > 1:
            insights.append(CompetitorInsight(
                category="timing",
                title="Alta frequencia de postagem",
                description=f"{competitor.username} posta {snapshot.posting_frequency:.1f}x por dia",
                competitor_username=competitor.username,
                data={"frequency": snapshot.posting_frequency},
            ))

        # Insight de top posts
        if snapshot.recent_top_posts:
            top_post = snapshot.recent_top_posts[0]
            insights.append(CompetitorInsight(
                category="content",
                title="Post de melhor performance",
                description=f"Top post com {top_post.get('likes', 0):,} likes",
                competitor_username=competitor.username,
                action="Analise o que fez este post viralizar",
                data={"top_post": top_post},
            ))

        return insights

    def _generate_benchmark(
        self,
        snapshots: list[CompetitorSnapshot],
    ) -> CompetitorBenchmark:
        """Gera benchmark contra concorrentes."""
        if not snapshots:
            return CompetitorBenchmark(
                your_followers=0,
                your_avg_engagement=0,
                competitor_avg_followers=0,
                competitor_avg_engagement=0,
                your_ranking=0,
                total_competitors=0,
            )

        # Medias dos concorrentes
        avg_followers = sum(s.followers for s in snapshots) / len(snapshots)
        avg_engagement = sum(s.avg_engagement_rate for s in snapshots) / len(snapshots)

        # Leader
        leader = max(snapshots, key=lambda x: x.followers)

        recommendations = []

        if avg_engagement > 0.03:
            recommendations.append("Foque em aumentar engajamento para igualar concorrentes")
        if avg_followers > 10000:
            recommendations.append("Priorize crescimento de seguidores")

        # Hashtags mais comuns
        all_hashtags = []
        for s in snapshots:
            all_hashtags.extend(s.top_hashtags)

        from collections import Counter
        common_hashtags = Counter(all_hashtags).most_common(5)
        if common_hashtags:
            recommendations.append(f"Use hashtags comuns: {', '.join(h for h, _ in common_hashtags)}")

        return CompetitorBenchmark(
            your_followers=0,  # TODO: Integrar com seu perfil
            your_avg_engagement=0,
            competitor_avg_followers=int(avg_followers),
            competitor_avg_engagement=avg_engagement,
            your_ranking=0,
            total_competitors=len(snapshots),
            gap_to_leader={
                "username": leader.username,
                "followers": leader.followers,
                "engagement": leader.avg_engagement_rate,
            },
            recommendations=recommendations,
        )

    def get_competitors_list(
        self,
        platform: Optional[Platform] = None,
        active_only: bool = True,
    ) -> list[dict]:
        """Lista todos os concorrentes monitorados.

        Args:
            platform: Filtrar por plataforma
            active_only: Apenas ativos

        Returns:
            Lista de concorrentes
        """
        db = get_sync_db()
        try:
            query = select(Competitor)
            if active_only:
                query = query.where(Competitor.is_active == True)
            if platform:
                query = query.where(Competitor.platform == platform)

            competitors = list(db.execute(query).scalars().all())

            return [
                {
                    "id": c.id,
                    "username": c.username,
                    "platform": c.platform.value,
                    "tier": c.tier,
                    "niche": c.niche,
                    "followers": c.follower_count,
                    "avg_engagement": float(c.avg_engagement_rate or 0),
                    "last_scraped": c.last_scraped_at.isoformat() if c.last_scraped_at else None,
                }
                for c in competitors
            ]

        finally:
            db.close()


# Factory function
def get_competitor_intel() -> CompetitorIntelAgent:
    """Retorna instancia do CompetitorIntelAgent."""
    return CompetitorIntelAgent()
