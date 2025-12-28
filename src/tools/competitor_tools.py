"""Competitor Intel MCP Tools - Ferramentas para analise de concorrentes."""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.agents.competitor_intel_agent import get_competitor_intel
from src.db.models.trends import Platform

# MCP Server para Competitor Tools
competitor_mcp = FastMCP("competitor-tools")


@competitor_mcp.tool()
def add_competitor(
    username: str,
    platform: str,
    niche: Optional[str] = None,
    tier: str = "similar",
    notes: Optional[str] = None,
) -> dict:
    """Adiciona um novo concorrente para monitorar.

    Args:
        username: Username do concorrente
        platform: Plataforma (instagram, tiktok, youtube)
        niche: Nicho do concorrente (opcional)
        tier: Tier - bigger (maior), similar, smaller (menor)
        notes: Notas adicionais

    Returns:
        Resultado com ID do concorrente
    """
    intel = get_competitor_intel()

    try:
        plat = Platform(platform)
    except ValueError:
        return {"error": f"Plataforma invalida: {platform}"}

    competitor_id = intel.add_competitor(username, plat, niche, tier, notes)

    return {
        "success": True,
        "competitor_id": competitor_id,
        "username": username,
        "platform": platform,
        "tier": tier,
    }


@competitor_mcp.tool()
def analyze_competitor(
    username: str,
    platform: str,
    max_posts: int = 30,
) -> dict:
    """Analisa um concorrente especifico.

    Coleta dados de posts, engagement, hashtags, etc.

    Args:
        username: Username do concorrente
        platform: Plataforma (instagram, tiktok, youtube)
        max_posts: Maximo de posts para analisar

    Returns:
        Snapshot completo do concorrente
    """
    intel = get_competitor_intel()

    try:
        plat = Platform(platform)
    except ValueError:
        return {"error": f"Plataforma invalida: {platform}"}

    snapshot = intel.analyze_competitor(username, plat, max_posts)

    if not snapshot:
        return {"error": f"Nao foi possivel analisar {username}"}

    return {
        "username": snapshot.username,
        "platform": snapshot.platform,
        "followers": snapshot.followers,
        "total_posts": snapshot.posts,
        "avg_views": round(snapshot.avg_views, 1),
        "avg_likes": round(snapshot.avg_likes, 1),
        "avg_engagement_rate": round(snapshot.avg_engagement_rate, 4),
        "posting_frequency": round(snapshot.posting_frequency, 2),
        "top_hashtags": snapshot.top_hashtags,
        "top_content_types": snapshot.top_content_types,
        "best_posting_times": snapshot.best_posting_times,
        "recent_top_posts": snapshot.recent_top_posts,
    }


@competitor_mcp.tool()
def run_competitor_intel(
    platform: Optional[str] = None,
    max_posts_per_competitor: int = 20,
) -> dict:
    """Executa analise completa de todos os concorrentes.

    Analisa todos os concorrentes monitorados e gera insights.

    Args:
        platform: Plataforma especifica ou None para todas
        max_posts_per_competitor: Maximo de posts por concorrente

    Returns:
        Resultado completo com snapshots, insights e benchmark
    """
    intel = get_competitor_intel()

    plat = Platform(platform) if platform else None
    result = intel.run_intel(plat, max_posts_per_competitor)

    return {
        "success": True,
        "run_id": result.run_id,
        "competitors_analyzed": result.competitors_analyzed,
        "insights_found": result.insights_found,
        "duration_seconds": round(result.duration_seconds, 2),
        "snapshots": [
            {
                "username": s.username,
                "platform": s.platform,
                "followers": s.followers,
                "avg_engagement": round(s.avg_engagement_rate, 4),
            }
            for s in result.snapshots
        ],
        "insights": [
            {
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "competitor": i.competitor_username,
                "action": i.action,
            }
            for i in result.insights
        ],
        "benchmark": {
            "competitor_avg_followers": result.benchmark.competitor_avg_followers,
            "competitor_avg_engagement": round(result.benchmark.competitor_avg_engagement, 4),
            "total_competitors": result.benchmark.total_competitors,
            "leader": result.benchmark.gap_to_leader,
            "recommendations": result.benchmark.recommendations,
        } if result.benchmark else None,
    }


@competitor_mcp.tool()
def list_competitors(
    platform: Optional[str] = None,
    active_only: bool = True,
) -> dict:
    """Lista todos os concorrentes monitorados.

    Args:
        platform: Filtrar por plataforma (opcional)
        active_only: Apenas concorrentes ativos

    Returns:
        Lista de concorrentes
    """
    intel = get_competitor_intel()

    plat = Platform(platform) if platform else None
    competitors = intel.get_competitors_list(plat, active_only)

    return {
        "count": len(competitors),
        "competitors": competitors,
    }


