"""Publishing MCP Tools - Ferramentas para publicacao em plataformas."""

from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.publishers.base import ContentToPublish
from src.publishers.instagram_publisher import get_instagram_publisher
from src.publishers.tiktok_publisher import get_tiktok_publisher
from src.publishers.youtube_publisher import get_youtube_publisher

# MCP Server para Publishing Tools
publishing_mcp = FastMCP("publishing-tools")


@publishing_mcp.tool()
def publish_to_instagram(
    video_path: str,
    caption: str,
    hashtags: Optional[list[str]] = None,
    thumbnail_path: Optional[str] = None,
) -> dict:
    """Publica um Reel no Instagram.

    Args:
        video_path: Caminho do arquivo de video
        caption: Caption do post
        hashtags: Lista de hashtags (opcional)
        thumbnail_path: Caminho da thumbnail (opcional)

    Returns:
        Resultado da publicacao
    """
    publisher = get_instagram_publisher()

    content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        hashtags=hashtags or [],
        thumbnail_path=thumbnail_path,
    )

    result = publisher.publish(content)

    return {
        "success": result.status.value in ["published", "pending", "scheduled"],
        "status": result.status.value,
        "platform": result.platform,
        "post_id": result.post_id,
        "post_url": result.post_url,
        "error": result.error,
        "extra_data": result.extra_data,
    }


@publishing_mcp.tool()
def publish_to_tiktok(
    video_path: str,
    caption: str,
    hashtags: Optional[list[str]] = None,
) -> dict:
    """Publica um video no TikTok.

    Args:
        video_path: Caminho do arquivo de video
        caption: Caption do post
        hashtags: Lista de hashtags (opcional)

    Returns:
        Resultado da publicacao
    """
    publisher = get_tiktok_publisher()

    content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        hashtags=hashtags or [],
    )

    result = publisher.publish(content)

    return {
        "success": result.status.value in ["published", "pending", "scheduled"],
        "status": result.status.value,
        "platform": result.platform,
        "post_id": result.post_id,
        "post_url": result.post_url,
        "error": result.error,
        "extra_data": result.extra_data,
    }


@publishing_mcp.tool()
def publish_to_youtube(
    video_path: str,
    title: str,
    description: str,
    hashtags: Optional[list[str]] = None,
    thumbnail_path: Optional[str] = None,
) -> dict:
    """Publica um Short no YouTube.

    Args:
        video_path: Caminho do arquivo de video
        title: Titulo do video (max 100 chars, #Shorts sera adicionado)
        description: Descricao do video
        hashtags: Lista de hashtags/tags (opcional)
        thumbnail_path: Caminho da thumbnail (opcional)

    Returns:
        Resultado da publicacao
    """
    publisher = get_youtube_publisher()

    content = ContentToPublish(
        video_path=video_path,
        caption=description,
        title=title,
        description=description,
        hashtags=hashtags or [],
        thumbnail_path=thumbnail_path,
    )

    result = publisher.publish(content)

    return {
        "success": result.status.value in ["published", "pending", "scheduled"],
        "status": result.status.value,
        "platform": result.platform,
        "post_id": result.post_id,
        "post_url": result.post_url,
        "error": result.error,
        "extra_data": result.extra_data,
    }


@publishing_mcp.tool()
def publish_to_all_platforms(
    video_path: str,
    caption: str,
    hashtags: Optional[list[str]] = None,
    youtube_title: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
) -> dict:
    """Publica em todas as plataformas simultaneamente.

    Args:
        video_path: Caminho do arquivo de video
        caption: Caption base (usado em todas as plataformas)
        hashtags: Lista de hashtags
        youtube_title: Titulo especifico para YouTube (opcional)
        thumbnail_path: Caminho da thumbnail

    Returns:
        Resultados de cada plataforma
    """
    results = {}

    # Instagram
    ig_publisher = get_instagram_publisher()
    ig_content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        hashtags=hashtags or [],
        thumbnail_path=thumbnail_path,
    )
    ig_result = ig_publisher.publish(ig_content)
    results["instagram"] = {
        "status": ig_result.status.value,
        "post_id": ig_result.post_id,
        "post_url": ig_result.post_url,
        "error": ig_result.error,
    }

    # TikTok
    tt_publisher = get_tiktok_publisher()
    tt_content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        hashtags=hashtags or [],
    )
    tt_result = tt_publisher.publish(tt_content)
    results["tiktok"] = {
        "status": tt_result.status.value,
        "post_id": tt_result.post_id,
        "post_url": tt_result.post_url,
        "error": tt_result.error,
    }

    # YouTube
    yt_publisher = get_youtube_publisher()
    yt_content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        title=youtube_title or caption[:100],
        description=caption,
        hashtags=hashtags or [],
        thumbnail_path=thumbnail_path,
    )
    yt_result = yt_publisher.publish(yt_content)
    results["youtube"] = {
        "status": yt_result.status.value,
        "post_id": yt_result.post_id,
        "post_url": yt_result.post_url,
        "error": yt_result.error,
    }

    # Resumo
    success_count = sum(
        1 for r in results.values()
        if r["status"] in ["published", "pending", "scheduled"]
    )

    return {
        "success": success_count > 0,
        "published_count": success_count,
        "total_platforms": 3,
        "results": results,
    }


