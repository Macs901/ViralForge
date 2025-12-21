"""Rotas de Videos do ViralForge."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.db.models import VideoAnalysis, ViralVideo

router = APIRouter()


@router.get("/")
async def list_videos(
    prefiltered_only: bool = False,
    analyzed_only: bool = False,
    min_score: Optional[float] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Lista videos coletados."""
    stmt = select(ViralVideo)

    if prefiltered_only:
        stmt = stmt.where(ViralVideo.passes_prefilter == True)
    if analyzed_only:
        stmt = stmt.where(ViralVideo.is_analyzed == True)
    if min_score is not None:
        stmt = stmt.where(ViralVideo.statistical_viral_score >= min_score)

    stmt = stmt.order_by(ViralVideo.statistical_viral_score.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    videos = result.scalars().all()

    return [
        {
            "id": v.id,
            "platform_id": v.platform_id,
            "shortcode": v.shortcode,
            "source_url": v.source_url,
            "views": v.views_count,
            "likes": v.likes_count,
            "comments": v.comments_count,
            "statistical_score": float(v.statistical_viral_score) if v.statistical_viral_score else None,
            "passes_prefilter": v.passes_prefilter,
            "is_downloaded": v.is_downloaded,
            "is_transcribed": v.is_transcribed,
            "is_analyzed": v.is_analyzed,
            "posted_at": v.posted_at.isoformat() if v.posted_at else None,
        }
        for v in videos
    ]


@router.get("/pending")
async def list_pending_videos(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lista videos pendentes de analise."""
    stmt = (
        select(ViralVideo)
        .where(
            ViralVideo.passes_prefilter == True,
            ViralVideo.is_analyzed == False,
        )
        .order_by(ViralVideo.statistical_viral_score.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    videos = result.scalars().all()

    return [
        {
            "id": v.id,
            "platform_id": v.platform_id,
            "statistical_score": float(v.statistical_viral_score) if v.statistical_viral_score else None,
            "is_downloaded": v.is_downloaded,
            "is_transcribed": v.is_transcribed,
        }
        for v in videos
    ]


@router.get("/top")
async def list_top_videos(
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Lista melhores videos analisados."""
    stmt = (
        select(ViralVideo)
        .join(VideoAnalysis)
        .where(
            ViralVideo.is_analyzed == True,
            VideoAnalysis.virality_score >= 0.7,
        )
        .order_by(VideoAnalysis.virality_score.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    videos = result.scalars().all()

    return [
        {
            "id": v.id,
            "platform_id": v.platform_id,
            "source_url": v.source_url,
            "views": v.views_count,
            "virality_score": float(v.analysis.virality_score) if v.analysis else None,
            "replicability_score": float(v.analysis.replicability_score) if v.analysis else None,
            "has_strategy": len(v.strategies) > 0,
        }
        for v in videos
    ]


@router.get("/{video_id}")
async def get_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna detalhes de um video."""
    video = await db.get(ViralVideo, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video nao encontrado")

    response = {
        "id": video.id,
        "platform_id": video.platform_id,
        "shortcode": video.shortcode,
        "source_url": video.source_url,
        "video_file_path": video.video_file_path,
        "views": video.views_count,
        "likes": video.likes_count,
        "comments": video.comments_count,
        "engagement_rate": float(video.engagement_rate) if video.engagement_rate else None,
        "caption": video.caption,
        "hashtags": video.hashtags,
        "duration_seconds": video.duration_seconds,
        "statistical_score": float(video.statistical_viral_score) if video.statistical_viral_score else None,
        "passes_prefilter": video.passes_prefilter,
        "is_downloaded": video.is_downloaded,
        "is_transcribed": video.is_transcribed,
        "is_analyzed": video.is_analyzed,
        "transcription": video.transcription,
        "posted_at": video.posted_at.isoformat() if video.posted_at else None,
        "scraped_at": video.scraped_at.isoformat() if video.scraped_at else None,
    }

    if video.analysis:
        response["analysis"] = {
            "virality_score": float(video.analysis.virality_score) if video.analysis.virality_score else None,
            "replicability_score": float(video.analysis.replicability_score) if video.analysis.replicability_score else None,
            "hook_analysis": video.analysis.hook_analysis,
            "viral_factors": video.analysis.viral_factors,
            "is_valid": video.analysis.is_valid_json,
        }

    return response


@router.post("/{video_id}/analyze")
async def trigger_analysis(video_id: int, force: bool = False):
    """Dispara analise de um video."""
    from src.tasks.analysis_tasks import analyze_video

    task = analyze_video.delay(video_id=video_id, force=force)
    return {"task_id": task.id, "status": "queued"}


@router.post("/{video_id}/process")
async def trigger_processing(video_id: int):
    """Dispara download e transcricao de um video."""
    from src.tasks.processing_tasks import download_video, transcribe_video

    download_task = download_video.delay(video_id=video_id)
    return {
        "download_task_id": download_task.id,
        "status": "queued",
    }