@competitor_mcp.tool()
def get_competitor_insights(
    username: str,
    platform: str,
) -> dict:
    """Gera insights especificos sobre um concorrente.

    Analisa o concorrente e retorna insights acionaveis.

    Args:
        username: Username do concorrente
        platform: Plataforma

    Returns:
        Insights sobre o concorrente
    """
    intel = get_competitor_intel()

    try:
        plat = Platform(platform)
    except ValueError:
        return {"error": f"Plataforma invalida: {platform}"}

    snapshot = intel.analyze_competitor(username, plat, 30)

    if not snapshot:
        return {"error": f"Nao foi possivel analisar {username}"}

    # Gera insights manualmente
    insights = []

    # Insight de engajamento
    if snapshot.avg_engagement_rate > 0.05:
        insights.append({
            "type": "engagement",
            "insight": f"Taxa de engajamento alta ({snapshot.avg_engagement_rate:.1%})",
            "action": "Estude os hooks e CTAs deste perfil",
        })
    elif snapshot.avg_engagement_rate < 0.02:
        insights.append({
            "type": "engagement",
            "insight": f"Engajamento baixo ({snapshot.avg_engagement_rate:.1%})",
            "action": "Foque em criar conteudo mais envolvente que este concorrente",
        })

    # Insight de frequencia
    if snapshot.posting_frequency > 1:
        insights.append({
            "type": "frequency",
            "insight": f"Alta frequencia ({snapshot.posting_frequency:.1f} posts/dia)",
            "action": "Considere aumentar sua frequencia de postagem",
        })

    # Insight de hashtags
    if snapshot.top_hashtags:
        insights.append({
            "type": "hashtags",
            "insight": f"Hashtags mais usadas: {', '.join(snapshot.top_hashtags[:5])}",
            "action": "Teste usar hashtags similares",
        })

    # Insight de melhor post
    if snapshot.recent_top_posts:
        top = snapshot.recent_top_posts[0]
        insights.append({
            "type": "content",
            "insight": f"Melhor post tem {top.get('likes', 0):,} likes",
            "action": "Analise o que fez este post ter bom desempenho",
            "data": top,
        })

    return {
        "username": username,
        "platform": platform,
        "snapshot_summary": {
            "followers": snapshot.followers,
            "avg_engagement": round(snapshot.avg_engagement_rate, 4),
            "posting_frequency": round(snapshot.posting_frequency, 2),
        },
        "insights": insights,
        "recommendations": [
            "Estude os top posts para entender o que funciona",
            "Teste horarios de postagem similares",
            "Use hashtags que eles usam como ponto de partida",
        ],
    }


@competitor_mcp.tool()
def compare_competitors(
    usernames: list[str],
    platform: str,
) -> dict:
    """Compara multiplos concorrentes lado a lado.

    Args:
        usernames: Lista de usernames para comparar
        platform: Plataforma

    Returns:
        Comparacao entre concorrentes
    """
    intel = get_competitor_intel()

    try:
        plat = Platform(platform)
    except ValueError:
        return {"error": f"Plataforma invalida: {platform}"}

    snapshots = []
    for username in usernames:
        snapshot = intel.analyze_competitor(username, plat, 20)
        if snapshot:
            snapshots.append(snapshot)

    if not snapshots:
        return {"error": "Nenhum concorrente analisado com sucesso"}

    # Rankings
    by_followers = sorted(snapshots, key=lambda x: x.followers, reverse=True)
    by_engagement = sorted(snapshots, key=lambda x: x.avg_engagement_rate, reverse=True)
    by_views = sorted(snapshots, key=lambda x: x.avg_views, reverse=True)

    return {
        "compared": len(snapshots),
        "comparison": [
            {
                "username": s.username,
                "followers": s.followers,
                "avg_views": round(s.avg_views, 1),
                "avg_likes": round(s.avg_likes, 1),
                "avg_engagement": round(s.avg_engagement_rate, 4),
            }
            for s in snapshots
        ],
        "rankings": {
            "by_followers": [s.username for s in by_followers],
            "by_engagement": [s.username for s in by_engagement],
            "by_views": [s.username for s in by_views],
        },
        "leader": {
            "by_followers": by_followers[0].username,
            "by_engagement": by_engagement[0].username,
            "by_views": by_views[0].username,
        },
    }


# Export
__all__ = ["competitor_mcp"]
