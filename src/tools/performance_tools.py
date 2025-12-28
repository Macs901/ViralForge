"""Performance Tracking MCP Tools - Ferramentas para analytics e relatorios."""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.agents.performance_tracker_agent import get_performance_tracker
from src.db.models.trends import Platform

# MCP Server para Performance Tools
performance_mcp = FastMCP("performance-tools")


@performance_mcp.tool()
def collect_performance_metrics(
    platform: Optional[str] = None,
    days: int = 7,
) -> dict:
    """Coleta metricas de posts publicados.

    Busca dados de views, likes, comentarios, etc. dos posts publicados.

    Args:
        platform: Plataforma (instagram, tiktok, youtube) ou None para todas
        days: Ultimos N dias para coletar

    Returns:
        Resultado da coleta
    """
    tracker = get_performance_tracker()

    plat = Platform(platform) if platform else None
    collected = tracker.collect_metrics(plat, days)

    return {
        "success": True,
        "metrics_collected": collected,
        "platform": platform or "all",
        "days": days,
    }


@performance_mcp.tool()
def generate_performance_report(
    days: int = 7,
    platform: Optional[str] = None,
) -> dict:
    """Gera relatorio de performance de conteudo.

    Analisa metricas e gera insights acionaveis.

    Args:
        days: Periodo em dias
        platform: Plataforma especifica ou None para todas

    Returns:
        Relatorio completo com insights
    """
    tracker = get_performance_tracker()

    plat = Platform(platform) if platform else None
    report = tracker.generate_report(days, plat)

    # Converte para dict serializavel
    return {
        "period": {
            "start": report.period_start.isoformat(),
            "end": report.period_end.isoformat(),
        },
        "summary": {
            "total_posts": report.total_posts,
            "total_views": report.total_views,
            "total_engagement": report.total_engagement,
            "avg_engagement_rate": round(report.avg_engagement_rate, 4),
        },
        "best_performing": [
            {
                "content_id": p.content_id,
                "title": p.title,
                "platform": p.platform,
                "views": p.views,
                "engagement_rate": round(p.engagement_rate, 4),
                "tier": p.performance_tier,
            }
            for p in report.best_performing
        ],
        "worst_performing": [
            {
                "content_id": p.content_id,
                "title": p.title,
                "platform": p.platform,
                "views": p.views,
                "engagement_rate": round(p.engagement_rate, 4),
                "tier": p.performance_tier,
            }
            for p in report.worst_performing
        ],
        "insights": [
            {
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "impact": i.impact,
                "action": i.action,
            }
            for i in report.insights
        ],
        "trends": report.trends,
    }


@performance_mcp.tool()
def get_best_posting_times(
    platform: Optional[str] = None,
    days: int = 30,
) -> dict:
    """Analisa melhores horarios para postar.

    Baseado no historico de performance, identifica horarios
    e dias da semana com melhor engajamento.

    Args:
        platform: Plataforma especifica ou None para todas
        days: Periodo de analise em dias

    Returns:
        Melhores horarios e dias para postar
    """
    tracker = get_performance_tracker()

    plat = Platform(platform) if platform else None
    return tracker.get_best_posting_times(plat, days)


@performance_mcp.tool()
def run_performance_analysis(
    collect: bool = True,
    days: int = 7,
    platform: Optional[str] = None,
) -> dict:
    """Executa analise completa de performance.

    Coleta metricas (opcional), gera relatorio e insights.

    Args:
        collect: Se deve coletar novas metricas antes
        days: Periodo em dias
        platform: Plataforma especifica ou None para todas

    Returns:
        Resultado completo da analise
    """
    tracker = get_performance_tracker()

    plat = Platform(platform) if platform else None
    result = tracker.run(collect, days, plat)

    report_dict = None
    if result.report:
        report_dict = {
            "period": {
                "start": result.report.period_start.isoformat(),
                "end": result.report.period_end.isoformat(),
            },
            "summary": {
                "total_posts": result.report.total_posts,
                "total_views": result.report.total_views,
                "total_engagement": result.report.total_engagement,
                "avg_engagement_rate": round(result.report.avg_engagement_rate, 4),
            },
            "insights_count": len(result.report.insights),
            "best_posts_count": len(result.report.best_performing),
        }

    return {
        "success": True,
        "run_id": result.run_id,
        "metrics_collected": result.metrics_collected,
        "reports_generated": result.reports_generated,
        "insights_found": result.insights_found,
        "duration_seconds": round(result.duration_seconds, 2),
        "report_summary": report_dict,
    }


