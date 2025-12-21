"""Tasks de producao do ViralForge."""

import asyncio

from src.agents import producer_agent
from src.tasks.celery_app import celery_app
from src.tools import budget_tools


@celery_app.task(bind=True, max_retries=1)
def produce_video(
    self,
    strategy_id: int,
    mode: str = None,
    music_track: str = None,
):
    """Produz video a partir de uma estrategia.

    Args:
        strategy_id: ID da estrategia
        mode: Modo Veo (test/production)
        music_track: Nome do arquivo de musica
    """
    try:
        result = producer_agent.produce_sync(
            strategy_id=strategy_id,
            mode=mode,
            music_track=music_track,
        )
        return {
            "run_id": result.run_id,
            "production_id": result.production_id,
            "strategy_id": result.strategy_id,
            "final_video_path": result.final_video_path,
            "duration_seconds": result.duration_seconds,
            "total_cost_usd": result.total_cost_usd,
            "production_time_seconds": result.production_time_seconds,
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=300)  # 5 min retry


@celery_app.task
def produce_next_approved(mode: str = None):
    """Produz proxima estrategia aprovada.

    Args:
        mode: Modo Veo
    """
    # Verifica budget
    status = budget_tools.get_daily_status()
    if status["budget"]["exceeded"]:
        return {"status": "skipped", "reason": "budget_exceeded"}

    result = producer_agent.produce_next_approved(mode=mode)

    if result is None:
        return {"status": "no_approved_strategies"}

    return {
        "status": "completed",
        "production_id": result.production_id,
        "strategy_id": result.strategy_id,
        "total_cost_usd": result.total_cost_usd,
    }


@celery_app.task
def approve_strategy(strategy_id: int):
    """Aprova estrategia para producao.

    Args:
        strategy_id: ID da estrategia
    """
    strategy = producer_agent.approve_strategy(strategy_id)
    return {
        "strategy_id": strategy.id,
        "title": strategy.title,
        "status": strategy.status,
    }


@celery_app.task
def produce_all_approved(mode: str = None, limit: int = 3):
    """Produz todas as estrategias aprovadas.

    Args:
        mode: Modo Veo
        limit: Maximo de videos a produzir
    """
    from sqlalchemy import select
    from src.core.database import get_sync_db
    from src.db.models import GeneratedStrategy, StrategyStatus

    db = get_sync_db()
    try:
        stmt = (
            select(GeneratedStrategy)
            .where(GeneratedStrategy.status == StrategyStatus.APPROVED.value)
            .order_by(GeneratedStrategy.created_at)
            .limit(limit)
        )
        strategies = db.execute(stmt).scalars().all()

        results = []
        for strategy in strategies:
            # Verifica budget antes de cada producao
            status = budget_tools.get_daily_status()
            if status["budget"]["exceeded"]:
                break

            try:
                result = producer_agent.produce_sync(strategy.id, mode=mode)
                results.append({
                    "production_id": result.production_id,
                    "strategy_id": result.strategy_id,
                    "cost_usd": result.total_cost_usd,
                })
            except Exception as e:
                results.append({
                    "strategy_id": strategy.id,
                    "error": str(e),
                })

        return {
            "status": "completed",
            "produced": len([r for r in results if "production_id" in r]),
            "failed": len([r for r in results if "error" in r]),
            "results": results,
        }
    finally:
        db.close()
