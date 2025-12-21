"""Tasks de processamento do ViralForge."""

import tempfile
from datetime import date
from pathlib import Path

from sqlalchemy import select

from src.core.database import get_sync_db
from src.db.models import DailyCounter, ViralVideo
from src.tasks.celery_app import celery_app
from src.tools import scraping_tools, storage_tools, whisper_tools


@celery_app.task(bind=True, max_retries=3)
def download_video(self, video_id: int):
    """Download de video do Instagram.

    Args:
        video_id: ID do video no banco
    """
    db = get_sync_db()
    try:
        video = db.get(ViralVideo, video_id)
        if not video:
            raise ValueError(f"Video {video_id} nao encontrado")

        if video.is_downloaded:
            return {"status": "already_downloaded", "video_id": video_id}

        # Cria diretorio temporario
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = Path(tmp_dir) / f"{video.platform_id}.mp4"

            # Download
            # Precisamos da URL do video - vamos buscar via shortcode
            video_url = video.source_url
            success = scraping_tools.download_video(video_url, str(local_path))

            if not success:
                raise RuntimeError("Falha no download do video")

            # Upload para MinIO
            remote_path = storage_tools.upload_video(local_path, video.id)

            # Atualiza video
            video.video_file_path = remote_path
            video.is_downloaded = True
            db.commit()

        return {
            "status": "downloaded",
            "video_id": video_id,
            "path": remote_path,
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def transcribe_video(self, video_id: int):
    """Transcreve video usando Whisper.

    Args:
        video_id: ID do video no banco
    """
    db = get_sync_db()
    try:
        video = db.get(ViralVideo, video_id)
        if not video:
            raise ValueError(f"Video {video_id} nao encontrado")

        if video.is_transcribed:
            return {"status": "already_transcribed", "video_id": video_id}

        if not video.video_file_path:
            raise ValueError("Video sem arquivo para transcrever")

        # Download do MinIO
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = Path(tmp_dir) / "video.mp4"
            storage_tools.download_file(video.video_file_path, local_path)

            # Transcreve
            result = whisper_tools.transcribe_video(local_path)

            # Atualiza video
            video.transcription = result.text
            video.transcription_language = result.language
            video.transcription_confidence = result.confidence
            video.is_transcribed = True
            db.commit()

        return {
            "status": "transcribed",
            "video_id": video_id,
            "language": result.language,
            "duration": result.duration_seconds,
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=120 * (self.request.retries + 1))
    finally:
        db.close()


@celery_app.task
def process_pending_videos(limit: int = 10):
    """Processa videos pendentes (download + transcricao).

    Args:
        limit: Maximo de videos a processar
    """
    db = get_sync_db()
    try:
        # Videos que passaram no pre-filtro mas nao foram baixados
        stmt = (
            select(ViralVideo)
            .where(
                ViralVideo.passes_prefilter == True,
                ViralVideo.is_downloaded == False,
            )
            .order_by(ViralVideo.statistical_viral_score.desc())
            .limit(limit)
        )
        videos = db.execute(stmt).scalars().all()

        downloaded = 0
        transcribed = 0

        for video in videos:
            try:
                # Download
                download_video.delay(video.id)
                downloaded += 1
            except Exception as e:
                print(f"Erro ao agendar download de {video.id}: {e}")

        # Videos baixados mas nao transcritos
        stmt = (
            select(ViralVideo)
            .where(
                ViralVideo.is_downloaded == True,
                ViralVideo.is_transcribed == False,
            )
            .order_by(ViralVideo.statistical_viral_score.desc())
            .limit(limit)
        )
        videos = db.execute(stmt).scalars().all()

        for video in videos:
            try:
                transcribe_video.delay(video.id)
                transcribed += 1
            except Exception as e:
                print(f"Erro ao agendar transcricao de {video.id}: {e}")

        return {
            "downloads_scheduled": downloaded,
            "transcriptions_scheduled": transcribed,
        }
    finally:
        db.close()


@celery_app.task
def reset_daily_counters():
    """Reseta contadores diarios (executado a meia-noite)."""
    db = get_sync_db()
    try:
        today = date.today()

        # Verifica se ja existe contador para hoje
        stmt = select(DailyCounter).where(DailyCounter.date == today)
        existing = db.execute(stmt).scalar_one_or_none()

        if not existing:
            counter = DailyCounter(date=today)
            db.add(counter)
            db.commit()
            return {"status": "created", "date": str(today)}

        return {"status": "exists", "date": str(today)}
    finally:
        db.close()
