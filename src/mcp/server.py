"""Model Context Protocol server exposing ViralForge tools."""

from __future__ import annotations

import base64
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import anyio
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from config.settings import get_settings
from src.agents import producer_agent, strategist_agent, watcher_agent
from src.agents.analyst_agent import get_analyst_agent
from src.core.database import get_sync_db
from src.db.models import (
    GeneratedStrategy,
    ProducedVideo,
    StrategyStatus,
    ViralVideo,
)
from src.tools import (
    budget_tools,
    scraping_tools,
    sheets_exporter,
    storage_tools,
    whisper_tools,
)
from src.tools.video_downloader import VideoDownloaderFactory

settings = get_settings()

# === Configuracao de rede do MCP (pode ser sobrescrita por envs) ===
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
MCP_MOUNT_PATH = os.getenv("MCP_MOUNT_PATH", "/")

mcp = FastMCP(
    name="viralforge",
    instructions=(
        "Expose ViralForge's scraping, analysis, strategy generation and production pipeline via MCP. "
        "Ensure environment variables (database + API keys for Apify, Gemini, OpenAI, Veo and TTS providers) "
        "are configured before starting this server."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    mount_path=MCP_MOUNT_PATH,
)


def _decimal_to_float(value: Any) -> Optional[float]:
    """Convert Decimal/str/None to float for JSON serialization."""
    return float(value) if value is not None else None


def _dt_to_iso(value: Optional[datetime]) -> Optional[str]:
    """Return ISO8601 string for datetimes."""
    return value.isoformat() if value else None


async def _run_in_thread(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run blocking call in a worker thread."""
    return await anyio.to_thread.run_sync(fn, *args, **kwargs)


def _video_to_dict(video: ViralVideo) -> dict[str, Any]:
    """Serialize ViralVideo ORM object to plain dict."""
    analysis = video.analysis
    return {
        "id": video.id,
        "profile_id": video.profile_id,
        "profile_username": video.profile.username if video.profile else None,
        "platform_id": video.platform_id,
        "shortcode": video.shortcode,
        "source_url": video.source_url,
        "metrics": {
            "views": video.views_count,
            "likes": video.likes_count,
            "comments": video.comments_count,
            "shares": video.shares_count,
            "saves": video.saves_count,
        },
        "prefilter": {
            "statistical_viral_score": _decimal_to_float(video.statistical_viral_score),
            "normalized_views": _decimal_to_float(video.normalized_views),
            "normalized_engagement": _decimal_to_float(video.normalized_engagement),
            "recency_score": _decimal_to_float(video.recency_score),
            "passes_prefilter": video.passes_prefilter,
        },
        "status": {
            "is_downloaded": video.is_downloaded,
            "is_transcribed": video.is_transcribed,
            "is_analyzed": video.is_analyzed,
            "processing_error": video.processing_error,
        },
        "caption": video.caption,
        "hashtags": video.hashtags or [],
        "mentions": video.mentions or [],
        "duration_seconds": video.duration_seconds,
        "posted_at": _dt_to_iso(video.posted_at),
        "file_paths": {
            "video": video.video_file_path,
            "thumbnail": video.thumbnail_path,
            "audio": video.audio_file_path,
        },
        "analysis": (
            {
                "id": analysis.id,
                "virality_score": _decimal_to_float(analysis.virality_score),
                "replicability_score": _decimal_to_float(analysis.replicability_score),
                "production_quality_score": _decimal_to_float(analysis.production_quality_score),
                "is_valid_json": analysis.is_valid_json,
                "validation_errors": analysis.validation_errors,
            }
            if analysis
            else None
        ),
        "strategies": [s.id for s in video.strategies] if video.strategies else [],
        "created_at": _dt_to_iso(video.created_at),
        "scraped_at": _dt_to_iso(video.scraped_at),
        "updated_at": _dt_to_iso(video.updated_at),
    }


def _strategy_to_dict(strategy: GeneratedStrategy) -> dict[str, Any]:
    """Serialize GeneratedStrategy ORM object to dict."""
    return {
        "id": strategy.id,
        "source_video_id": strategy.source_video_id,
        "title": strategy.title,
        "concept": strategy.concept,
        "target_niche": strategy.target_niche,
        "status": strategy.status,
        "scene_count": strategy.scene_count,
        "estimated_production_cost_usd": _decimal_to_float(strategy.estimated_production_cost_usd),
        "scripts": {
            "hook": strategy.hook_script,
            "development": strategy.development_script,
            "cta": strategy.cta_script,
        },
        "veo_prompts": strategy.veo_prompts or [],
        "tts_config": strategy.tts_config,
        "music": {
            "track": strategy.music_track,
            "volume": _decimal_to_float(strategy.music_volume),
        },
        "publishing": {
            "hashtags": strategy.suggested_hashtags or [],
            "caption": strategy.suggested_caption,
            "best_posting_time": strategy.best_posting_time,
            "suggested_music": strategy.suggested_music,
        },
        "model_used": strategy.model_used,
        "tokens_used": strategy.tokens_used,
        "productions": [p.id for p in strategy.productions] if strategy.productions else [],
        "created_at": _dt_to_iso(strategy.created_at),
        "updated_at": _dt_to_iso(strategy.updated_at),
    }


def _production_to_dict(production: ProducedVideo) -> dict[str, Any]:
    """Serialize ProducedVideo ORM object to dict."""
    return {
        "id": production.id,
        "strategy_id": production.strategy_id,
        "status": production.status,
        "veo_jobs": production.veo_jobs or [],
        "clips_paths": production.clips_paths or [],
        "tts": {
            "file_path": production.tts_file_path,
            "provider": production.tts_provider,
            "duration_seconds": _decimal_to_float(production.narration_duration_seconds),
            "cost_usd": _decimal_to_float(production.tts_cost_usd),
        },
        "video": {
            "final_path": production.final_video_path,
            "duration_seconds": production.final_duration_seconds,
            "resolution": production.final_resolution,
            "file_size_mb": _decimal_to_float(production.final_file_size_mb),
        },
        "costs": {
            "veo_cost_usd": _decimal_to_float(production.veo_cost_usd),
            "total_production_cost_usd": _decimal_to_float(production.total_production_cost_usd),
        },
        "publishing": {
            "is_published": production.is_published,
            "platform": production.published_platform,
            "url": production.published_url,
            "published_at": _dt_to_iso(production.published_at),
            "post_metrics": {
                "views": production.post_views,
                "likes": production.post_likes,
                "comments": production.post_comments,
                "shares": production.post_shares,
            },
        },
        "error": production.error_message,
        "created_at": _dt_to_iso(production.created_at),
        "updated_at": _dt_to_iso(production.updated_at),
    }


def _get_video_dict(video_id: int) -> dict[str, Any]:
    db = get_sync_db()
    try:
        video = db.get(ViralVideo, video_id)
        if not video:
            raise ValueError(f"Video {video_id} nao encontrado")
        return _video_to_dict(video)
    finally:
        db.close()


def _get_strategy_dict(strategy_id: int) -> dict[str, Any]:
    db = get_sync_db()
    try:
        strategy = db.get(GeneratedStrategy, strategy_id)
        if not strategy:
            raise ValueError(f"Estrategia {strategy_id} nao encontrada")
        return _strategy_to_dict(strategy)
    finally:
        db.close()


def _get_production_dict(production_id: int) -> dict[str, Any]:
    db = get_sync_db()
    try:
        production = db.get(ProducedVideo, production_id)
        if not production:
            raise ValueError(f"Producao {production_id} nao encontrada")
        return _production_to_dict(production)
    finally:
        db.close()


@mcp.tool()
async def scrape_profile(
    username: Optional[str] = None,
    profile_id: Optional[int] = None,
    max_videos: int = 50,
) -> dict[str, Any]:
    """Coleta videos virais de um perfil do Instagram e aplica pre-filtro estatistico."""

    def _run() -> dict[str, Any]:
        if not username and not profile_id:
            raise ValueError("Informe username ou profile_id")
        result = watcher_agent.run(
            profile_id=profile_id,
            username=username,
            max_videos=max_videos,
        )
        return {
            "run_id": result.run_id,
            "profile_username": result.profile_username,
            "videos_collected": result.videos_collected,
            "videos_prefiltered": result.videos_prefiltered,
            "cost_usd": result.cost_usd,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def analyze_video(video_id: int, force: bool = False) -> dict[str, Any]:
    """Analisa um video especifico com o provider configurado (Gemini ou Claude) e salva o resultado no banco."""

    def _run() -> dict[str, Any]:
        agent = get_analyst_agent()
        result = agent.analyze(video_id, force=force)
        return {
            "run_id": result.run_id,
            "video_id": result.video_id,
            "virality_score": result.virality_score,
            "replicability_score": result.replicability_score,
            "is_valid": result.is_valid,
            "cost_usd": result.cost_usd,
            "duration_seconds": result.duration_seconds,
            "error": result.error,
            "provider": agent.provider,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def analyze_video_with_claude(video_id: int, force: bool = False) -> dict[str, Any]:
    """Analisa um video especifico usando Claude (ignora config VIDEO_ANALYSIS_PROVIDER).

    Use esta tool quando a quota do Gemini estiver esgotada ou quando preferir
    analise mais detalhada com Claude.
    """

    def _run() -> dict[str, Any]:
        agent = get_analyst_agent(provider="claude")
        result = agent.analyze(video_id, force=force)
        return {
            "run_id": result.run_id,
            "video_id": result.video_id,
            "virality_score": result.virality_score,
            "replicability_score": result.replicability_score,
            "is_valid": result.is_valid,
            "cost_usd": result.cost_usd,
            "duration_seconds": result.duration_seconds,
            "error": result.error,
            "provider": "claude",
        }

    return await _run_in_thread(_run)


def _get_video_for_analysis_sync(video_id: int, include_video_base64: bool = True) -> dict[str, Any]:
    """Busca video completo com todos os metadados para analise."""
    db = get_sync_db()
    try:
        video = db.get(ViralVideo, video_id)
        if not video:
            raise ValueError(f"Video {video_id} nao encontrado")

        result = {
            "id": video.id,
            "shortcode": video.shortcode,
            "source_url": video.source_url,
            "caption": video.caption,
            "hashtags": video.hashtags or [],
            "mentions": video.mentions or [],
            "duration_seconds": video.duration_seconds,
            "posted_at": _dt_to_iso(video.posted_at),
            "metrics": {
                "views": video.views_count,
                "likes": video.likes_count,
                "comments": video.comments_count,
                "shares": video.shares_count,
                "saves": video.saves_count,
            },
            "scores": {
                "statistical_viral_score": _decimal_to_float(video.statistical_viral_score),
                "normalized_views": _decimal_to_float(video.normalized_views),
                "normalized_engagement": _decimal_to_float(video.normalized_engagement),
            },
            "profile": {
                "id": video.profile_id,
                "username": video.profile.username if video.profile else None,
                "niche": video.profile.niche if video.profile else None,
            },
            "transcription": video.transcription,
            "analysis": None,
            "video_base64": None,
            "video_available": False,
        }

        # Inclui analise se existir
        if video.analysis:
            result["analysis"] = {
                # Scores
                "virality_score": _decimal_to_float(video.analysis.virality_score),
                "replicability_score": _decimal_to_float(video.analysis.replicability_score),
                "production_quality_score": _decimal_to_float(video.analysis.production_quality_score),
                # Analise estrutural
                "hook_analysis": video.analysis.hook_analysis,
                "development": video.analysis.development,
                "cta_analysis": video.analysis.cta_analysis,
                "viral_factors": video.analysis.viral_factors,
                # Analise semantica completa
                "visual_elements": video.analysis.visual_elements,
                "audio_elements": video.analysis.audio_elements,
                "performance_elements": video.analysis.performance_elements,
                "replication_guide": video.analysis.replication_guide,
                "script_suggestion": video.analysis.script_suggestion,
                # Raw response (backup)
                "raw_gemini_response": video.analysis.raw_gemini_response,
            }

        # Tenta baixar video do MinIO se solicitado
        if include_video_base64 and video.video_file_path:
            try:
                # Remove prefixo do bucket se presente
                remote_path = video.video_file_path
                if remote_path.startswith(f"{storage_tools.bucket}/"):
                    remote_path = remote_path[len(storage_tools.bucket) + 1:]

                video_bytes = storage_tools.download_bytes(remote_path)
                result["video_base64"] = base64.b64encode(video_bytes).decode("utf-8")
                result["video_available"] = True
                result["video_size_bytes"] = len(video_bytes)
                result["video_mime_type"] = "video/mp4"
            except Exception as e:
                result["video_error"] = str(e)

        return result
    finally:
        db.close()


@mcp.tool()
async def get_video_for_analysis(
    video_id: int,
    include_video: bool = True,
) -> dict[str, Any]:
    """Retorna video completo com metadados para analise direta pelo Claude.

    Use esta tool para analisar:
    - Semantica e estrutura do video
    - Hooks de atencao e CTAs
    - Padroes de viralizacao
    - Elementos visuais e narrativos
    - Transcricao e legendas

    Args:
        video_id: ID do video no banco
        include_video: Se True, inclui video em base64 (default: True)

    Returns:
        Dicionario com video em base64, transcricao, caption, metricas e analises previas
    """
    return await _run_in_thread(_get_video_for_analysis_sync, video_id, include_video)


@mcp.tool()
async def generate_strategy(video_id: int, niche: Optional[str] = None) -> dict[str, Any]:
    """Gera estrategia de conteudo usando um video analisado como referencia."""

    def _run() -> dict[str, Any]:
        result = strategist_agent.generate(video_id, niche=niche)
        return {
            "run_id": result.run_id,
            "strategy_id": result.strategy_id,
            "title": result.title,
            "num_scenes": result.num_scenes,
            "estimated_cost_usd": result.estimated_cost_usd,
            "cost_usd": result.cost_usd,
            "duration_seconds": result.duration_seconds,
            "is_valid": result.is_valid,
            "error": result.error,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def produce_video(strategy_id: int, mode: str = "test", music_track: Optional[str] = None) -> dict[str, Any]:
    """Produz video completo a partir de uma estrategia (modo test ou production)."""

    def _run() -> dict[str, Any]:
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
            "error": result.error,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def get_budget_status() -> dict[str, Any]:
    """Retorna status atualizado do orcamento diario e contadores."""
    return await _run_in_thread(budget_tools.get_daily_status)


@mcp.tool()
async def export_to_google_sheets(
    videos_limit: int = 50,
    strategies_limit: int = 50,
    productions_limit: int = 50,
    include_status: bool = True,
) -> dict[str, Any]:
    """Exporta videos, estrategias, producoes e status para Google Sheets."""

    def _run() -> dict[str, Any]:
        return sheets_exporter.export_all(
            videos_limit=videos_limit,
            strategies_limit=strategies_limit,
            productions_limit=productions_limit,
            include_status=include_status,
        )

    return await _run_in_thread(_run)


def _list_videos_sync(status: str, limit: int) -> list[dict[str, Any]]:
    valid_status = {"all", "pending", "analyzed"}
    if status not in valid_status:
        raise ValueError(f"Status invalido: {status}")

    db = get_sync_db()
    try:
        stmt = select(ViralVideo)
        if status == "pending":
            stmt = stmt.where(
                ViralVideo.passes_prefilter == True,  # noqa: E712
                ViralVideo.is_analyzed == False,  # noqa: E712
            )
        elif status == "analyzed":
            stmt = stmt.where(ViralVideo.is_analyzed == True)  # noqa: E712

        stmt = stmt.order_by(ViralVideo.statistical_viral_score.desc()).limit(limit)
        videos = db.execute(stmt).scalars().all()
        return [_video_to_dict(v) for v in videos]
    finally:
        db.close()


@mcp.tool()
async def list_videos(status: str = "all", limit: int = 20) -> list[dict[str, Any]]:
    """Lista videos coletados com filtros basicos de status."""
    return await _run_in_thread(_list_videos_sync, status, limit)


def _list_strategies_sync(status: str, limit: int) -> list[dict[str, Any]]:
    valid_status = {s.value for s in StrategyStatus} | {"all"}
    if status not in valid_status:
        raise ValueError(f"Status invalido: {status}")

    db = get_sync_db()
    try:
        stmt = select(GeneratedStrategy)
        if status != "all":
            stmt = stmt.where(GeneratedStrategy.status == status)

        stmt = stmt.order_by(GeneratedStrategy.created_at.desc()).limit(limit)
        strategies = db.execute(stmt).scalars().all()
        return [_strategy_to_dict(s) for s in strategies]
    finally:
        db.close()


@mcp.tool()
async def list_strategies(status: str = "all", limit: int = 20) -> list[dict[str, Any]]:
    """Lista estrategias geradas, filtrando por status."""
    return await _run_in_thread(_list_strategies_sync, status, limit)


@mcp.tool()
async def get_production_status(production_id: int) -> dict[str, Any]:
    """Consulta status detalhado de uma producao especifica."""
    return await _run_in_thread(_get_production_dict, production_id)


@mcp.resource(
    "viralforge://budget/today",
    title="Orcamento diario",
    description="Status atual de uso de budget e contadores do dia",
    mime_type="application/json",
)
async def budget_resource() -> dict[str, Any]:
    return await _run_in_thread(budget_tools.get_daily_status)


@mcp.resource(
    "viralforge://videos/{id}",
    title="Video coletado",
    description="Detalhes de um video viral coletado",
    mime_type="application/json",
)
async def video_resource(id: int) -> dict[str, Any]:  # noqa: A002
    return await _run_in_thread(_get_video_dict, id)


@mcp.resource(
    "viralforge://strategies/{id}",
    title="Estrategia gerada",
    description="Detalhes completos de uma estrategia",
    mime_type="application/json",
)
async def strategy_resource(id: int) -> dict[str, Any]:  # noqa: A002
    return await _run_in_thread(_get_strategy_dict, id)


@mcp.resource(
    "viralforge://productions/{id}",
    title="Producao de video",
    description="Status e metadados de uma producao",
    mime_type="application/json",
)
async def production_resource(id: int) -> dict[str, Any]:  # noqa: A002
    return await _run_in_thread(_get_production_dict, id)


def _next_production_sync(mode: Optional[str] = None) -> dict[str, Any]:
    """Produce next approved strategy, used as a convenience helper."""
    result = producer_agent.produce_next_approved(mode=mode)
    if not result:
        return {"status": "no-approved-strategy-found"}
    return {
        "run_id": result.run_id,
        "production_id": result.production_id,
        "strategy_id": result.strategy_id,
        "final_video_path": result.final_video_path,
        "duration_seconds": result.duration_seconds,
        "total_cost_usd": result.total_cost_usd,
        "production_time_seconds": result.production_time_seconds,
    }


@mcp.tool()
async def produce_next_approved(mode: Optional[str] = None) -> dict[str, Any]:
    """Produz automaticamente a proxima estrategia aprovada (fila FIFO)."""
    return await _run_in_thread(_next_production_sync, mode)


# === Tools de Download e Transcricao ===


def _download_video_sync(video_id: int) -> dict[str, Any]:
    """Baixa video do Instagram e salva no MinIO."""
    db = get_sync_db()
    try:
        video = db.get(ViralVideo, video_id)
        if not video:
            raise ValueError(f"Video {video_id} nao encontrado")

        if video.is_downloaded and video.video_file_path:
            return {
                "success": True,
                "status": "already_downloaded",
                "video_id": video_id,
                "video_path": video.video_file_path,
                "thumbnail_path": video.thumbnail_path,
                "duration_seconds": video.duration_seconds,
            }

        # Cria diretorio temporario para download
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = Path(tmp_dir) / f"{video.platform_id}.mp4"

            # Download do Instagram
            success = scraping_tools.download_video(video.source_url, str(local_path))
            if not success:
                return {
                    "success": False,
                    "status": "download_failed",
                    "video_id": video_id,
                    "error": "Falha no download do video do Instagram",
                }

            # Upload para MinIO
            remote_path = storage_tools.upload_video(local_path, video.id)

            # Atualiza video no banco
            video.video_file_path = remote_path
            video.is_downloaded = True
            db.commit()

            return {
                "success": True,
                "status": "downloaded",
                "video_id": video_id,
                "video_path": remote_path,
                "thumbnail_path": video.thumbnail_path,
                "duration_seconds": video.duration_seconds,
            }
    finally:
        db.close()


@mcp.tool()
async def download_video(video_id: int) -> dict[str, Any]:
    """Baixa um video especifico do Instagram e salva no storage.

    O video e baixado do Instagram usando a URL original e armazenado no MinIO.
    Se o video ja foi baixado anteriormente, retorna o caminho existente.

    Args:
        video_id: ID do video no banco de dados

    Returns:
        {success, status, video_path, thumbnail_path, duration_seconds}
    """
    return await _run_in_thread(_download_video_sync, video_id)


def _transcribe_video_sync(
    video_id: int,
    language: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict[str, Any]:
    """Transcreve audio de um video usando Whisper (local ou Groq)."""
    from src.tools.whisper_tools import WhisperTools

    db = get_sync_db()
    try:
        video = db.get(ViralVideo, video_id)
        if not video:
            raise ValueError(f"Video {video_id} nao encontrado")

        if video.is_transcribed and video.transcription:
            return {
                "success": True,
                "status": "already_transcribed",
                "video_id": video_id,
                "transcription": video.transcription,
                "language": video.transcription_language,
                "confidence": _decimal_to_float(video.transcription_confidence),
            }

        if not video.video_file_path:
            return {
                "success": False,
                "status": "video_not_downloaded",
                "video_id": video_id,
                "error": "Video precisa ser baixado primeiro. Use download_video.",
            }

        # Download do MinIO para arquivo temporario
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = Path(tmp_dir) / "video.mp4"

            # Remove prefixo do bucket se presente
            remote_path = video.video_file_path
            if remote_path.startswith(f"{storage_tools.bucket}/"):
                remote_path = remote_path[len(storage_tools.bucket) + 1:]

            storage_tools.download_file(remote_path, local_path)

            # Transcreve com Whisper (local ou Groq)
            tools = WhisperTools(provider=provider) if provider else whisper_tools
            result = tools.transcribe_video(local_path, language=language)

            # Atualiza video no banco
            video.transcription = result.text
            video.transcription_language = result.language
            video.transcription_confidence = result.confidence
            video.is_transcribed = True
            db.commit()

            return {
                "success": True,
                "status": "transcribed",
                "video_id": video_id,
                "transcription": result.text,
                "language": result.language,
                "confidence": result.confidence,
                "duration_seconds": result.duration_seconds,
                "segments": result.segments,
                "provider": provider or settings.whisper_provider,
            }
    finally:
        db.close()


@mcp.tool()
async def transcribe_video(
    video_id: int,
    language: str = "pt",
    provider: str = "",
) -> dict[str, Any]:
    """Transcreve o audio de um video usando Whisper (local ou Groq).

    O video deve ter sido baixado anteriormente com download_video.
    A transcricao e salva no banco e retornada.

    Args:
        video_id: ID do video no banco de dados
        language: Codigo do idioma (pt, en, es, etc). Default: pt
        provider: Provider de transcricao ("local" ou "groq"). Se vazio, usa config.

    Returns:
        {success, status, transcription, language, confidence, segments, provider}
    """
    lang = language if language != "pt" else None
    prov = provider if provider in ("local", "groq") else None
    return await _run_in_thread(_transcribe_video_sync, video_id, lang, prov)


def _full_pipeline_sync(video_id: int, analyzer: str = "gemini") -> dict[str, Any]:
    """Executa pipeline completo: download + transcricao + analise."""
    results = {
        "video_id": video_id,
        "steps": {},
        "success": False,
    }

    # Step 1: Download
    download_result = _download_video_sync(video_id)
    results["steps"]["download"] = download_result
    if not download_result["success"]:
        results["error"] = "Falha no download"
        return results

    # Step 2: Transcricao
    transcribe_result = _transcribe_video_sync(video_id, language=None)
    results["steps"]["transcribe"] = transcribe_result
    if not transcribe_result["success"]:
        results["error"] = "Falha na transcricao"
        return results

    # Step 3: Analise
    try:
        agent = get_analyst_agent(provider=analyzer if analyzer in ("gemini", "claude") else None)
        analysis_result = agent.analyze(video_id, force=False)
        results["steps"]["analyze"] = {
            "success": True,
            "run_id": analysis_result.run_id,
            "virality_score": analysis_result.virality_score,
            "replicability_score": analysis_result.replicability_score,
            "is_valid": analysis_result.is_valid,
            "cost_usd": analysis_result.cost_usd,
            "provider": agent.provider,
        }
    except Exception as e:
        results["steps"]["analyze"] = {
            "success": False,
            "error": str(e),
        }
        results["error"] = f"Falha na analise: {e}"
        return results

    results["success"] = True
    results["final_analysis"] = results["steps"]["analyze"]
    return results


@mcp.tool()
async def full_pipeline(video_id: int, analyzer: str = "gemini") -> dict[str, Any]:
    """Executa pipeline completo: download + transcricao + analise.

    Pipeline em sequencia:
    1. Baixa o video do Instagram
    2. Transcreve o audio usando Whisper
    3. Analisa com IA (Gemini ou Claude)

    Cada etapa so executa se a anterior nao foi feita ainda.

    Args:
        video_id: ID do video no banco de dados
        analyzer: Provider de analise - "gemini" ou "claude"

    Returns:
        Resultado completo com status de cada etapa e analise final
    """
    return await _run_in_thread(_full_pipeline_sync, video_id, analyzer)


def _get_semantic_analysis_sync(video_id: int) -> dict[str, Any]:
    """Retorna analise semantica completa de um video."""
    db = get_sync_db()
    try:
        video = db.get(ViralVideo, video_id)
        if not video:
            raise ValueError(f"Video {video_id} nao encontrado")

        if not video.analysis:
            return {
                "success": False,
                "video_id": video_id,
                "error": "Video nao foi analisado ainda. Use analyze_video ou full_pipeline primeiro.",
            }

        analysis = video.analysis
        return {
            "success": True,
            "video_id": video_id,
            "video_info": {
                "shortcode": video.shortcode,
                "source_url": video.source_url,
                "caption": video.caption,
                "duration_seconds": video.duration_seconds,
                "metrics": {
                    "views": video.views_count,
                    "likes": video.likes_count,
                    "comments": video.comments_count,
                },
            },
            "transcription": video.transcription,
            "scores": {
                "virality_score": _decimal_to_float(analysis.virality_score),
                "replicability_score": _decimal_to_float(analysis.replicability_score),
                "production_quality_score": _decimal_to_float(analysis.production_quality_score),
            },
            "semantic_analysis": {
                "hook_analysis": analysis.hook_analysis,
                "development": analysis.development,
                "cta_analysis": analysis.cta_analysis,
                "viral_factors": analysis.viral_factors,
                "visual_elements": analysis.visual_elements,
                "audio_elements": analysis.audio_elements,
                "performance_elements": analysis.performance_elements,
                "replication_guide": analysis.replication_guide,
            },
            "script_suggestion": analysis.script_suggestion,
            "is_valid_json": analysis.is_valid_json,
            "analyzed_at": _dt_to_iso(analysis.analyzed_at),
        }
    finally:
        db.close()


@mcp.tool()
async def get_semantic_analysis(video_id: int) -> dict[str, Any]:
    """Retorna analise semantica COMPLETA de um video analisado.

    Inclui todos os elementos de analise:
    - Hook (0-3s): tipo de abertura, tecnica de atencao, primeiras palavras
    - Desenvolvimento: estrutura, pontos-chave, ritmo, tecnicas de retencao
    - CTA: tipo, texto, tecnica, urgencia
    - Fatores Virais: gatilhos emocionais, compartilhabilidade, trends

    ANALISE VISUAL COMPLETA:
    - Cores dominantes
    - Enquadramento (close/medio/aberto)
    - Iluminacao
    - Texto na tela (estilo, timing)
    - Transicoes e cortes por minuto

    ANALISE DE AUDIO:
    - Tipo de voz (direta/voz_off)
    - Tom de voz
    - Musica (tipo, volume)
    - Efeitos sonoros

    ANALISE DE PERFORMANCE:
    - Expressoes faciais
    - Linguagem corporal
    - Contato visual
    - Nivel de energia
    - Bordoes/frases de efeito

    GUIA DE REPLICACAO:
    - Equipamentos necessarios
    - Nivel de dificuldade
    - Tempo de producao
    - Elementos-chave para copiar
    - Sugestoes de adaptacao

    ROTEIRO SUGERIDO:
    - Script pronto baseado nos padroes do video

    Args:
        video_id: ID do video no banco de dados

    Returns:
        Analise semantica completa com todos os elementos
    """
    return await _run_in_thread(_get_semantic_analysis_sync, video_id)


# === Tools de Integracao Multi-Plataforma (SparkOne) ===


def _detect_platform(url: str) -> str:
    """Detecta plataforma a partir da URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "tiktok.com" in url_lower or "vt.tiktok.com" in url_lower:
        return "tiktok"
    elif "instagram.com" in url_lower or "instagr.am" in url_lower:
        return "instagram"
    return "unknown"


def _generate_platform_id(url: str, platform: str) -> str:
    """Gera ID unico baseado na URL."""
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{platform}_{url_hash}"


def _ingest_video_from_url_sync(
    url: str,
    creator: str,
    niche: Optional[str] = None,
) -> dict[str, Any]:
    """Baixa video de qualquer plataforma e cria registro no banco."""
    platform = _detect_platform(url)
    if platform == "unknown":
        return {
            "success": False,
            "error": f"Plataforma nao suportada. URL: {url}",
            "supported_platforms": VideoDownloaderFactory.get_supported_platforms(),
        }

    # Verifica se video ja existe
    platform_id = _generate_platform_id(url, platform)
    db = get_sync_db()
    try:
        existing = db.execute(
            select(ViralVideo).where(ViralVideo.platform_id == platform_id)
        ).scalar_one_or_none()

        if existing:
            return {
                "success": True,
                "status": "already_exists",
                "video_id": existing.id,
                "platform": platform,
                "creator": creator,
                "is_downloaded": existing.is_downloaded,
                "is_transcribed": existing.is_transcribed,
                "is_analyzed": existing.is_analyzed,
            }

        # Cria diretorio temporario para download
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            # Usa factory para selecionar downloader
            downloader = VideoDownloaderFactory.create_downloader(
                url, output_dir, meta_api_key=settings.meta_access_token
            )

            if not downloader:
                return {
                    "success": False,
                    "error": f"Nenhum downloader disponivel para: {url}",
                }

            # Download
            local_path = downloader.download(url, creator)
            if not local_path or not local_path.exists():
                return {
                    "success": False,
                    "error": f"Falha no download do video de {platform}",
                }

            # Upload para MinIO
            remote_path = f"videos/{creator}/{platform_id}.mp4"
            storage_tools.upload_file(local_path, remote_path)

            # Cria registro no banco
            video = ViralVideo(
                platform_id=platform_id,
                shortcode=f"{creator}_{platform_id[:8]}",
                source_url=url,
                caption=f"[{platform.upper()}] @{creator}" + (f" | Niche: {niche}" if niche else ""),
                hashtags=[platform, creator, niche] if niche else [platform, creator],
                video_file_path=remote_path,
                is_downloaded=True,
                passes_prefilter=True,  # Videos manuais passam direto
            )
            db.add(video)
            db.commit()
            db.refresh(video)

            return {
                "success": True,
                "status": "ingested",
                "video_id": video.id,
                "platform": platform,
                "creator": creator,
                "niche": niche,
                "video_path": remote_path,
                "is_downloaded": True,
                "is_transcribed": False,
                "is_analyzed": False,
            }
    finally:
        db.close()


@mcp.tool()
async def ingest_video_from_url(
    url: str,
    creator: str,
    niche: str = "",
) -> dict[str, Any]:
    """Baixa video de YouTube, TikTok ou Instagram e salva no banco.

    Funciona como porta de entrada para videos de qualquer plataforma.
    O video e baixado, armazenado no MinIO e registrado no banco de dados.

    Apos a ingestao, use:
    - transcribe_video(video_id) para transcrever
    - analyze_video(video_id) para analisar
    - full_pipeline(video_id) para fazer tudo de uma vez

    Args:
        url: URL do video (YouTube, TikTok ou Instagram)
        creator: Nome do criador (@username)
        niche: Nicho do conteudo (opcional)

    Returns:
        {success, video_id, platform, creator, status}
    """
    return await _run_in_thread(_ingest_video_from_url_sync, url, creator, niche if niche else None)


def _list_creators_sync() -> dict[str, Any]:
    """Lista criadores unicos dos videos."""
    db = get_sync_db()
    try:
        videos = db.execute(
            select(ViralVideo).where(ViralVideo.is_downloaded == True)  # noqa: E712
        ).scalars().all()

        creators: dict[str, dict] = {}
        for v in videos:
            # Extrai creator do caption ou hashtags
            creator = None
            platform = "unknown"

            # Tenta extrair de caption formatado
            if v.caption and v.caption.startswith("["):
                parts = v.caption.split("@")
                if len(parts) > 1:
                    creator_part = parts[1].split()[0] if parts[1] else None
                    if creator_part:
                        creator = creator_part.strip()
                    # Extrai plataforma
                    if "[YOUTUBE]" in v.caption.upper():
                        platform = "youtube"
                    elif "[TIKTOK]" in v.caption.upper():
                        platform = "tiktok"
                    elif "[INSTAGRAM]" in v.caption.upper():
                        platform = "instagram"

            # Fallback para hashtags
            if not creator and v.hashtags:
                for tag in v.hashtags:
                    if tag not in ("youtube", "tiktok", "instagram"):
                        creator = tag
                        break
                if not creator and len(v.hashtags) > 1:
                    creator = v.hashtags[1]

            # Fallback para profile
            if not creator and v.profile:
                creator = v.profile.username

            if not creator:
                creator = f"unknown_{v.id}"

            # Detecta plataforma do platform_id
            if platform == "unknown" and v.platform_id:
                if v.platform_id.startswith("youtube_"):
                    platform = "youtube"
                elif v.platform_id.startswith("tiktok_"):
                    platform = "tiktok"
                elif v.platform_id.startswith("instagram_") or v.platform_id.isdigit():
                    platform = "instagram"

            # Agrupa por creator
            if creator not in creators:
                creators[creator] = {
                    "creator": creator,
                    "platforms": set(),
                    "video_count": 0,
                    "transcribed_count": 0,
                    "analyzed_count": 0,
                    "video_ids": [],
                }

            creators[creator]["platforms"].add(platform)
            creators[creator]["video_count"] += 1
            creators[creator]["video_ids"].append(v.id)
            if v.is_transcribed:
                creators[creator]["transcribed_count"] += 1
            if v.is_analyzed:
                creators[creator]["analyzed_count"] += 1

        # Converte sets para lists
        result = []
        for c in creators.values():
            c["platforms"] = list(c["platforms"])
            result.append(c)

        return {
            "success": True,
            "creators": result,
            "total_creators": len(result),
        }
    finally:
        db.close()


@mcp.tool()
async def list_creators() -> dict[str, Any]:
    """Lista todos os criadores com videos no sistema.

    Retorna lista de criadores com:
    - Plataformas onde tem videos
    - Quantidade de videos
    - Quantos foram transcritos
    - Quantos foram analisados
    - IDs dos videos

    Util para o SparkOne listar criadores disponiveis para referencia.
    """
    return await _run_in_thread(_list_creators_sync)


def _get_creator_transcriptions_sync(creator: str) -> dict[str, Any]:
    """Retorna transcricoes de um criador especifico."""
    db = get_sync_db()
    try:
        # Busca videos que mencionam o creator
        videos = db.execute(
            select(ViralVideo).where(
                ViralVideo.is_transcribed == True,  # noqa: E712
                ViralVideo.transcription.isnot(None),
            )
        ).scalars().all()

        # Filtra por creator
        creator_videos = []
        creator_lower = creator.lower()

        for v in videos:
            match = False

            # Verifica no caption
            if v.caption and creator_lower in v.caption.lower():
                match = True

            # Verifica nas hashtags
            if not match and v.hashtags:
                for tag in v.hashtags:
                    if creator_lower in tag.lower():
                        match = True
                        break

            # Verifica no shortcode
            if not match and v.shortcode and creator_lower in v.shortcode.lower():
                match = True

            # Verifica no profile
            if not match and v.profile and creator_lower in v.profile.username.lower():
                match = True

            if match:
                # Extrai niche do caption se disponivel
                niche = None
                if v.caption and "Niche:" in v.caption:
                    niche = v.caption.split("Niche:")[-1].strip()

                creator_videos.append({
                    "video_id": v.id,
                    "source_url": v.source_url,
                    "transcription": v.transcription,
                    "language": v.transcription_language,
                    "confidence": _decimal_to_float(v.transcription_confidence),
                    "duration_seconds": v.duration_seconds,
                    "niche": niche,
                    "has_analysis": v.is_analyzed,
                    "views": v.views_count,
                    "likes": v.likes_count,
                })

        return {
            "success": True,
            "creator": creator,
            "transcriptions": creator_videos,
            "count": len(creator_videos),
        }
    finally:
        db.close()


@mcp.tool()
async def get_creator_transcriptions(creator: str) -> dict[str, Any]:
    """Retorna todas as transcricoes de um criador especifico.

    Busca videos que mencionam o criador no caption, hashtags ou profile.
    Retorna transcricoes completas com metadados.

    Util para o SparkOne criar roteiros baseados em criadores especificos.

    Args:
        creator: Nome do criador (@username ou nome parcial)

    Returns:
        Lista de transcricoes com video_id, source_url, transcription, etc.
    """
    return await _run_in_thread(_get_creator_transcriptions_sync, creator)


def _search_transcriptions_sync(query: str, limit: int = 20) -> dict[str, Any]:
    """Busca em todas as transcricoes."""
    db = get_sync_db()
    try:
        # Busca videos transcritos
        videos = db.execute(
            select(ViralVideo).where(
                ViralVideo.is_transcribed == True,  # noqa: E712
                ViralVideo.transcription.isnot(None),
            )
        ).scalars().all()

        # Filtra por query
        results = []
        query_lower = query.lower()

        for v in videos:
            if not v.transcription:
                continue

            # Busca na transcricao
            transcription_lower = v.transcription.lower()
            if query_lower in transcription_lower:
                # Encontra contexto
                idx = transcription_lower.find(query_lower)
                start = max(0, idx - 100)
                end = min(len(v.transcription), idx + len(query) + 100)
                context = v.transcription[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(v.transcription):
                    context = context + "..."

                # Extrai creator
                creator = None
                if v.caption and "@" in v.caption:
                    parts = v.caption.split("@")
                    if len(parts) > 1:
                        creator = parts[1].split()[0] if parts[1] else None
                if not creator and v.profile:
                    creator = v.profile.username

                results.append({
                    "video_id": v.id,
                    "creator": creator,
                    "source_url": v.source_url,
                    "context": context,
                    "full_transcription": v.transcription,
                    "has_analysis": v.is_analyzed,
                    "duration_seconds": v.duration_seconds,
                })

                if len(results) >= limit:
                    break

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
        }
    finally:
        db.close()


@mcp.tool()
async def search_transcriptions(query: str, limit: int = 20) -> dict[str, Any]:
    """Busca texto em todas as transcricoes do sistema.

    Busca full-text em todas as transcricoes.
    Retorna contexto com a busca destacada.

    Util para o SparkOne encontrar referencias sobre temas especificos.

    Args:
        query: Texto a buscar nas transcricoes
        limit: Maximo de resultados (default: 20)

    Returns:
        Lista de matches com contexto, video_id, creator, etc.
    """
    return await _run_in_thread(_search_transcriptions_sync, query, limit)


# ============================================================================
# INSTAGRAM COMPLETE SCRAPING TOOLS
# ============================================================================

from src.tools.instagram_scraper import instagram_scraper, FullScrapingResult


def _story_to_dict(story) -> dict[str, Any]:
    """Serializa ScrapedStory para dict."""
    return {
        "story_id": story.story_id,
        "owner_username": story.owner_username,
        "media_type": story.media_type,
        "is_video": story.is_video,
        "media_url": story.media_url,
        "video_url": story.video_url,
        "duration_seconds": story.duration_seconds,
        "has_music": story.has_music,
        "music_info": story.music_info,
        "has_poll": story.has_poll,
        "has_question": story.has_question,
        "has_link": story.has_link,
        "link_url": story.link_url,
        "mentions": story.mentions,
        "hashtags": story.hashtags,
        "taken_at": story.taken_at.isoformat() if story.taken_at else None,
        "expiring_at": story.expiring_at.isoformat() if story.expiring_at else None,
    }


def _carousel_to_dict(carousel) -> dict[str, Any]:
    """Serializa ScrapedCarousel para dict."""
    return {
        "carousel_id": carousel.carousel_id,
        "shortcode": carousel.shortcode,
        "source_url": carousel.source_url,
        "owner_username": carousel.owner_username,
        "likes_count": carousel.likes_count,
        "comments_count": carousel.comments_count,
        "caption": carousel.caption,
        "hashtags": carousel.hashtags,
        "mentions": carousel.mentions,
        "slide_count": len(carousel.slides),
        "slides": [
            {
                "index": s.index,
                "media_type": s.media_type,
                "url": s.url,
                "is_video": s.is_video,
                "duration_seconds": s.duration_seconds,
            }
            for s in carousel.slides
        ],
        "posted_at": carousel.posted_at.isoformat() if carousel.posted_at else None,
    }


def _comment_to_dict(comment) -> dict[str, Any]:
    """Serializa ScrapedComment para dict."""
    return {
        "comment_id": comment.comment_id,
        "author_username": comment.author_username,
        "author_full_name": comment.author_full_name,
        "is_author_verified": comment.is_author_verified,
        "text": comment.text,
        "likes_count": comment.likes_count,
        "replies_count": comment.replies_count,
        "is_reply": comment.is_reply,
        "is_pinned": comment.is_pinned,
        "is_from_creator": comment.is_from_creator,
        "replies": [_comment_to_dict(r) for r in comment.replies],
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


def _profile_to_dict(profile) -> dict[str, Any]:
    """Serializa ScrapedProfile para dict."""
    return {
        "instagram_id": profile.instagram_id,
        "username": profile.username,
        "full_name": profile.full_name,
        "biography": profile.biography,
        "external_url": profile.external_url,
        "profile_pic_url": profile.profile_pic_url,
        "follower_count": profile.follower_count,
        "following_count": profile.following_count,
        "media_count": profile.media_count,
        "is_private": profile.is_private,
        "is_verified": profile.is_verified,
        "is_business": profile.is_business,
        "business_category": profile.business_category,
        "avg_likes": profile.avg_likes,
        "avg_comments": profile.avg_comments,
        "engagement_rate": profile.engagement_rate,
        "top_hashtags": profile.top_hashtags,
    }


@mcp.tool()
async def scrape_instagram_profile(username: str) -> dict[str, Any]:
    """Coleta dados completos de um perfil do Instagram.

    Retorna: followers, following, posts, bio, verificacao, categoria de negocio, etc.

    Args:
        username: Username do perfil (sem @)

    Returns:
        Dados completos do perfil
    """
    def _run() -> dict[str, Any]:
        profile = instagram_scraper.scrape_profile(username)
        return _profile_to_dict(profile)

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_instagram_stories(username: str) -> dict[str, Any]:
    """Coleta stories ativos de um perfil (conteudo efemero 24h).

    Captura: media, musica, polls, perguntas, links, stickers, etc.

    Args:
        username: Username do perfil (sem @)

    Returns:
        Lista de stories com todos os dados
    """
    def _run() -> dict[str, Any]:
        stories = instagram_scraper.scrape_stories(username)
        return {
            "username": username,
            "story_count": len(stories),
            "stories": [_story_to_dict(s) for s in stories],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_instagram_carousels(
    username: str,
    max_posts: int = 50,
) -> dict[str, Any]:
    """Coleta carrosseis (posts com multiplas midias) de um perfil.

    Retorna cada slide individual com URLs e metricas.

    Args:
        username: Username do perfil (sem @)
        max_posts: Maximo de posts a verificar

    Returns:
        Lista de carrosseis com slides
    """
    def _run() -> dict[str, Any]:
        carousels = instagram_scraper.scrape_carousels(username, max_posts)
        return {
            "username": username,
            "carousel_count": len(carousels),
            "carousels": [_carousel_to_dict(c) for c in carousels],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_instagram_comments(
    post_url: str,
    max_comments: int = 100,
    include_replies: bool = True,
) -> dict[str, Any]:
    """Coleta comentarios de um post/reel do Instagram.

    Inclui: autor, texto, likes, respostas aninhadas, verificacao, etc.

    Args:
        post_url: URL do post
        max_comments: Maximo de comentarios
        include_replies: Incluir respostas

    Returns:
        Lista de comentarios com replies
    """
    def _run() -> dict[str, Any]:
        comments = instagram_scraper.scrape_comments(post_url, max_comments, include_replies)
        return {
            "post_url": post_url,
            "comment_count": len(comments),
            "total_with_replies": sum(1 + len(c.replies) for c in comments),
            "comments": [_comment_to_dict(c) for c in comments],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_instagram_full(
    username: str,
    include_stories: bool = True,
    include_carousels: bool = True,
    include_comments: bool = True,
    max_videos: int = 50,
    max_comments_per_post: int = 50,
) -> dict[str, Any]:
    """Coleta TUDO de um perfil do Instagram.

    Scraping completo: perfil, videos/reels, stories, carrosseis, comentarios, audios.

    Args:
        username: Username do perfil (sem @)
        include_stories: Coletar stories ativos
        include_carousels: Coletar carrosseis
        include_comments: Coletar comentarios dos posts
        max_videos: Maximo de videos/reels
        max_comments_per_post: Comentarios por post

    Returns:
        FullScrapingResult com todos os dados
    """
    def _run() -> dict[str, Any]:
        result = instagram_scraper.scrape_full_profile(
            username=username,
            include_stories=include_stories,
            include_carousels=include_carousels,
            include_comments=include_comments,
            max_videos=max_videos,
            max_comments_per_post=max_comments_per_post,
        )

        return {
            "username": username,
            "profile": _profile_to_dict(result.profile) if result.profile else None,
            "totals": {
                "posts": result.total_posts,
                "videos": result.total_videos,
                "stories": result.total_stories,
                "carousels": result.total_carousels,
                "comments": result.total_comments,
                "audios": len(result.audios),
            },
            "videos": result.videos[:10],  # Limita para nao estourar resposta
            "stories": [_story_to_dict(s) for s in result.stories],
            "carousels": [_carousel_to_dict(c) for c in result.carousels],
            "comments_sample": [_comment_to_dict(c) for c in result.comments[:20]],
            "audios": [
                {
                    "audio_id": a.audio_id,
                    "title": a.title,
                    "artist_name": a.artist_name,
                    "reels_count": a.reels_count,
                    "is_trending": a.is_trending,
                }
                for a in result.audios
            ],
            "cost_usd": result.cost_usd,
            "duration_seconds": result.duration_seconds,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_instagram_hashtag(
    hashtag: str,
    max_posts: int = 100,
) -> dict[str, Any]:
    """Coleta posts de uma hashtag do Instagram.

    Retorna videos e carrosseis da hashtag.

    Args:
        hashtag: Hashtag sem #
        max_posts: Maximo de posts

    Returns:
        Lista de posts da hashtag
    """
    def _run() -> dict[str, Any]:
        result = instagram_scraper.scrape_hashtag(hashtag, max_posts)
        return {
            "hashtag": hashtag,
            "total_posts": result.total_posts,
            "videos": result.total_videos,
            "carousels": result.total_carousels,
            "video_list": result.videos[:20],  # Limita
            "carousel_list": [_carousel_to_dict(c) for c in result.carousels[:10]],
            "cost_usd": result.cost_usd,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def estimate_instagram_scraping_cost(
    profiles: int = 1,
    videos_per_profile: int = 50,
    include_stories: bool = True,
    include_comments: bool = True,
    comments_per_post: int = 50,
) -> dict[str, Any]:
    """Estima custo de scraping do Instagram.

    Retorna breakdown detalhado de custos por componente.

    Args:
        profiles: Numero de perfis
        videos_per_profile: Videos por perfil
        include_stories: Incluir stories
        include_comments: Incluir comentarios
        comments_per_post: Comentarios por post

    Returns:
        Breakdown de custos em USD
    """
    return instagram_scraper.estimate_cost(
        profiles=profiles,
        videos_per_profile=videos_per_profile,
        include_stories=include_stories,
        include_comments=include_comments,
        comments_per_post=comments_per_post,
    )


# ============================================================================
# TIKTOK SCRAPING TOOLS
# ============================================================================

from src.tools.tiktok_scraper import tiktok_scraper


def _tiktok_profile_to_dict(profile) -> dict[str, Any]:
    """Serializa TikTokProfile para dict."""
    return {
        "user_id": profile.user_id,
        "username": profile.username,
        "nickname": profile.nickname,
        "bio": profile.bio,
        "profile_pic_url": profile.profile_pic_url,
        "follower_count": profile.follower_count,
        "following_count": profile.following_count,
        "likes_count": profile.likes_count,
        "video_count": profile.video_count,
        "is_verified": profile.is_verified,
        "is_private": profile.is_private,
        "avg_views": profile.avg_views,
        "avg_likes": profile.avg_likes,
        "engagement_rate": profile.engagement_rate,
    }


def _tiktok_video_to_dict(video) -> dict[str, Any]:
    """Serializa TikTokVideo para dict."""
    return {
        "video_id": video.video_id,
        "author_username": video.author_username,
        "video_url": video.video_url,
        "download_url": video.download_url,
        "cover_url": video.cover_url,
        "title": video.title,
        "description": video.description,
        "duration_seconds": video.duration_seconds,
        "view_count": video.view_count,
        "like_count": video.like_count,
        "comment_count": video.comment_count,
        "share_count": video.share_count,
        "play_count": video.play_count,
        "hashtags": video.hashtags,
        "mentions": video.mentions,
        "sound_id": video.sound_id,
        "sound_name": video.sound_name,
        "sound_author": video.sound_author,
        "is_ad": video.is_ad,
        "is_duet": video.is_duet,
        "is_stitch": video.is_stitch,
        "created_at": video.created_at.isoformat() if video.created_at else None,
    }


def _tiktok_sound_to_dict(sound) -> dict[str, Any]:
    """Serializa TikTokSound para dict."""
    return {
        "sound_id": sound.sound_id,
        "title": sound.title,
        "author": sound.author,
        "author_name": sound.author_name,
        "duration_seconds": sound.duration_seconds,
        "video_count": sound.video_count,
        "play_url": sound.play_url,
        "cover_url": sound.cover_url,
        "is_original": sound.is_original,
    }


@mcp.tool()
async def scrape_tiktok_profile(username: str) -> dict[str, Any]:
    """Coleta dados completos de um perfil do TikTok.

    Retorna: followers, following, likes, videos, bio, verificacao, etc.

    Args:
        username: Username do perfil (sem @)

    Returns:
        Dados completos do perfil
    """
    def _run() -> dict[str, Any]:
        profile = tiktok_scraper.scrape_profile(username)
        return _tiktok_profile_to_dict(profile)

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_tiktok_videos(
    username: str,
    max_videos: int = 50,
    min_views: int = 0,
) -> dict[str, Any]:
    """Coleta videos de um perfil do TikTok.

    Args:
        username: Username do perfil (sem @)
        max_videos: Maximo de videos
        min_views: Filtro minimo de views

    Returns:
        Lista de videos com metricas
    """
    def _run() -> dict[str, Any]:
        videos = tiktok_scraper.scrape_videos(username, max_videos, min_views)
        return {
            "username": username,
            "video_count": len(videos),
            "videos": [_tiktok_video_to_dict(v) for v in videos],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_tiktok_full(
    username: str,
    max_videos: int = 50,
    min_views: int = 0,
) -> dict[str, Any]:
    """Coleta TUDO de um perfil do TikTok.

    Scraping completo: perfil, todos os videos, sons usados, metricas.

    Args:
        username: Username do perfil (sem @)
        max_videos: Maximo de videos
        min_views: Filtro minimo de views

    Returns:
        Resultado completo com perfil e videos
    """
    def _run() -> dict[str, Any]:
        result = tiktok_scraper.scrape_full_profile(username, max_videos, min_views)
        return {
            "username": username,
            "profile": _tiktok_profile_to_dict(result.profile) if result.profile else None,
            "totals": {
                "videos": result.total_videos,
                "likes": result.total_likes,
                "comments": result.total_comments,
                "shares": result.total_shares,
            },
            "top_sounds": [_tiktok_sound_to_dict(s) for s in result.top_sounds],
            "top_hashtags": result.top_hashtags,
            "videos": [_tiktok_video_to_dict(v) for v in result.videos[:20]],  # Limita
            "duration_seconds": result.duration_seconds,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_tiktok_hashtag(
    hashtag: str,
    max_videos: int = 100,
) -> dict[str, Any]:
    """Coleta videos de uma hashtag do TikTok.

    Args:
        hashtag: Hashtag sem #
        max_videos: Maximo de videos

    Returns:
        Lista de videos da hashtag
    """
    def _run() -> dict[str, Any]:
        result = tiktok_scraper.scrape_hashtag(hashtag, max_videos)
        return {
            "hashtag": hashtag,
            "video_count": len(result.videos),
            "videos": [_tiktok_video_to_dict(v) for v in result.videos[:20]],
            "top_sounds": [_tiktok_sound_to_dict(s) for s in result.top_sounds],
            "top_hashtags": result.top_hashtags,
            "duration_seconds": result.duration_seconds,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_trending_sounds(limit: int = 30) -> dict[str, Any]:
    """Coleta sons/musicas trending no TikTok.

    Args:
        limit: Maximo de sons

    Returns:
        Lista de sons trending
    """
    def _run() -> dict[str, Any]:
        sounds = tiktok_scraper.scrape_trending_sounds(limit)
        return {
            "sound_count": len(sounds),
            "sounds": [_tiktok_sound_to_dict(s) for s in sounds],
        }

    return await _run_in_thread(_run)


# ============================================================================
# YOUTUBE SCRAPING TOOLS
# ============================================================================

from src.tools.youtube_scraper import youtube_scraper


def _youtube_channel_to_dict(channel) -> dict[str, Any]:
    """Serializa YouTubeChannel para dict."""
    return {
        "channel_id": channel.channel_id,
        "username": channel.username,
        "title": channel.title,
        "description": channel.description,
        "thumbnail_url": channel.thumbnail_url,
        "banner_url": channel.banner_url,
        "subscriber_count": channel.subscriber_count,
        "video_count": channel.video_count,
        "view_count": channel.view_count,
        "is_verified": channel.is_verified,
        "avg_views": channel.avg_views,
        "avg_likes": channel.avg_likes,
        "engagement_rate": channel.engagement_rate,
    }


def _youtube_video_to_dict(video) -> dict[str, Any]:
    """Serializa YouTubeVideo para dict."""
    return {
        "video_id": video.video_id,
        "channel_id": video.channel_id,
        "channel_title": video.channel_title,
        "video_url": video.video_url,
        "thumbnail_url": video.thumbnail_url,
        "title": video.title,
        "description": video.description[:200] if video.description else None,
        "tags": video.tags[:10] if video.tags else [],
        "hashtags": video.hashtags,
        "is_short": video.is_short,
        "view_count": video.view_count,
        "like_count": video.like_count,
        "comment_count": video.comment_count,
        "duration_seconds": video.duration_seconds,
        "category_id": video.category_id,
        "category_name": video.category_name,
        "published_at": video.published_at.isoformat() if video.published_at else None,
    }


@mcp.tool()
async def scrape_youtube_channel(channel_id: str) -> dict[str, Any]:
    """Coleta dados de um canal do YouTube.

    Args:
        channel_id: ID do canal ou @username

    Returns:
        Dados do canal
    """
    def _run() -> dict[str, Any]:
        channel = youtube_scraper.scrape_channel(channel_id)
        return _youtube_channel_to_dict(channel)

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_youtube_shorts(
    channel_id: str,
    max_shorts: int = 50,
    min_views: int = 0,
) -> dict[str, Any]:
    """Coleta Shorts de um canal do YouTube.

    Args:
        channel_id: ID do canal ou @username
        max_shorts: Maximo de shorts
        min_views: Filtro minimo de views

    Returns:
        Lista de shorts
    """
    def _run() -> dict[str, Any]:
        shorts = youtube_scraper.scrape_shorts(channel_id, max_shorts, min_views)
        return {
            "channel_id": channel_id,
            "short_count": len(shorts),
            "shorts": [_youtube_video_to_dict(s) for s in shorts],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_youtube_videos(
    channel_id: str,
    max_videos: int = 50,
    min_views: int = 0,
) -> dict[str, Any]:
    """Coleta videos de um canal do YouTube.

    Args:
        channel_id: ID do canal ou @username
        max_videos: Maximo de videos
        min_views: Filtro minimo de views

    Returns:
        Lista de videos
    """
    def _run() -> dict[str, Any]:
        videos = youtube_scraper.scrape_videos(channel_id, max_videos, min_views)
        return {
            "channel_id": channel_id,
            "video_count": len(videos),
            "videos": [_youtube_video_to_dict(v) for v in videos],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_youtube_full(
    channel_id: str,
    max_videos: int = 50,
    max_shorts: int = 50,
) -> dict[str, Any]:
    """Coleta TUDO de um canal do YouTube.

    Scraping completo: canal, videos, shorts, metricas.

    Args:
        channel_id: ID do canal ou @username
        max_videos: Maximo de videos
        max_shorts: Maximo de shorts

    Returns:
        Resultado completo
    """
    def _run() -> dict[str, Any]:
        result = youtube_scraper.scrape_full_channel(channel_id, max_videos, max_shorts)
        return {
            "channel_id": channel_id,
            "channel": _youtube_channel_to_dict(result.channel) if result.channel else None,
            "totals": {
                "videos": result.total_videos,
                "shorts": result.total_shorts,
            },
            "videos": [_youtube_video_to_dict(v) for v in result.videos[:20]],
            "shorts": [_youtube_video_to_dict(s) for s in result.shorts[:20]],
            "duration_seconds": result.duration_seconds,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_trending_shorts(country: str = "BR", limit: int = 50) -> dict[str, Any]:
    """Coleta Shorts trending do YouTube.

    Args:
        country: Codigo do pais (BR, US, etc)
        limit: Maximo de shorts

    Returns:
        Lista de shorts trending
    """
    def _run() -> dict[str, Any]:
        shorts = youtube_scraper.scrape_trending_shorts(country, limit)
        return {
            "country": country,
            "short_count": len(shorts),
            "shorts": [_youtube_video_to_dict(s) for s in shorts],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def scrape_youtube_search(
    query: str,
    max_results: int = 50,
    shorts_only: bool = False,
) -> dict[str, Any]:
    """Busca videos no YouTube.

    Args:
        query: Termo de busca
        max_results: Maximo de resultados
        shorts_only: Apenas Shorts

    Returns:
        Lista de videos
    """
    def _run() -> dict[str, Any]:
        videos = youtube_scraper.scrape_search(query, max_results, shorts_only)
        return {
            "query": query,
            "shorts_only": shorts_only,
            "video_count": len(videos),
            "videos": [_youtube_video_to_dict(v) for v in videos],
        }

    return await _run_in_thread(_run)


# ============================================================================
# TREND HUNTER TOOLS
# ============================================================================

from src.agents.trend_hunter_agent import get_trend_hunter
from src.db.models.trends import Platform, TrendType, TrendStatus


def _trend_to_dict(trend) -> dict[str, Any]:
    """Serializa Trend/DetectedTrend para dict."""
    # Detecta se e DetectedTrend (dataclass) ou Trend (ORM)
    if hasattr(trend, 'id'):
        # ORM Trend
        return {
            "id": trend.id,
            "name": trend.name,
            "trend_type": trend.trend_type.value if hasattr(trend.trend_type, 'value') else str(trend.trend_type),
            "platform": trend.platform.value if hasattr(trend.platform, 'value') else str(trend.platform),
            "description": trend.description,
            "current_score": float(trend.current_score) if trend.current_score else None,
            "velocity": float(trend.velocity) if trend.velocity else None,
            "volume": trend.volume,
            "status": trend.status.value if hasattr(trend.status, 'value') else str(trend.status),
            "is_actionable": trend.is_actionable,
            "external_id": trend.external_id,
            "external_url": trend.external_url,
            "related_hashtags": trend.related_hashtags or [],
            "example_videos": trend.example_videos or [],
            "first_detected_at": trend.first_detected_at.isoformat() if trend.first_detected_at else None,
            "last_updated_at": trend.last_updated_at.isoformat() if trend.last_updated_at else None,
        }
    else:
        # DetectedTrend (dataclass)
        return {
            "name": trend.name,
            "trend_type": trend.trend_type.value if hasattr(trend.trend_type, 'value') else str(trend.trend_type),
            "platform": trend.platform.value if hasattr(trend.platform, 'value') else str(trend.platform),
            "description": trend.description,
            "score": trend.score,
            "velocity": trend.velocity,
            "volume": trend.volume,
            "external_id": trend.external_id,
            "external_url": trend.external_url,
            "related_hashtags": trend.related_hashtags,
            "example_videos": trend.example_videos,
        }


@mcp.tool()
async def hunt_trends(
    platforms: str = "instagram,tiktok,youtube",
    limit_per_platform: int = 20,
) -> dict[str, Any]:
    """Detecta tendencias em tempo real em multiplas plataformas.

    Analisa Instagram, TikTok e YouTube para encontrar:
    - Audios/sons virais
    - Hashtags em alta
    - Formatos de conteudo trending
    - Topicos emergentes

    Args:
        platforms: Plataformas separadas por virgula (instagram,tiktok,youtube)
        limit_per_platform: Limite de tendencias por plataforma

    Returns:
        TrendHunterResult com tendencias detectadas
    """
    def _run() -> dict[str, Any]:
        hunter = get_trend_hunter()

        # Parseia plataformas
        platform_list = []
        for p in platforms.split(","):
            p = p.strip().lower()
            if p == "instagram":
                platform_list.append(Platform.INSTAGRAM)
            elif p == "tiktok":
                platform_list.append(Platform.TIKTOK)
            elif p == "youtube":
                platform_list.append(Platform.YOUTUBE)

        result = hunter.hunt_all(
            platforms=platform_list if platform_list else None,
            limit_per_platform=limit_per_platform,
        )

        return {
            "run_id": result.run_id,
            "trends_detected": result.trends_detected,
            "trends_by_type": result.trends_by_type,
            "trends_by_platform": result.trends_by_platform,
            "top_trends": [_trend_to_dict(t) for t in result.top_trends],
            "duration_seconds": result.duration_seconds,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def get_actionable_trends(
    platform: str = "",
    trend_type: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Retorna tendencias acionaveis (que podem ser replicadas).

    Tendencias acionaveis sao aquelas em status EMERGING, RISING ou PEAK
    que foram marcadas como replicaveis.

    Args:
        platform: Filtrar por plataforma (instagram, tiktok, youtube, ou vazio para todas)
        trend_type: Filtrar por tipo (audio, hashtag, format, topic, challenge, ou vazio para todos)
        limit: Maximo de resultados

    Returns:
        Lista de tendencias acionaveis do banco
    """
    def _run() -> dict[str, Any]:
        hunter = get_trend_hunter()

        # Parseia plataforma
        plat = None
        if platform:
            p = platform.strip().lower()
            if p == "instagram":
                plat = Platform.INSTAGRAM
            elif p == "tiktok":
                plat = Platform.TIKTOK
            elif p == "youtube":
                plat = Platform.YOUTUBE

        # Parseia tipo
        ttype = None
        if trend_type:
            t = trend_type.strip().lower()
            if t == "audio":
                ttype = TrendType.AUDIO
            elif t == "hashtag":
                ttype = TrendType.HASHTAG
            elif t == "format":
                ttype = TrendType.FORMAT
            elif t == "topic":
                ttype = TrendType.TOPIC
            elif t == "challenge":
                ttype = TrendType.CHALLENGE

        trends = hunter.get_actionable_trends(
            platform=plat,
            trend_type=ttype,
            limit=limit,
        )

        return {
            "filters": {
                "platform": platform or "all",
                "trend_type": trend_type or "all",
            },
            "count": len(trends),
            "trends": [_trend_to_dict(t) for t in trends],
        }

    return await _run_in_thread(_run)


# ============================================================================
# CONTENT SCHEDULER TOOLS
# ============================================================================

from src.agents.scheduler_agent import get_scheduler, ContentStatus


def _content_queue_to_dict(content) -> dict[str, Any]:
    """Serializa ContentQueue para dict."""
    return {
        "id": content.id,
        "title": content.title,
        "video_path": content.video_path,
        "caption": content.caption,
        "hashtags": content.hashtags,
        "target_platforms": content.target_platforms,
        "scheduled_at": content.scheduled_at.isoformat() if content.scheduled_at else None,
        "optimal_time_used": content.optimal_time_used,
        "priority": content.priority,
        "status": content.status.value if hasattr(content.status, 'value') else str(content.status),
        "published_at": content.published_at.isoformat() if content.published_at else None,
        "published_urls": content.published_urls,
        "error_message": content.error_message,
        "retry_count": content.retry_count,
        "strategy_id": content.strategy_id,
        "production_id": content.production_id,
        "trend_id": content.trend_id,
        "created_at": content.created_at.isoformat() if content.created_at else None,
    }


@mcp.tool()
async def schedule_content(
    title: str,
    video_path: str,
    platforms: str = "instagram",
    caption: str = "",
    hashtags: str = "",
    scheduled_at: str = "",
    use_optimal_time: bool = True,
    priority: int = 1,
) -> dict[str, Any]:
    """Agenda conteudo para publicacao em multiplas plataformas.

    Usa horarios otimos baseados em estudos de engajamento por plataforma.

    Args:
        title: Titulo do conteudo
        video_path: Caminho do video no MinIO
        platforms: Plataformas separadas por virgula (instagram,tiktok,youtube)
        caption: Legenda do post
        hashtags: Hashtags separadas por virgula
        scheduled_at: Data/hora no formato ISO (YYYY-MM-DDTHH:MM:SS) ou vazio para automatico
        use_optimal_time: Usar horario otimo se scheduled_at nao fornecido
        priority: Prioridade 1-5 (5 = mais alta)

    Returns:
        ScheduleResult com ID e horario agendado
    """
    def _run() -> dict[str, Any]:
        scheduler = get_scheduler()

        # Parseia plataformas
        platform_list = []
        for p in platforms.split(","):
            p = p.strip().lower()
            if p == "instagram":
                platform_list.append(Platform.INSTAGRAM)
            elif p == "tiktok":
                platform_list.append(Platform.TIKTOK)
            elif p == "youtube":
                platform_list.append(Platform.YOUTUBE)

        if not platform_list:
            platform_list = [Platform.INSTAGRAM]

        # Parseia hashtags
        hashtag_list = [h.strip() for h in hashtags.split(",") if h.strip()] if hashtags else []

        # Parseia data
        scheduled_datetime = None
        if scheduled_at:
            from datetime import datetime
            scheduled_datetime = datetime.fromisoformat(scheduled_at)

        result = scheduler.schedule_content(
            title=title,
            video_path=video_path,
            platforms=platform_list,
            caption=caption if caption else None,
            hashtags=hashtag_list if hashtag_list else None,
            scheduled_at=scheduled_datetime,
            use_optimal_time=use_optimal_time,
            priority=priority,
        )

        return {
            "content_id": result.content_id,
            "scheduled_at": result.scheduled_at.isoformat(),
            "platforms": result.platforms,
            "optimal_time_used": result.optimal_time_used,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def list_scheduled_content(
    status: str = "",
    platform: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Lista conteudos agendados.

    Args:
        status: Filtrar por status (scheduled, processing, ready, published, failed, cancelled)
        platform: Filtrar por plataforma (instagram, tiktok, youtube)
        limit: Maximo de resultados

    Returns:
        Lista de conteudos agendados
    """
    def _run() -> dict[str, Any]:
        scheduler = get_scheduler()

        # Parseia status
        content_status = None
        if status:
            s = status.strip().lower()
            if s == "scheduled":
                content_status = ContentStatus.SCHEDULED
            elif s == "processing":
                content_status = ContentStatus.PROCESSING
            elif s == "ready":
                content_status = ContentStatus.READY
            elif s == "published":
                content_status = ContentStatus.PUBLISHED
            elif s == "failed":
                content_status = ContentStatus.FAILED
            elif s == "cancelled":
                content_status = ContentStatus.CANCELLED

        # Parseia plataforma
        plat = None
        if platform:
            p = platform.strip().lower()
            if p == "instagram":
                plat = Platform.INSTAGRAM
            elif p == "tiktok":
                plat = Platform.TIKTOK
            elif p == "youtube":
                plat = Platform.YOUTUBE

        contents = scheduler.list_scheduled(
            status=content_status,
            platform=plat,
            limit=limit,
        )

        return {
            "filters": {
                "status": status or "all",
                "platform": platform or "all",
            },
            "count": len(contents),
            "contents": [_content_queue_to_dict(c) for c in contents],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def get_optimal_times(
    platform: str = "instagram",
    days_ahead: int = 7,
) -> dict[str, Any]:
    """Retorna melhores horarios para publicacao nos proximos dias.

    Baseado em estudos de engajamento por plataforma e dia da semana.

    Args:
        platform: Plataforma (instagram, tiktok, youtube)
        days_ahead: Quantos dias a frente mostrar

    Returns:
        Lista de horarios otimos por dia
    """
    def _run() -> dict[str, Any]:
        scheduler = get_scheduler()

        # Parseia plataforma
        plat = Platform.INSTAGRAM
        p = platform.strip().lower()
        if p == "tiktok":
            plat = Platform.TIKTOK
        elif p == "youtube":
            plat = Platform.YOUTUBE

        times = scheduler.get_optimal_times(plat, days_ahead)

        return {
            "platform": platform,
            "days_ahead": days_ahead,
            "optimal_times": times,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def publish_now(content_id: int) -> dict[str, Any]:
    """Publica conteudo imediatamente (ignora agendamento).

    Args:
        content_id: ID do conteudo na fila

    Returns:
        PublishResult com status e URLs publicadas
    """
    def _run() -> dict[str, Any]:
        scheduler = get_scheduler()
        result = scheduler.publish_content(content_id)

        return {
            "content_id": result.content_id,
            "success": result.success,
            "published_urls": result.published_urls,
            "error": result.error,
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def get_due_content() -> dict[str, Any]:
    """Retorna conteudos prontos para publicar (horario passou).

    Util para automatizar publicacao de conteudos agendados.

    Returns:
        Lista de conteudos que devem ser publicados
    """
    def _run() -> dict[str, Any]:
        scheduler = get_scheduler()
        contents = scheduler.get_due_content()

        return {
            "count": len(contents),
            "contents": [_content_queue_to_dict(c) for c in contents],
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def cancel_scheduled_content(content_id: int) -> dict[str, Any]:
    """Cancela conteudo agendado.

    Args:
        content_id: ID do conteudo

    Returns:
        Status do cancelamento
    """
    def _run() -> dict[str, Any]:
        scheduler = get_scheduler()
        success = scheduler.cancel_scheduled(content_id)

        return {
            "content_id": content_id,
            "success": success,
            "status": "cancelled" if success else "failed",
        }

    return await _run_in_thread(_run)


@mcp.tool()
async def reschedule_content(content_id: int, new_time: str) -> dict[str, Any]:
    """Reagenda conteudo para nova data/hora.

    Args:
        content_id: ID do conteudo
        new_time: Nova data/hora no formato ISO (YYYY-MM-DDTHH:MM:SS)

    Returns:
        Status do reagendamento
    """
    def _run() -> dict[str, Any]:
        scheduler = get_scheduler()
        from datetime import datetime
        new_datetime = datetime.fromisoformat(new_time)

        success = scheduler.reschedule(content_id, new_datetime)

        return {
            "content_id": content_id,
            "success": success,
            "new_time": new_time if success else None,
            "status": "rescheduled" if success else "failed",
        }

    return await _run_in_thread(_run)


# === HTTP REST API para integracao com SparkOne ===
# O FastMCP usa SSE, mas SparkOne precisa de endpoints HTTP REST

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Modelos de request
class IngestVideoRequest(BaseModel):
    url: str
    creator: str
    niche: str = ""

class GetCreatorTranscriptionsRequest(BaseModel):
    creator: str

class SearchTranscriptionsRequest(BaseModel):
    query: str
    limit: int = 20

class TranscribeVideoRequest(BaseModel):
    video_id: int
    language: str = "pt"

class FullPipelineRequest(BaseModel):
    video_id: int

class SemanticAnalysisRequest(BaseModel):
    video_id: int

# Cria app FastAPI separada para endpoints REST
rest_app = FastAPI(title="ViralForge REST API", version="2.1.0")

@rest_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "viralforge-mcp"}

@rest_app.post("/tools/list_creators")
async def api_list_creators():
    """Lista criadores via HTTP."""
    try:
        return await list_creators()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rest_app.post("/tools/get_creator_transcriptions")
async def api_get_creator_transcriptions(request: GetCreatorTranscriptionsRequest):
    """Retorna transcricoes de um criador via HTTP."""
    try:
        return await get_creator_transcriptions(request.creator)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rest_app.post("/tools/search_transcriptions")
async def api_search_transcriptions(request: SearchTranscriptionsRequest):
    """Busca em transcricoes via HTTP."""
    try:
        return await search_transcriptions(request.query, request.limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rest_app.post("/tools/ingest_video_from_url")
async def api_ingest_video(request: IngestVideoRequest):
    """Baixa e registra video via HTTP."""
    try:
        return await ingest_video_from_url(request.url, request.creator, request.niche)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rest_app.post("/tools/transcribe_video")
async def api_transcribe_video(request: TranscribeVideoRequest):
    """Transcreve video via HTTP."""
    try:
        return await transcribe_video(request.video_id, request.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rest_app.post("/tools/full_pipeline")
async def api_full_pipeline(request: FullPipelineRequest):
    """Executa pipeline completo via HTTP."""
    try:
        return await full_pipeline(request.video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rest_app.post("/tools/get_semantic_analysis")
async def api_get_semantic_analysis(request: SemanticAnalysisRequest):
    """Retorna analise semantica via HTTP."""
    try:
        return await get_semantic_analysis(request.video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_server(transport: str = "sse") -> None:
    """Run the MCP server with specified transport.

    Args:
        transport: Transport protocol - "sse" for HTTP/SSE or "stdio" for stdio.
    """
    mcp.run(transport=transport)


def run_rest_server(host: str = "0.0.0.0", port: int = 8001) -> None:
    """Run the REST API server for SparkOne integration.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn
    uvicorn.run(rest_app, host=host, port=port)


if __name__ == "__main__":
    import sys

    mode = os.getenv("MCP_MODE", "mcp")

    if mode == "rest" or (len(sys.argv) > 1 and sys.argv[1] == "rest"):
        # Modo REST para integracao com SparkOne
        host = os.getenv("REST_HOST", "0.0.0.0")
        port = int(os.getenv("REST_PORT", "8001"))
        print(f"Starting ViralForge REST API Server on {host}:{port}")
        run_rest_server(host, port)
    else:
        # Modo MCP padrao (SSE)
        transport = os.getenv("MCP_TRANSPORT", "sse")
        run_server(transport=transport)
