"""Rotas de Productions do ViralForge."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.db.models import ProducedVideo, ProductionStatus

router = APIRouter()


@router.get("/")
async def list_productions(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Lista videos produzidos."""
    stmt = select(ProducedVideo)

    if status:
        stmt = stmt.where(ProducedVideo.status == status)

    stmt = stmt.order_by(ProducedVideo.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    productions = result.scalars().all()

    return [
        {
            "id": p.id,
            "strategy_id": p.strategy_id,
            "status": p.status,
            "tts_provider": p.tts_provider,
            "final_duration": p.final_duration_seconds,
            "total_cost": float(p.total_production_cost_usd) if p.total_production_cost_usd else None,
            "is_published": p.is_published,
            "created_at": p.created_at.isoformat(),
        }
        for p in productions
    ]


@router.get("/completed")
async def list_completed_productions(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lista producoes concluidas."""
    stmt = (
        select(ProducedVideo)
        .where(ProducedVideo.status == ProductionStatus.COMPLETED.value)
        .order_by(ProducedVideo.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    productions = result.scalars().all()

    return [
        {
            "id": p.id,
            "strategy_id": p.strategy_id,
            "final_video_path": p.final_video_path,
            "final_duration": p.final_duration_seconds,
            "final_resolution": p.final_resolution,
            "total_cost": float(p.total_production_cost_usd) if p.total_production_cost_usd else None,
            "is_published": p.is_published,
        }
        for p in productions
    ]


@router.get("/{production_id}")
async def get_production(production_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna detalhes de uma producao."""
    production = await db.get(ProducedVideo, production_id)
    if not production:
        raise HTTPException(status_code=404, detail="Producao nao encontrada")

    return {
        "id": production.id,
        "strategy_id": production.strategy_id,
        "batch_id": production.production_batch_id,
        "status": production.status,
        "tts_provider": production.tts_provider,
        "tts_file_path": production.tts_file_path,
        "narration_duration": float(production.narration_duration_seconds) if production.narration_duration_seconds else None,
        "clips_paths": production.clips_paths,
        "final_video_path": production.final_video_path,
        "final_duration": production.final_duration_seconds,
        "final_resolution": production.final_resolution,
        "final_file_size_mb": float(production.final_file_size_mb) if production.final_file_size_mb else None,
        "music_track": production.music_track_used,
        "costs": {
            "tts": float(production.tts_cost_usd) if production.tts_cost_usd else 0,
            "veo": float(production.veo_cost_usd) if production.veo_cost_usd else 0,
            "total": float(production.total_production_cost_usd) if production.total_production_cost_usd else 0,
        },
        "is_published": production.is_published,
        "published_url": production.published_url,
        "error": production.error_message,
        "created_at": production.created_at.isoformat(),
    }


@router.get("/{production_id}/download")
async def get_download_url(production_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna URL pre-assinada para download do video."""
    from src.tools import storage_tools

    production = await db.get(ProducedVideo, production_id)
    if not production:
        raise HTTPException(status_code=404, detail="Producao nao encontrada")

    if not production.final_video_path:
        raise HTTPException(status_code=400, detail="Video ainda nao disponivel")

    # Gera URL pre-assinada (valida por 24h)
    download_url = storage_tools.get_file_url(
        production.final_video_path.replace(f"{storage_tools.bucket}/", ""),
        expires_hours=24,
    )

    return {"download_url": download_url, "expires_in_hours": 24}


@router.post("/{production_id}/publish")
async def mark_as_published(
    production_id: int,
    platform: str,
    url: str,
    db: AsyncSession = Depends(get_db),
):
    """Marca producao como publicada."""
    from datetime import datetime

    production = await db.get(ProducedVideo, production_id)
    if not production:
        raise HTTPException(status_code=404, detail="Producao nao encontrada")

    production.is_published = True
    production.published_platform = platform
    production.published_url = url
    production.published_at = datetime.now()

    await db.commit()

    return {"id": production.id, "published": True, "url": url}
