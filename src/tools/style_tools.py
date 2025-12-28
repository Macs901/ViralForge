"""Style Cloning MCP Tools - Ferramentas para aprendizado e aplicacao de estilo."""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.agents.style_cloner_agent import get_style_cloner

# MCP Server para Style Tools
style_mcp = FastMCP("style-tools")


@style_mcp.tool()
def learn_style_from_profile(
    username: str,
    platform: str = "instagram",
    max_posts: int = 30,
) -> dict:
    """Aprende o estilo de um perfil de rede social.

    Analisa posts/videos de um perfil e cria um perfil de estilo
    que pode ser aplicado a novos conteudos.

    Args:
        username: Username do perfil para analisar
        platform: Plataforma (instagram, tiktok, youtube)
        max_posts: Maximo de posts para analisar (default 30)

    Returns:
        Resultado com perfil de estilo criado
    """
    cloner = get_style_cloner()
    result = cloner.learn_from_username(username, platform, max_posts)

    return {
        "success": result.profile_id is not None,
        "run_id": result.run_id,
        "profile_id": result.profile_id,
        "profile_name": result.profile_name,
        "samples_analyzed": result.samples_analyzed,
        "confidence_score": result.confidence_score,
        "primary_tone": result.primary_tone.value,
        "summary": result.summary,
        "duration_seconds": round(result.duration_seconds, 2),
    }


@style_mcp.tool()
def learn_style_from_captions(
    captions: list[str],
    profile_name: str = "Custom",
) -> dict:
    """Aprende estilo a partir de uma lista de captions.

    Cria um perfil de estilo baseado nos textos fornecidos.

    Args:
        captions: Lista de captions para analisar
        profile_name: Nome para o perfil criado

    Returns:
        Resultado com perfil de estilo criado
    """
    cloner = get_style_cloner()
    result = cloner.learn_from_captions(captions, profile_name)

    return {
        "success": result.profile_id is not None,
        "run_id": result.run_id,
        "profile_id": result.profile_id,
        "profile_name": result.profile_name,
        "samples_analyzed": result.samples_analyzed,
        "confidence_score": result.confidence_score,
        "primary_tone": result.primary_tone.value,
        "summary": result.summary,
        "duration_seconds": round(result.duration_seconds, 2),
    }


@style_mcp.tool()
def analyze_text_style(text: str) -> dict:
    """Analisa o estilo de um texto especifico.

    Extrai caracteristicas como tom, emojis, hashtags, etc.

    Args:
        text: Texto para analisar (caption, bio, etc.)

    Returns:
        Analise detalhada do texto
    """
    cloner = get_style_cloner()
    result = cloner.analyze_text(text)

    return {
        "tone": result.tone.value,
        "tone_scores": result.tone_scores,
        "word_count": result.word_count,
        "sentence_count": result.sentence_count,
        "avg_sentence_length": round(result.avg_sentence_length, 1),
        "emoji_count": result.emoji_count,
        "hashtag_count": result.hashtag_count,
        "question_count": result.question_count,
        "has_cta": result.has_cta,
        "vocabulary_level": result.vocabulary_level,
        "hashtags": result.hashtags,
        "emojis": result.emojis,
    }


@style_mcp.tool()
def apply_style(
    content: str,
    profile_id: Optional[int] = None,
    profile_name: Optional[str] = None,
) -> dict:
    """Aplica um estilo aprendido a um conteudo.

    Retorna sugestoes de como adaptar o conteudo ao estilo do perfil.

    Args:
        content: Conteudo base para estilizar
        profile_id: ID do perfil de estilo (opcional)
        profile_name: Nome do perfil de estilo (opcional)

    Returns:
        Conteudo estilizado e sugestoes
    """
    cloner = get_style_cloner()
    return cloner.apply_style(content, profile_id, profile_name)


@style_mcp.tool()
def list_style_profiles(active_only: bool = True) -> dict:
    """Lista todos os perfis de estilo disponveis.

    Args:
        active_only: Se True, retorna apenas perfis ativos

    Returns:
        Lista de perfis de estilo
    """
    cloner = get_style_cloner()
    profiles = cloner.get_all_profiles(active_only)

    return {
        "count": len(profiles),
        "profiles": profiles,
    }


@style_mcp.tool()
def get_style_suggestions(
    content_type: str = "reel",
    profile_name: Optional[str] = None,
) -> dict:
    """Gera sugestoes de estilo para um tipo de conteudo.

    Args:
        content_type: Tipo de conteudo (reel, story, post, short)
        profile_name: Nome do perfil para basear sugestoes (opcional)

    Returns:
        Sugestoes de estilo para o conteudo
    """
    cloner = get_style_cloner()

    # Sugestoes base por tipo
    base_suggestions = {
        "reel": {
            "duration": "15-60 segundos",
            "hook": "Primeiro 3 segundos sao criticos",
            "structure": ["Hook forte", "Conteudo principal", "CTA ou surpresa"],
            "music": "Use audio trending",
            "text": "Legendas sincronizadas ajudam retencao",
        },
        "story": {
            "duration": "15 segundos max",
            "hook": "Direto ao ponto",
            "structure": ["Pergunta ou statement", "Conteudo rapido"],
            "engagement": "Use stickers de perguntas/enquetes",
        },
        "post": {
            "visual": "Imagem de alta qualidade",
            "caption": "Pode ser mais longa, conte uma historia",
            "hashtags": "10-15 hashtags relevantes",
        },
        "short": {
            "duration": "15-60 segundos",
            "vertical": "9:16 obrigatorio",
            "hook": "Primeiro frame deve chamar atencao",
            "end_screen": "Use para mais engajamento",
        },
    }

    result = {
        "content_type": content_type,
        "base_suggestions": base_suggestions.get(content_type, {}),
    }

    # Se tem perfil, adiciona sugestoes personalizadas
    if profile_name:
        style_result = cloner.apply_style("", profile_name=profile_name)
        if not style_result.get("error"):
            result["profile_suggestions"] = {
                "profile_name": style_result.get("profile_name"),
                "tone": style_result.get("profile_tone"),
                "suggestions": style_result.get("suggestions", []),
                "recommended_hashtags": style_result.get("recommended_hashtags", []),
            }

    return result


# Export
__all__ = ["style_mcp"]
