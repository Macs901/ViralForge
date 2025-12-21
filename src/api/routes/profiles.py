"""Rotas de Profiles do ViralForge."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.db.models import MonitoredProfile

router = APIRouter()


class ProfileCreate(BaseModel):
    """Schema para criacao de perfil."""

    username: str
    niche: str
    priority: int = 1
    niche_avg_views: int = 50000
    niche_avg_likes: int = 5000
    niche_avg_comments: int = 500


class ProfileUpdate(BaseModel):
    """Schema para atualizacao de perfil."""

    niche: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_profiles(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os perfis."""
    stmt = select(MonitoredProfile)
    if active_only:
        stmt = stmt.where(MonitoredProfile.is_active == True)
    stmt = stmt.order_by(MonitoredProfile.priority.desc())

    result = await db.execute(stmt)
    profiles = result.scalars().all()

    return [
        {
            "id": p.id,
            "username": p.username,
            "niche": p.niche,
            "priority": p.priority,
            "is_active": p.is_active,
            "total_videos": p.total_videos_collected,
            "last_scraped_at": p.last_scraped_at.isoformat() if p.last_scraped_at else None,
        }
        for p in profiles
    ]


@router.get("/{profile_id}")
async def get_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna detalhes de um perfil."""
    profile = await db.get(MonitoredProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    return {
        "id": profile.id,
        "username": profile.username,
        "platform": profile.platform,
        "niche": profile.niche,
        "priority": profile.priority,
        "is_active": profile.is_active,
        "niche_avg_views": profile.niche_avg_views,
        "niche_avg_likes": profile.niche_avg_likes,
        "niche_avg_comments": profile.niche_avg_comments,
        "total_videos": profile.total_videos_collected,
        "last_scraped_at": profile.last_scraped_at.isoformat() if profile.last_scraped_at else None,
        "created_at": profile.created_at.isoformat(),
    }


@router.post("/")
async def create_profile(data: ProfileCreate, db: AsyncSession = Depends(get_db)):
    """Cria novo perfil."""
    # Verifica se ja existe
    stmt = select(MonitoredProfile).where(
        MonitoredProfile.username == data.username.lower().replace("@", "")
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Perfil ja existe")

    profile = MonitoredProfile(
        username=data.username.lower().replace("@", ""),
        niche=data.niche,
        priority=data.priority,
        niche_avg_views=data.niche_avg_views,
        niche_avg_likes=data.niche_avg_likes,
        niche_avg_comments=data.niche_avg_comments,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return {"id": profile.id, "username": profile.username}


@router.patch("/{profile_id}")
async def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza perfil."""
    profile = await db.get(MonitoredProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    if data.niche is not None:
        profile.niche = data.niche
    if data.priority is not None:
        profile.priority = data.priority
    if data.is_active is not None:
        profile.is_active = data.is_active

    await db.commit()
    return {"id": profile.id, "updated": True}


@router.delete("/{profile_id}")
async def delete_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Remove perfil."""
    profile = await db.get(MonitoredProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil nao encontrado")

    await db.delete(profile)
    await db.commit()
    return {"id": profile_id, "deleted": True}


@router.post("/{profile_id}/scrape")
async def trigger_scrape(profile_id: int, max_videos: int = 50):
    """Dispara scraping para um perfil."""
    from src.tasks.scraping_tasks import scrape_profile

    task = scrape_profile.delay(profile_id=profile_id, max_videos=max_videos)
    return {"task_id": task.id, "status": "queued"}
