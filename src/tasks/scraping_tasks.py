"""Tasks de scraping do ViralForge."""

from src.agents import watcher_agent
from src.tasks.celery_app import celery_app
from src.tools import budget_tools


@celery_app.task(bind=True, max_retries=3)
def scrape_profile(self, profile_id: int = None, username: str = None, max_videos: int = 50):
    """Scrape de um perfil especifico.

    Args:
        profile_id: ID do perfil
        username: Username (alternativa ao profile_id)
        max_videos: Maximo de videos a coletar
    """
    try:
        result = watcher_agent.run(
            profile_id=profile_id,
            username=username,
            max_videos=max_videos,
        )
        return {
            "run_id": result.run_id,
            "profile": result.profile_username,
            "collected": result.videos_collected,
            "prefiltered": result.videos_prefiltered,
            "cost_usd": result.cost_usd,
            "errors": result.errors,
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True)
def scrape_all_profiles(self, max_videos_per_profile: int = 30):
    """Scrape de todos os perfis ativos.

    Args:
        max_videos_per_profile: Maximo de videos por perfil
    """
    # Verifica budget antes de iniciar
    status = budget_tools.get_daily_status()
    if status["budget"]["exceeded"]:
        return {"status": "skipped", "reason": "budget_exceeded"}

    results = watcher_agent.run_all_active_profiles(max_videos_per_profile)

    return {
        "status": "completed",
        "profiles_scraped": len(results),
        "total_collected": sum(r.videos_collected for r in results),
        "total_prefiltered": sum(r.videos_prefiltered for r in results),
        "total_cost_usd": sum(r.cost_usd for r in results),
    }


@celery_app.task
def add_profile(
    username: str,
    niche: str,
    priority: int = 1,
    niche_avg_views: int = 50000,
    niche_avg_likes: int = 5000,
    niche_avg_comments: int = 500,
):
    """Adiciona novo perfil para monitoramento.

    Args:
        username: Username do Instagram
        niche: Categoria/nicho
        priority: Prioridade (1-5)
        niche_avg_views: Media de views do nicho
        niche_avg_likes: Media de likes do nicho
        niche_avg_comments: Media de comentarios do nicho
    """
    profile = watcher_agent.add_profile(
        username=username,
        niche=niche,
        priority=priority,
        niche_avg_views=niche_avg_views,
        niche_avg_likes=niche_avg_likes,
        niche_avg_comments=niche_avg_comments,
    )
    return {
        "id": profile.id,
        "username": profile.username,
        "niche": profile.niche,
    }
