"""Tasks de analise do ViralForge."""

from typing import Optional

from src.agents import get_analyst_agent, strategist_agent
from src.tasks.celery_app import celery_app
from src.tools import budget_tools


@celery_app.task(bind=True, max_retries=2)
def analyze_video(self, video_id: int, force: bool = False, provider: Optional[str] = None):
    """Analisa um video especifico.

    Args:
        video_id: ID do video
        force: Se True, reanalisa mesmo se ja analisado
        provider: Provider de analise (gemini ou claude)
    """
    try:
        agent = get_analyst_agent(provider=provider)
        result = agent.analyze(video_id, force=force)
        return {
            "run_id": result.run_id,
            "video_id": result.video_id,
            "virality_score": result.virality_score,
            "replicability_score": result.replicability_score,
            "is_valid": result.is_valid,
            "cost_usd": result.cost_usd,
            "provider": agent.provider,
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


@celery_app.task
def analyze_pending_videos(limit: int = 10, provider: Optional[str] = None):
    """Analisa videos pendentes.

    Args:
        limit: Maximo de videos a analisar
        provider: Provider de analise (gemini ou claude)
    """
    # Verifica budget
    status = budget_tools.get_daily_status()
    if status["budget"]["exceeded"]:
        return {"status": "skipped", "reason": "budget_exceeded"}

    agent = get_analyst_agent(provider=provider)
    results = agent.analyze_pending(limit=limit)

    return {
        "status": "completed",
        "videos_analyzed": len(results),
        "valid_analyses": sum(1 for r in results if r.is_valid),
        "total_cost_usd": sum(r.cost_usd for r in results),
        "provider": agent.provider,
    }


@celery_app.task(bind=True, max_retries=2)
def generate_strategy(self, video_id: int, niche: str = None):
    """Gera estrategia para um video especifico.

    Args:
        video_id: ID do video de referencia
        niche: Nicho alvo
    """
    try:
        result = strategist_agent.generate(video_id, niche=niche)
        return {
            "run_id": result.run_id,
            "strategy_id": result.strategy_id,
            "title": result.title,
            "num_scenes": result.num_scenes,
            "estimated_cost_usd": result.estimated_cost_usd,
            "is_valid": result.is_valid,
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task
def generate_strategies(niche: str = "geral", limit: int = 3):
    """Gera estrategias a partir dos melhores videos.

    Args:
        niche: Nicho para filtrar
        limit: Numero de estrategias
    """
    # Verifica budget
    status = budget_tools.get_daily_status()
    if status["budget"]["exceeded"]:
        return {"status": "skipped", "reason": "budget_exceeded"}

    results = strategist_agent.generate_from_best_videos(niche=niche, limit=limit)

    return {
        "status": "completed",
        "strategies_generated": len(results),
        "titles": [r.title for r in results],
        "total_cost_usd": sum(r.cost_usd for r in results),
    }
