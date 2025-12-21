"""Rotas de Strategies do ViralForge."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.db.models import GeneratedStrategy, StrategyStatus

router = APIRouter()


class StrategyUpdate(BaseModel):
    """Schema para atualizacao de estrategia."""

    title: Optional[str] = None
    status: Optional[str] = None


@router.get("/")
async def list_strategies(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Lista estrategias geradas."""
    stmt = select(GeneratedStrategy)

    if status:
        stmt = stmt.where(GeneratedStrategy.status == status)

    stmt = stmt.order_by(GeneratedStrategy.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    strategies = result.scalars().all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "target_niche": s.target_niche,
            "status": s.status,
            "scene_count": s.scene_count,
            "estimated_cost": float(s.estimated_production_cost_usd) if s.estimated_production_cost_usd else None,
            "created_at": s.created_at.isoformat(),
        }
        for s in strategies
    ]


@router.get("/draft")
async def list_draft_strategies(db: AsyncSession = Depends(get_db)):
    """Lista estrategias em rascunho."""
    stmt = (
        select(GeneratedStrategy)
        .where(GeneratedStrategy.status == StrategyStatus.DRAFT.value)
        .order_by(GeneratedStrategy.created_at.desc())
    )

    result = await db.execute(stmt)
    strategies = result.scalars().all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "scene_count": s.scene_count,
            "estimated_cost": float(s.estimated_production_cost_usd) if s.estimated_production_cost_usd else None,
        }
        for s in strategies
    ]


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna detalhes de uma estrategia."""
    strategy = await db.get(GeneratedStrategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia nao encontrada")

    return {
        "id": strategy.id,
        "source_video_id": strategy.source_video_id,
        "title": strategy.title,
        "concept": strategy.concept,
        "target_niche": strategy.target_niche,
        "status": strategy.status,
        "hook_script": strategy.hook_script,
        "development_script": strategy.development_script,
        "cta_script": strategy.cta_script,
        "full_script": strategy.full_script,
        "veo_prompts": strategy.veo_prompts,
        "tts_config": strategy.tts_config,
        "music_track": strategy.music_track,
        "suggested_hashtags": strategy.suggested_hashtags,
        "suggested_caption": strategy.suggested_caption,
        "best_posting_time": strategy.best_posting_time,
        "scene_count": strategy.scene_count,
        "script_length": strategy.total_script_length,
        "estimated_cost": float(strategy.estimated_production_cost_usd) if strategy.estimated_production_cost_usd else None,
        "created_at": strategy.created_at.isoformat(),
    }


@router.patch("/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    data: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza estrategia."""
    strategy = await db.get(GeneratedStrategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia nao encontrada")

    if data.title is not None:
        strategy.title = data.title
    if data.status is not None:
        if data.status not in [s.value for s in StrategyStatus]:
            raise HTTPException(status_code=400, detail="Status invalido")
        strategy.status = data.status

    await db.commit()
    return {"id": strategy.id, "updated": True}


@router.post("/{strategy_id}/approve")
async def approve_strategy(strategy_id: int, db: AsyncSession = Depends(get_db)):
    """Aprova estrategia para producao."""
    strategy = await db.get(GeneratedStrategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia nao encontrada")

    strategy.status = StrategyStatus.APPROVED.value
    await db.commit()

    return {"id": strategy.id, "status": "approved"}


@router.post("/{strategy_id}/produce")
async def trigger_production(
    strategy_id: int,
    mode: str = "test",
    music_track: Optional[str] = None,
):
    """Dispara producao de video."""
    from src.tasks.production_tasks import produce_video

    task = produce_video.delay(
        strategy_id=strategy_id,
        mode=mode,
        music_track=music_track,
    )
    return {"task_id": task.id, "status": "queued"}


@router.post("/generate")
async def trigger_generation(video_id: int, niche: Optional[str] = None):
    """Dispara geracao de estrategia para um video."""
    from src.tasks.analysis_tasks import generate_strategy

    task = generate_strategy.delay(video_id=video_id, niche=niche)
    return {"task_id": task.id, "status": "queued"}