@publishing_mcp.tool()
def schedule_publication(
    platform: str,
    video_path: str,
    caption: str,
    scheduled_at: str,
    hashtags: Optional[list[str]] = None,
    title: Optional[str] = None,
) -> dict:
    """Agenda publicacao para uma data/hora especifica.

    Args:
        platform: Plataforma (instagram, tiktok, youtube)
        video_path: Caminho do arquivo de video
        caption: Caption do post
        scheduled_at: Data/hora para publicar (ISO format: 2025-01-15T14:30:00)
        hashtags: Lista de hashtags
        title: Titulo (obrigatorio para YouTube)

    Returns:
        Resultado do agendamento
    """
    try:
        publish_at = datetime.fromisoformat(scheduled_at)
    except ValueError:
        return {"error": f"Data invalida: {scheduled_at}. Use formato ISO: 2025-01-15T14:30:00"}

    if publish_at <= datetime.now():
        return {"error": "Data de agendamento deve ser no futuro"}

    content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        hashtags=hashtags or [],
        title=title,
    )

    if platform == "instagram":
        publisher = get_instagram_publisher()
    elif platform == "tiktok":
        publisher = get_tiktok_publisher()
    elif platform == "youtube":
        publisher = get_youtube_publisher()
        content.description = caption
    else:
        return {"error": f"Plataforma invalida: {platform}"}

    result = publisher.schedule(content, publish_at)

    return {
        "success": result.status.value in ["scheduled", "pending"],
        "status": result.status.value,
        "platform": result.platform,
        "scheduled_at": result.scheduled_at.isoformat() if result.scheduled_at else scheduled_at,
        "post_id": result.post_id,
        "error": result.error,
        "extra_data": result.extra_data,
    }


@publishing_mcp.tool()
def export_for_manual_publish(
    video_path: str,
    caption: str,
    platforms: list[str],
    hashtags: Optional[list[str]] = None,
    title: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> dict:
    """Exporta conteudo para publicacao manual.

    Cria pasta com todos os arquivos necessarios para cada plataforma.

    Args:
        video_path: Caminho do arquivo de video
        caption: Caption do post
        platforms: Lista de plataformas (instagram, tiktok, youtube)
        hashtags: Lista de hashtags
        title: Titulo (para YouTube)
        output_dir: Diretorio de saida (opcional)

    Returns:
        Caminhos dos arquivos exportados
    """
    import os

    output_dir = output_dir or os.getenv("VIRALFORGE_EXPORT_DIR", "/tmp/viralforge_exports")

    content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        hashtags=hashtags or [],
        title=title,
    )

    exports = {}

    for platform in platforms:
        if platform == "instagram":
            publisher = get_instagram_publisher()
        elif platform == "tiktok":
            publisher = get_tiktok_publisher()
        elif platform == "youtube":
            publisher = get_youtube_publisher()
            content.description = caption
        else:
            exports[platform] = {"error": f"Plataforma invalida: {platform}"}
            continue

        result = publisher.prepare_export(content, output_dir)
        exports[platform] = result

    return {
        "success": True,
        "exports": exports,
        "output_dir": output_dir,
    }


@publishing_mcp.tool()
def check_auth_status() -> dict:
    """Verifica status de autenticacao em todas as plataformas.

    Returns:
        Status de cada plataforma
    """
    ig_publisher = get_instagram_publisher()
    tt_publisher = get_tiktok_publisher()
    yt_publisher = get_youtube_publisher()

    return {
        "instagram": {
            "authenticated": ig_publisher.authenticate(),
            "has_webhook": bool(ig_publisher.webhook_url),
        },
        "tiktok": {
            "authenticated": tt_publisher.authenticate(),
            "has_webhook": bool(tt_publisher.webhook_url),
        },
        "youtube": {
            "authenticated": yt_publisher.authenticate(),
            "has_webhook": bool(yt_publisher.webhook_url),
        },
    }


@publishing_mcp.tool()
def validate_content_for_platform(
    platform: str,
    video_path: str,
    caption: str,
    hashtags: Optional[list[str]] = None,
) -> dict:
    """Valida se o conteudo pode ser publicado em uma plataforma.

    Args:
        platform: Plataforma (instagram, tiktok, youtube)
        video_path: Caminho do video
        caption: Caption
        hashtags: Hashtags

    Returns:
        Resultado da validacao
    """
    content = ContentToPublish(
        video_path=video_path,
        caption=caption,
        hashtags=hashtags or [],
    )

    if platform == "instagram":
        publisher = get_instagram_publisher()
    elif platform == "tiktok":
        publisher = get_tiktok_publisher()
    elif platform == "youtube":
        publisher = get_youtube_publisher()
    else:
        return {"valid": False, "error": f"Plataforma invalida: {platform}"}

    valid, error = publisher.validate_content(content)

    return {
        "valid": valid,
        "error": error if not valid else None,
        "platform": platform,
        "content_summary": {
            "video_path": video_path,
            "caption_length": len(caption),
            "hashtags_count": len(hashtags) if hashtags else 0,
        },
    }


# Export
__all__ = ["publishing_mcp"]
