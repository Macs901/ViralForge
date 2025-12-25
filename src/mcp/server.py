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
from src.tools import budget_tools, scraping_tools, storage_tools, whisper_tools
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


# === Tools de Integracao Multi-Plataforma (MacsMorpheus) ===


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

    Util para o MacsMorpheus listar criadores disponiveis para referencia.
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

    Util para o MacsMorpheus criar roteiros baseados em criadores especificos.

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

    Util para o MacsMorpheus encontrar referencias sobre temas especificos.

    Args:
        query: Texto a buscar nas transcricoes
        limit: Maximo de resultados (default: 20)

    Returns:
        Lista de matches com contexto, video_id, creator, etc.
    """
    return await _run_in_thread(_search_transcriptions_sync, query, limit)


# === HTTP REST API para integracao com MacsMorpheus ===
# O FastMCP usa SSE, mas MacsMorpheus precisa de endpoints HTTP REST

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
    """Run the REST API server for MacsMorpheus integration.

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
        # Modo REST para integracao com MacsMorpheus
        host = os.getenv("REST_HOST", "0.0.0.0")
        port = int(os.getenv("REST_PORT", "8001"))
        print(f"Starting ViralForge REST API Server on {host}:{port}")
        run_rest_server(host, port)
    else:
        # Modo MCP padrao (SSE)
        transport = os.getenv("MCP_TRANSPORT", "sse")
        run_server(transport=transport)