@performance_mcp.tool()
def get_content_performance(
    content_id: int,
) -> dict:
    """Obtem performance detalhada de um conteudo especifico.

    Args:
        content_id: ID do conteudo na content_queue

    Returns:
        Metricas detalhadas do conteudo
    """
    from sqlalchemy import select
    from src.core.database import get_sync_db
    from src.db.models.trends import ContentQueue, PerformanceMetric

    db = get_sync_db()
    try:
        # Busca o conteudo
        content = db.execute(
            select(ContentQueue).where(ContentQueue.id == content_id)
        ).scalar_one_or_none()

        if not content:
            return {"error": f"Conteudo {content_id} nao encontrado"}

        # Busca metricas
        metrics = list(db.execute(
            select(PerformanceMetric).where(
                PerformanceMetric.content_id == content_id
            ).order_by(PerformanceMetric.measured_at.desc())
        ).scalars().all())

        return {
            "content_id": content.id,
            "title": content.title,
            "status": content.status.value,
            "published_at": content.published_at.isoformat() if content.published_at else None,
            "published_urls": content.published_urls,
            "metrics": [
                {
                    "platform": m.platform.value,
                    "views": m.views,
                    "likes": m.likes,
                    "comments": m.comments,
                    "shares": m.shares,
                    "saves": m.saves,
                    "engagement_rate": float(m.engagement_rate or 0),
                    "measured_at": m.measured_at.isoformat() if m.measured_at else None,
                }
                for m in metrics
            ],
            "total_metrics": len(metrics),
        }

    finally:
        db.close()


@performance_mcp.tool()
def compare_content_performance(
    content_ids: list[int],
) -> dict:
    """Compara performance entre multiplos conteudos.

    Args:
        content_ids: Lista de IDs de conteudo para comparar

    Returns:
        Comparacao lado a lado
    """
    from sqlalchemy import select
    from src.core.database import get_sync_db
    from src.db.models.trends import PerformanceMetric

    db = get_sync_db()
    try:
        results = []

        for content_id in content_ids:
            # Busca ultima metrica
            metric = db.execute(
                select(PerformanceMetric).where(
                    PerformanceMetric.content_id == content_id
                ).order_by(PerformanceMetric.measured_at.desc())
            ).scalar_one_or_none()

            if metric:
                total_engagement = metric.likes + metric.comments + metric.shares + metric.saves
                results.append({
                    "content_id": content_id,
                    "platform": metric.platform.value,
                    "views": metric.views,
                    "engagement": total_engagement,
                    "engagement_rate": float(metric.engagement_rate or 0),
                })
            else:
                results.append({
                    "content_id": content_id,
                    "error": "No metrics found",
                })

        # Ranking
        valid_results = [r for r in results if "error" not in r]
        if valid_results:
            by_views = sorted(valid_results, key=lambda x: x["views"], reverse=True)
            by_engagement = sorted(valid_results, key=lambda x: x["engagement_rate"], reverse=True)

            return {
                "comparison": results,
                "ranking": {
                    "by_views": [r["content_id"] for r in by_views],
                    "by_engagement_rate": [r["content_id"] for r in by_engagement],
                },
                "winner_by_views": by_views[0]["content_id"] if by_views else None,
                "winner_by_engagement": by_engagement[0]["content_id"] if by_engagement else None,
            }

        return {"comparison": results, "ranking": {}}

    finally:
        db.close()


# Export
__all__ = ["performance_mcp"]
