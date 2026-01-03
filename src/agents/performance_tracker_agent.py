"""Performance Tracker Agent - Monitora e analisa performance de conteudo."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models.trends import ContentQueue, ContentStatus, PerformanceMetric, Platform

settings = get_settings()


@dataclass
class PerformanceInsight:
    """Insight de performance."""
    category: str  # timing, content, engagement, growth
    title: str
    description: str
    impact: str  # high, medium, low
    action: Optional[str] = None
    data: dict = field(default_factory=dict)


@dataclass
class ContentPerformance:
    """Performance de um conteudo."""
    content_id: int
    title: str
    platform: str
    published_at: Optional[datetime]
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    viral_score: float = 0.0
    performance_tier: str = "average"  # viral, high, average, low, flop


@dataclass
class PerformanceReport:
    """Relatorio de performance."""
    period_start: datetime
    period_end: datetime
    total_posts: int
    total_views: int
    total_engagement: int
    avg_engagement_rate: float
    best_performing: list[ContentPerformance]
    worst_performing: list[ContentPerformance]
    insights: list[PerformanceInsight]
    trends: dict = field(default_factory=dict)


@dataclass
class PerformanceTrackerResult:
    """Resultado do Performance Tracker."""
    run_id: str
    metrics_collected: int
    reports_generated: int
    insights_found: int
    duration_seconds: float
    report: Optional[PerformanceReport] = None


class PerformanceTrackerAgent:
    """Agent que monitora e analisa performance de conteudo."""

    def __init__(self):
        """Inicializa o agent."""
        self.run_id = str(uuid4())

    def collect_metrics(
        self,
        platform: Optional[Platform] = None,
        days: int = 7,
    ) -> int:
        """Coleta metricas de posts publicados.

        Args:
            platform: Plataforma especifica ou None para todas
            days: Ultimos N dias

        Returns:
            Numero de metricas coletadas
        """
        collected = 0
        start_date = datetime.now() - timedelta(days=days)

        # Coleta por plataforma
        if platform:
            platforms = [platform]
        else:
            platforms = [Platform.INSTAGRAM, Platform.TIKTOK, Platform.YOUTUBE]

        for p in platforms:
            try:
                if p == Platform.INSTAGRAM:
                    collected += self._collect_instagram_metrics(start_date)
                elif p == Platform.TIKTOK:
                    collected += self._collect_tiktok_metrics(start_date)
                elif p == Platform.YOUTUBE:
                    collected += self._collect_youtube_metrics(start_date)
            except Exception as e:
                print(f"[PerformanceTracker] Erro coletando {p.value}: {e}")

        return collected

    def _collect_instagram_metrics(self, since: datetime) -> int:
        """Coleta metricas do Instagram via scraper real."""
        collected = 0
        db = get_sync_db()

        try:
            # Busca posts publicados
            query = select(ContentQueue).where(
                ContentQueue.status == ContentStatus.PUBLISHED,
                ContentQueue.published_at >= since,
            )

            posts = list(db.execute(query).scalars().all())

            for post in posts:
                published_urls = post.published_urls or {}
                insta_url = published_urls.get("instagram")

                if not insta_url:
                    continue

                try:
                    from src.tools.instagram_scraper import instagram_scraper

                    # Coleta metricas reais via scraper
                    metrics = instagram_scraper.get_post_metrics(insta_url)

                    if metrics:
                        perf_metric = PerformanceMetric(
                            content_id=post.id,
                            platform=Platform.INSTAGRAM,
                            post_url=insta_url,
                            views=metrics.get("views", 0),
                            likes=metrics.get("likes", 0),
                            comments=metrics.get("comments", 0),
                            shares=metrics.get("shares", 0),
                            saves=metrics.get("saves", 0),
                        )

                        # Calcula engagement rate
                        total_engagement = (
                            perf_metric.likes +
                            perf_metric.comments +
                            perf_metric.shares +
                            perf_metric.saves
                        )
                        if perf_metric.views > 0:
                            perf_metric.engagement_rate = Decimal(
                                str(total_engagement / perf_metric.views)
                            )

                        db.add(perf_metric)
                        collected += 1
                        print(f"[PerformanceTracker] Instagram {post.id}: {metrics.get('views', 0)} views")

                except Exception as e:
                    print(f"[PerformanceTracker] Erro Instagram post {post.id}: {e}")

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"[PerformanceTracker] Erro: {e}")
        finally:
            db.close()

        return collected

    def _collect_tiktok_metrics(self, since: datetime) -> int:
        """Coleta metricas do TikTok via scraper real."""
        collected = 0
        db = get_sync_db()

        try:
            query = select(ContentQueue).where(
                ContentQueue.status == ContentStatus.PUBLISHED,
                ContentQueue.published_at >= since,
            )

            posts = list(db.execute(query).scalars().all())

            for post in posts:
                published_urls = post.published_urls or {}
                tiktok_url = published_urls.get("tiktok")

                if not tiktok_url:
                    continue

                try:
                    from src.tools.tiktok_scraper import tiktok_scraper

                    # Coleta metricas reais via scraper
                    video_info = tiktok_scraper.get_video_info(tiktok_url)

                    if video_info:
                        perf_metric = PerformanceMetric(
                            content_id=post.id,
                            platform=Platform.TIKTOK,
                            post_id=video_info.video_id,
                            post_url=tiktok_url,
                            views=video_info.views_count,
                            likes=video_info.likes_count,
                            comments=video_info.comments_count,
                            shares=video_info.shares_count,
                            saves=video_info.saves_count,
                        )

                        # Calcula engagement
                        total_engagement = (
                            perf_metric.likes +
                            perf_metric.comments +
                            perf_metric.shares +
                            perf_metric.saves
                        )
                        if perf_metric.views > 0:
                            perf_metric.engagement_rate = Decimal(
                                str(total_engagement / perf_metric.views)
                            )

                        db.add(perf_metric)
                        collected += 1
                        print(f"[PerformanceTracker] TikTok {post.id}: {video_info.views_count} views")

                except Exception as e:
                    print(f"[PerformanceTracker] Erro TikTok post {post.id}: {e}")

            db.commit()

        except Exception as e:
            db.rollback()
        finally:
            db.close()

        return collected

    def _collect_youtube_metrics(self, since: datetime) -> int:
        """Coleta metricas do YouTube via yt-dlp."""
        collected = 0
        db = get_sync_db()

        try:
            query = select(ContentQueue).where(
                ContentQueue.status == ContentStatus.PUBLISHED,
                ContentQueue.published_at >= since,
            )

            posts = list(db.execute(query).scalars().all())

            for post in posts:
                published_urls = post.published_urls or {}
                youtube_url = published_urls.get("youtube")

                if not youtube_url:
                    continue

                try:
                    from src.tools.youtube_scraper import youtube_scraper

                    # Coleta metricas reais via yt-dlp
                    video_info = youtube_scraper.get_video_info(youtube_url)

                    if video_info:
                        perf_metric = PerformanceMetric(
                            content_id=post.id,
                            platform=Platform.YOUTUBE,
                            post_id=video_info.video_id,
                            post_url=youtube_url,
                            views=video_info.view_count,
                            likes=video_info.like_count,
                            comments=video_info.comment_count,
                        )

                        # Calcula engagement
                        total_engagement = perf_metric.likes + perf_metric.comments
                        if perf_metric.views > 0:
                            perf_metric.engagement_rate = Decimal(
                                str(total_engagement / perf_metric.views)
                            )

                        db.add(perf_metric)
                        collected += 1
                        print(f"[PerformanceTracker] YouTube {post.id}: {video_info.view_count} views")

                except Exception as e:
                    print(f"[PerformanceTracker] Erro YouTube post {post.id}: {e}")

            db.commit()

        except Exception as e:
            db.rollback()
        finally:
            db.close()

        return collected

    def generate_report(
        self,
        days: int = 7,
        platform: Optional[Platform] = None,
    ) -> PerformanceReport:
        """Gera relatorio de performance.

        Args:
            days: Periodo em dias
            platform: Plataforma especifica ou None para todas

        Returns:
            PerformanceReport
        """
        period_start = datetime.now() - timedelta(days=days)
        period_end = datetime.now()

        db = get_sync_db()
        try:
            # Query base
            query = select(PerformanceMetric).where(
                PerformanceMetric.measured_at >= period_start
            )

            if platform:
                query = query.where(PerformanceMetric.platform == platform)

            metrics = list(db.execute(query).scalars().all())

            if not metrics:
                return PerformanceReport(
                    period_start=period_start,
                    period_end=period_end,
                    total_posts=0,
                    total_views=0,
                    total_engagement=0,
                    avg_engagement_rate=0.0,
                    best_performing=[],
                    worst_performing=[],
                    insights=[
                        PerformanceInsight(
                            category="data",
                            title="Sem dados",
                            description="Nenhuma metrica encontrada no periodo",
                            impact="high",
                            action="Publique conteudo e colete metricas",
                        )
                    ],
                )

            # Calcula agregados
            total_views = sum(m.views for m in metrics)
            total_engagement = sum(m.total_engagement for m in metrics)
            avg_engagement = (
                sum(float(m.engagement_rate or 0) for m in metrics) / len(metrics)
            )

            # Classifica performance
            performances = []
            for m in metrics:
                tier = self._classify_performance(m)
                performances.append(ContentPerformance(
                    content_id=m.content_id or 0,
                    title=f"Post {m.content_id}",
                    platform=m.platform.value,
                    published_at=m.measured_at,
                    views=m.views,
                    likes=m.likes,
                    comments=m.comments,
                    shares=m.shares,
                    saves=m.saves,
                    engagement_rate=float(m.engagement_rate or 0),
                    performance_tier=tier,
                ))

            # Ordena
            performances.sort(key=lambda x: x.views, reverse=True)
            best = performances[:5]
            worst = sorted(performances, key=lambda x: x.views)[:5]

            # Gera insights
            insights = self._generate_insights(metrics, performances)

            # Trends
            trends = self._analyze_trends(metrics)

            return PerformanceReport(
                period_start=period_start,
                period_end=period_end,
                total_posts=len(metrics),
                total_views=total_views,
                total_engagement=total_engagement,
                avg_engagement_rate=avg_engagement,
                best_performing=best,
                worst_performing=worst,
                insights=insights,
                trends=trends,
            )

        finally:
            db.close()

    def _classify_performance(self, metric: PerformanceMetric) -> str:
        """Classifica a performance de um conteudo."""
        engagement_rate = float(metric.engagement_rate or 0)

        if engagement_rate > 0.1:  # >10%
            return "viral"
        elif engagement_rate > 0.05:  # >5%
            return "high"
        elif engagement_rate > 0.02:  # >2%
            return "average"
        elif engagement_rate > 0.01:  # >1%
            return "low"
        else:
            return "flop"

    def _generate_insights(
        self,
        metrics: list[PerformanceMetric],
        performances: list[ContentPerformance],
    ) -> list[PerformanceInsight]:
        """Gera insights baseados nos dados."""
        insights = []

        if not metrics:
            return insights

        # Insight de engajamento
        avg_engagement = sum(float(m.engagement_rate or 0) for m in metrics) / len(metrics)

        if avg_engagement > 0.05:
            insights.append(PerformanceInsight(
                category="engagement",
                title="Engajamento excelente",
                description=f"Taxa media de {avg_engagement:.1%} esta acima da media",
                impact="high",
                data={"avg_engagement": avg_engagement},
            ))
        elif avg_engagement < 0.02:
            insights.append(PerformanceInsight(
                category="engagement",
                title="Engajamento baixo",
                description=f"Taxa media de {avg_engagement:.1%} precisa melhorar",
                impact="high",
                action="Revise seus hooks e CTAs",
                data={"avg_engagement": avg_engagement},
            ))

        # Insight de views
        total_views = sum(m.views for m in metrics)
        avg_views = total_views / len(metrics)

        insights.append(PerformanceInsight(
            category="reach",
            title="Alcance medio",
            description=f"Media de {int(avg_views):,} views por post",
            impact="medium",
            data={"avg_views": avg_views, "total_views": total_views},
        ))

        # Insight de performance tiers
        tiers = {}
        for p in performances:
            tiers[p.performance_tier] = tiers.get(p.performance_tier, 0) + 1

        viral_count = tiers.get("viral", 0) + tiers.get("high", 0)
        if viral_count >= len(performances) * 0.3:
            insights.append(PerformanceInsight(
                category="content",
                title="Alta taxa de viralizacao",
                description=f"{viral_count} de {len(performances)} posts com alta performance",
                impact="high",
                action="Continue com a estrategia atual",
            ))

        # Insight de plataforma
        platform_views = {}
        for m in metrics:
            p = m.platform.value
            platform_views[p] = platform_views.get(p, 0) + m.views

        if platform_views:
            best_platform = max(platform_views, key=platform_views.get)
            insights.append(PerformanceInsight(
                category="platform",
                title=f"Melhor plataforma: {best_platform}",
                description=f"{best_platform.title()} gerando mais alcance",
                impact="medium",
                action=f"Priorize conteudo para {best_platform}",
                data={"platform_views": platform_views},
            ))

        return insights

    def _analyze_trends(self, metrics: list[PerformanceMetric]) -> dict:
        """Analisa tendencias nos dados."""
        if len(metrics) < 3:
            return {"data_points": len(metrics), "trend": "insufficient_data"}

        # Agrupa por dia
        by_day = {}
        for m in metrics:
            day = m.measured_at.date() if m.measured_at else None
            if day:
                if day not in by_day:
                    by_day[day] = {"views": 0, "engagement": 0, "count": 0}
                by_day[day]["views"] += m.views
                by_day[day]["engagement"] += m.total_engagement
                by_day[day]["count"] += 1

        # Calcula tendencia
        sorted_days = sorted(by_day.keys())
        if len(sorted_days) >= 2:
            first_half = sorted_days[:len(sorted_days)//2]
            second_half = sorted_days[len(sorted_days)//2:]

            first_views = sum(by_day[d]["views"] for d in first_half)
            second_views = sum(by_day[d]["views"] for d in second_half)

            if first_views > 0:
                growth = (second_views - first_views) / first_views
                trend = "growing" if growth > 0.1 else "declining" if growth < -0.1 else "stable"
            else:
                growth = 0
                trend = "stable"
        else:
            growth = 0
            trend = "insufficient_data"

        return {
            "data_points": len(metrics),
            "trend": trend,
            "growth_rate": growth,
            "daily_breakdown": {
                str(day): data for day, data in by_day.items()
            },
        }

    def get_best_posting_times(
        self,
        platform: Optional[Platform] = None,
        days: int = 30,
    ) -> dict:
        """Analisa melhores horarios para postar.

        Args:
            platform: Plataforma especifica
            days: Periodo de analise

        Returns:
            Dict com melhores horarios
        """
        period_start = datetime.now() - timedelta(days=days)

        db = get_sync_db()
        try:
            query = select(PerformanceMetric).where(
                PerformanceMetric.measured_at >= period_start
            )
            if platform:
                query = query.where(PerformanceMetric.platform == platform)

            metrics = list(db.execute(query).scalars().all())

            if not metrics:
                return {"best_hours": [], "best_days": [], "insufficient_data": True}

            # Agrupa por hora
            by_hour = {}
            by_day = {}

            for m in metrics:
                if not m.measured_at:
                    continue

                hour = m.measured_at.hour
                day = m.measured_at.strftime("%A")
                engagement = float(m.engagement_rate or 0)

                if hour not in by_hour:
                    by_hour[hour] = {"total_engagement": 0, "count": 0}
                by_hour[hour]["total_engagement"] += engagement
                by_hour[hour]["count"] += 1

                if day not in by_day:
                    by_day[day] = {"total_engagement": 0, "count": 0}
                by_day[day]["total_engagement"] += engagement
                by_day[day]["count"] += 1

            # Calcula medias e ordena
            hour_avgs = {
                h: data["total_engagement"] / data["count"]
                for h, data in by_hour.items()
                if data["count"] > 0
            }
            best_hours = sorted(hour_avgs.keys(), key=lambda h: hour_avgs[h], reverse=True)[:5]

            day_avgs = {
                d: data["total_engagement"] / data["count"]
                for d, data in by_day.items()
                if data["count"] > 0
            }
            best_days = sorted(day_avgs.keys(), key=lambda d: day_avgs[d], reverse=True)[:3]

            return {
                "best_hours": [{"hour": h, "avg_engagement": round(hour_avgs[h], 4)} for h in best_hours],
                "best_days": [{"day": d, "avg_engagement": round(day_avgs[d], 4)} for d in best_days],
                "sample_size": len(metrics),
            }

        finally:
            db.close()

    def run(
        self,
        collect: bool = True,
        days: int = 7,
        platform: Optional[Platform] = None,
    ) -> PerformanceTrackerResult:
        """Executa o Performance Tracker completo.

        Args:
            collect: Se deve coletar novas metricas
            days: Periodo em dias
            platform: Plataforma especifica

        Returns:
            PerformanceTrackerResult
        """
        start_time = datetime.now()
        metrics_collected = 0
        reports_generated = 0
        insights_found = 0

        # Coleta metricas
        if collect:
            print("[PerformanceTracker] Coletando metricas...")
            metrics_collected = self.collect_metrics(platform, days)
            print(f"[PerformanceTracker] Coletadas {metrics_collected} metricas")

        # Gera relatorio
        print("[PerformanceTracker] Gerando relatorio...")
        report = self.generate_report(days, platform)
        reports_generated = 1
        insights_found = len(report.insights)

        return PerformanceTrackerResult(
            run_id=self.run_id,
            metrics_collected=metrics_collected,
            reports_generated=reports_generated,
            insights_found=insights_found,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            report=report,
        )


# Factory function
def get_performance_tracker() -> PerformanceTrackerAgent:
    """Retorna instancia do PerformanceTrackerAgent."""
    return PerformanceTrackerAgent()
