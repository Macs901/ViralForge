"""Configuracao do Celery para ViralForge."""

from celery import Celery
from celery.schedules import crontab

from config.settings import get_settings

settings = get_settings()

# Cria app Celery
celery_app = Celery(
    "viralforge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.tasks.scraping_tasks",
        "src.tasks.processing_tasks",
        "src.tasks.analysis_tasks",
        "src.tasks.production_tasks",
    ],
)

# Configuracoes
celery_app.conf.update(
    # Timezone
    timezone=settings.timezone,
    enable_utc=True,

    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600 * 24,  # 24 horas

    # Worker settings
    worker_concurrency=settings.celery_concurrency,
    worker_prefetch_multiplier=1,  # Para tasks longas como Whisper

    # Task routing
    task_routes={
        "src.tasks.scraping_tasks.*": {"queue": "scraping"},
        "src.tasks.processing_tasks.*": {"queue": "processing"},
        "src.tasks.analysis_tasks.*": {"queue": "analysis"},
        "src.tasks.production_tasks.*": {"queue": "production"},
    },

    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Beat schedule (tarefas agendadas)
    beat_schedule={
        # Scraping a cada 4 horas
        "scrape-all-profiles": {
            "task": "src.tasks.scraping_tasks.scrape_all_profiles",
            "schedule": crontab(minute=0, hour="*/4"),
            "options": {"queue": "scraping"},
        },
        # Processamento a cada hora
        "process-pending-videos": {
            "task": "src.tasks.processing_tasks.process_pending_videos",
            "schedule": crontab(minute=30),
            "options": {"queue": "processing"},
        },
        # Analise a cada 2 horas
        "analyze-pending-videos": {
            "task": "src.tasks.analysis_tasks.analyze_pending_videos",
            "schedule": crontab(minute=0, hour="*/2"),
            "options": {"queue": "analysis"},
        },
        # Geracao de estrategias diaria
        "generate-daily-strategies": {
            "task": "src.tasks.analysis_tasks.generate_strategies",
            "schedule": crontab(minute=0, hour=10),  # 10h da manha
            "options": {"queue": "analysis"},
        },
        # Reset de contadores a meia-noite
        "reset-daily-counters": {
            "task": "src.tasks.processing_tasks.reset_daily_counters",
            "schedule": crontab(minute=0, hour=0),
        },
    },
)


if __name__ == "__main__":
    celery_app.start()
