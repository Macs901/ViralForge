"""Style Cloner Agent - Aprende e replica seu estilo unico."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models.style import StyleAnalysis, StyleProfile, ToneType, ContentRhythm

settings = get_settings()


# ========================
# ANALISE DE TOM
# ========================

TONE_KEYWORDS = {
    ToneType.FORMAL: [
        "prezado", "cordialmente", "respeitosamente", "senhor", "senhora",
        "conforme", "mediante", "portanto", "todavia", "entretanto",
    ],
    ToneType.CASUAL: [
        "oi", "eai", "bora", "vamos la", "galera", "pessoal",
        "tipo", "legal", "massa", "top", "show",
    ],
    ToneType.HUMOROUS: [
        "haha", "kkk", "rsrs", "lol", "piada", "zueira",
        "meme", "engraçado", "rir", "humor",
    ],
    ToneType.INSPIRATIONAL: [
        "sonho", "conquista", "acredite", "voce consegue", "nunca desista",
        "motivacao", "sucesso", "objetivo", "meta", "foco",
    ],
    ToneType.EDUCATIONAL: [
        "aprenda", "dica", "tutorial", "como fazer", "passo a passo",
        "entenda", "saiba", "descubra", "ensino", "explico",
    ],
    ToneType.PROVOCATIVE: [
        "chocante", "polêmico", "verdade", "ninguém fala", "segredo",
        "urgente", "cuidado", "alerta", "não ignore",
    ],
    ToneType.STORYTELLING: [
        "era uma vez", "um dia", "aconteceu", "historia", "quando eu",
        "lembro", "naquela época", "vou contar", "deixa eu te contar",
    ],
}

CTA_PATTERNS = [
    r"segu[ei]",
    r"curte?",
    r"compartilh[ae]",
    r"coment[ae]",
    r"salv[ae]",
    r"ativ[ae]\s*(o\s*)?sininho",
    r"link\s*na\s*bio",
    r"clica",
    r"acessa",
    r"inscreva",
]


@dataclass
class TextAnalysisResult:
    """Resultado da analise de texto."""
    tone: ToneType
    tone_scores: dict[str, float] = field(default_factory=dict)
    word_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    emoji_count: int = 0
    hashtag_count: int = 0
    question_count: int = 0
    has_cta: bool = False
    vocabulary_level: str = "medium"
    hashtags: list[str] = field(default_factory=list)
    emojis: list[str] = field(default_factory=list)


@dataclass
class StyleClonerResult:
    """Resultado do Style Cloner."""
    run_id: str
    profile_id: Optional[int]
    samples_analyzed: int
    profile_name: str
    confidence_score: float
    primary_tone: ToneType
    summary: dict = field(default_factory=dict)
    duration_seconds: float = 0.0


class StyleClonerAgent:
    """Agent que aprende e replica estilo unico do usuario."""

    def __init__(self):
        """Inicializa o agent."""
        self.run_id = str(uuid4())

    def analyze_text(self, text: str) -> TextAnalysisResult:
        """Analisa um texto para extrair caracteristicas de estilo.

        Args:
            text: Texto para analisar (caption, bio, etc.)

        Returns:
            TextAnalysisResult com metricas
        """
        if not text:
            return TextAnalysisResult(tone=ToneType.CASUAL)

        text_lower = text.lower()

        # Contagem basica
        words = text.split()
        word_count = len(words)

        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences) if sentences else 1
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

        # Emojis (pattern simplificado)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        emojis = emoji_pattern.findall(text)
        emoji_count = len(emojis)

        # Hashtags
        hashtags = re.findall(r'#\w+', text)
        hashtag_count = len(hashtags)

        # Perguntas
        question_count = text.count('?')

        # CTA detection
        has_cta = any(re.search(pattern, text_lower) for pattern in CTA_PATTERNS)

        # Tom de voz
        tone_scores = {}
        for tone, keywords in TONE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                tone_scores[tone.value] = score

        # Determina tom principal
        if tone_scores:
            primary_tone_str = max(tone_scores, key=tone_scores.get)
            primary_tone = ToneType(primary_tone_str)
        else:
            primary_tone = ToneType.CASUAL

        # Nivel de vocabulario
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        if avg_word_length > 7:
            vocabulary_level = "advanced"
        elif avg_word_length < 5:
            vocabulary_level = "simple"
        else:
            vocabulary_level = "medium"

        return TextAnalysisResult(
            tone=primary_tone,
            tone_scores=tone_scores,
            word_count=word_count,
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length,
            emoji_count=emoji_count,
            hashtag_count=hashtag_count,
            question_count=question_count,
            has_cta=has_cta,
            vocabulary_level=vocabulary_level,
            hashtags=[h.lower() for h in hashtags],
            emojis=emojis,
        )

    def learn_from_username(
        self,
        username: str,
        platform: str = "instagram",
        max_posts: int = 50,
    ) -> StyleClonerResult:
        """Aprende estilo de um perfil especifico.

        Args:
            username: Username do perfil
            platform: Plataforma (instagram, tiktok, youtube)
            max_posts: Maximo de posts para analisar

        Returns:
            StyleClonerResult
        """
        start_time = datetime.now()
        analyses = []

        try:
            if platform == "instagram":
                analyses = self._learn_from_instagram(username, max_posts)
            elif platform == "tiktok":
                analyses = self._learn_from_tiktok(username, max_posts)
            elif platform == "youtube":
                analyses = self._learn_from_youtube(username, max_posts)

        except Exception as e:
            print(f"[StyleCloner] Erro ao analisar {username}: {e}")

        if not analyses:
            print(f"[StyleCloner] Nenhuma analise obtida para {username}")
            return StyleClonerResult(
                run_id=self.run_id,
                profile_id=None,
                samples_analyzed=0,
                profile_name=username,
                confidence_score=0.0,
                primary_tone=ToneType.CASUAL,
            )

        # Agrega resultados
        profile = self._aggregate_analyses(username, analyses)

        # Salva no banco
        profile_id = self._save_profile(profile)

        return StyleClonerResult(
            run_id=self.run_id,
            profile_id=profile_id,
            samples_analyzed=len(analyses),
            profile_name=profile.get("name", username),
            confidence_score=profile.get("confidence_score", 0),
            primary_tone=ToneType(profile.get("primary_tone", "casual")),
            summary=profile,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

    def learn_from_captions(
        self,
        captions: list[str],
        profile_name: str = "Custom",
    ) -> StyleClonerResult:
        """Aprende estilo a partir de uma lista de captions.

        Args:
            captions: Lista de captions para analisar
            profile_name: Nome para o perfil

        Returns:
            StyleClonerResult
        """
        start_time = datetime.now()

        analyses = []
        for caption in captions:
            if caption and len(caption) > 10:
                result = self.analyze_text(caption)
                analyses.append({
                    "text": caption[:500],
                    "analysis": result,
                })

        if not analyses:
            return StyleClonerResult(
                run_id=self.run_id,
                profile_id=None,
                samples_analyzed=0,
                profile_name=profile_name,
                confidence_score=0.0,
                primary_tone=ToneType.CASUAL,
            )

        # Agrega
        profile = self._aggregate_analyses(profile_name, analyses)
        profile_id = self._save_profile(profile)

        return StyleClonerResult(
            run_id=self.run_id,
            profile_id=profile_id,
            samples_analyzed=len(analyses),
            profile_name=profile_name,
            confidence_score=profile.get("confidence_score", 0),
            primary_tone=ToneType(profile.get("primary_tone", "casual")),
            summary=profile,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

    def _learn_from_instagram(self, username: str, max_posts: int) -> list[dict]:
        """Aprende de um perfil do Instagram."""
        analyses = []

        try:
            from src.tools.instagram_scraper import instagram_scraper

            # Busca posts do perfil
            result = instagram_scraper.scrape_profile_posts(username, max_posts=max_posts)

            for post in result.posts:
                caption = post.get("caption", "")
                if caption and len(caption) > 10:
                    text_analysis = self.analyze_text(caption)
                    analyses.append({
                        "text": caption[:500],
                        "analysis": text_analysis,
                        "url": post.get("url"),
                        "platform": "instagram",
                        "likes": post.get("likes_count", 0),
                        "comments": post.get("comments_count", 0),
                    })

        except ImportError:
            print("[StyleCloner] instagram_scraper nao disponivel")
        except Exception as e:
            print(f"[StyleCloner] Erro Instagram: {e}")

        return analyses

    def _learn_from_tiktok(self, username: str, max_posts: int) -> list[dict]:
        """Aprende de um perfil do TikTok."""
        analyses = []

        try:
            from src.tools.tiktok_scraper import tiktok_scraper

            result = tiktok_scraper.scrape_profile(username, max_videos=max_posts)

            for video in result.videos:
                caption = video.caption or ""
                if caption and len(caption) > 5:
                    text_analysis = self.analyze_text(caption)
                    analyses.append({
                        "text": caption[:500],
                        "analysis": text_analysis,
                        "url": video.url,
                        "platform": "tiktok",
                        "views": video.views,
                        "likes": video.likes,
                    })

        except ImportError:
            print("[StyleCloner] tiktok_scraper nao disponivel")
        except Exception as e:
            print(f"[StyleCloner] Erro TikTok: {e}")

        return analyses

    def _learn_from_youtube(self, username: str, max_posts: int) -> list[dict]:
        """Aprende de um canal do YouTube."""
        analyses = []

        try:
            from src.tools.youtube_scraper import youtube_scraper

            result = youtube_scraper.scrape_channel_shorts(username, max_shorts=max_posts)

            for short in result:
                title = short.title or ""
                description = short.description or ""
                text = f"{title}\n{description}"

                if text and len(text) > 10:
                    text_analysis = self.analyze_text(text)
                    analyses.append({
                        "text": text[:500],
                        "analysis": text_analysis,
                        "url": short.url,
                        "platform": "youtube",
                        "views": short.views,
                        "likes": short.likes,
                    })

        except ImportError:
            print("[StyleCloner] youtube_scraper nao disponivel")
        except Exception as e:
            print(f"[StyleCloner] Erro YouTube: {e}")

        return analyses

    def _aggregate_analyses(self, name: str, analyses: list[dict]) -> dict:
        """Agrega multiplas analises em um perfil de estilo."""
        if not analyses:
            return {"name": name, "confidence_score": 0}

        # Contadores
        tone_counts = {}
        total_emojis = 0
        total_words = 0
        total_sentences = 0
        total_questions = 0
        total_cta = 0
        all_hashtags = []
        vocabulary_levels = []

        for item in analyses:
            analysis = item.get("analysis")
            if not analysis:
                continue

            # Tons
            tone_counts[analysis.tone.value] = tone_counts.get(analysis.tone.value, 0) + 1

            # Metricas
            total_emojis += analysis.emoji_count
            total_words += analysis.word_count
            total_sentences += analysis.sentence_count
            total_questions += analysis.question_count
            total_cta += 1 if analysis.has_cta else 0
            vocabulary_levels.append(analysis.vocabulary_level)
            all_hashtags.extend(analysis.hashtags)

        n = len(analyses)

        # Tom principal
        primary_tone = max(tone_counts, key=tone_counts.get) if tone_counts else "casual"

        # Tons secundarios
        secondary_tones = [
            t for t, c in sorted(tone_counts.items(), key=lambda x: x[1], reverse=True)[1:3]
            if c >= n * 0.2  # Minimo 20% das amostras
        ]

        # Frequencia de emoji
        avg_emoji = total_emojis / n
        if avg_emoji < 0.5:
            emoji_frequency = "sparse"
        elif avg_emoji < 2:
            emoji_frequency = "moderate"
        else:
            emoji_frequency = "heavy"

        # Tamanho de sentença
        avg_sentence_len = total_words / total_sentences if total_sentences else 0
        if avg_sentence_len < 10:
            sentence_length = "short"
        elif avg_sentence_len > 20:
            sentence_length = "long"
        else:
            sentence_length = "medium"

        # Vocabulario (moda)
        from collections import Counter
        vocab_counter = Counter(vocabulary_levels)
        vocabulary_level = vocab_counter.most_common(1)[0][0] if vocab_counter else "medium"

        # Hashtags mais usadas
        hashtag_counter = Counter(all_hashtags)
        favorite_hashtags = [h for h, _ in hashtag_counter.most_common(20)]

        # Conta hashtags
        avg_hashtags = len(all_hashtags) / n if n else 0
        hashtag_strategy = {
            "avg_count": round(avg_hashtags, 1),
            "total_unique": len(set(all_hashtags)),
        }

        # Confianca baseada no numero de amostras
        if n >= 50:
            confidence = 0.95
        elif n >= 30:
            confidence = 0.85
        elif n >= 15:
            confidence = 0.7
        elif n >= 5:
            confidence = 0.5
        else:
            confidence = 0.3

        return {
            "name": name,
            "primary_tone": primary_tone,
            "secondary_tones": secondary_tones,
            "vocabulary_level": vocabulary_level,
            "use_emoji": total_emojis > 0,
            "emoji_frequency": emoji_frequency,
            "sentence_length": sentence_length,
            "uses_questions": total_questions > n * 0.3,
            "uses_cta": total_cta > n * 0.3,
            "favorite_hashtags": favorite_hashtags,
            "hashtag_strategy": hashtag_strategy,
            "sample_count": n,
            "confidence_score": confidence,
            "raw_analysis": {
                "tone_distribution": tone_counts,
                "avg_emojis": round(avg_emoji, 2),
                "avg_words": round(total_words / n, 1),
                "avg_questions": round(total_questions / n, 2),
                "cta_rate": round(total_cta / n, 2),
            },
        }

    def _save_profile(self, profile_data: dict) -> Optional[int]:
        """Salva o perfil de estilo no banco."""
        db = get_sync_db()
        try:
            # Verifica se ja existe
            existing = db.execute(
                select(StyleProfile).where(StyleProfile.name == profile_data["name"])
            ).scalar_one_or_none()

            if existing:
                # Atualiza
                for key, value in profile_data.items():
                    if hasattr(existing, key) and key != "id":
                        setattr(existing, key, value)
                existing.last_analysis_at = datetime.now()
                db.commit()
                return existing.id
            else:
                # Cria novo
                new_profile = StyleProfile(
                    name=profile_data.get("name"),
                    primary_tone=profile_data.get("primary_tone", "casual"),
                    secondary_tones=profile_data.get("secondary_tones", []),
                    vocabulary_level=profile_data.get("vocabulary_level", "medium"),
                    use_emoji=profile_data.get("use_emoji", True),
                    emoji_frequency=profile_data.get("emoji_frequency", "moderate"),
                    sentence_length=profile_data.get("sentence_length", "medium"),
                    uses_questions=profile_data.get("uses_questions", True),
                    uses_cta=profile_data.get("uses_cta", True),
                    favorite_hashtags=profile_data.get("favorite_hashtags", []),
                    hashtag_strategy=profile_data.get("hashtag_strategy", {}),
                    sample_count=profile_data.get("sample_count", 0),
                    confidence_score=Decimal(str(profile_data.get("confidence_score", 0))),
                    raw_analysis=profile_data.get("raw_analysis", {}),
                    last_analysis_at=datetime.now(),
                    is_active=True,
                )
                db.add(new_profile)
                db.commit()
                db.refresh(new_profile)
                return new_profile.id

        except Exception as e:
            db.rollback()
            print(f"[StyleCloner] Erro ao salvar: {e}")
            return None
        finally:
            db.close()

    def apply_style(
        self,
        content: str,
        profile_id: Optional[int] = None,
        profile_name: Optional[str] = None,
    ) -> dict:
        """Aplica um estilo aprendido a um conteudo.

        Args:
            content: Conteudo base para estilizar
            profile_id: ID do perfil ou
            profile_name: Nome do perfil

        Returns:
            Dict com conteudo estilizado e sugestoes
        """
        db = get_sync_db()
        try:
            # Busca perfil
            if profile_id:
                profile = db.execute(
                    select(StyleProfile).where(StyleProfile.id == profile_id)
                ).scalar_one_or_none()
            elif profile_name:
                profile = db.execute(
                    select(StyleProfile).where(StyleProfile.name == profile_name)
                ).scalar_one_or_none()
            else:
                # Busca perfil default
                profile = db.execute(
                    select(StyleProfile).where(StyleProfile.is_default == True)
                ).scalar_one_or_none()

            if not profile:
                return {
                    "styled_content": content,
                    "suggestions": [],
                    "error": "Perfil nao encontrado",
                }

            # Gera sugestoes baseadas no perfil
            suggestions = []

            # Emojis
            if profile.use_emoji and profile.emoji_frequency != "none":
                emoji_suggestion = "Adicione emojis"
                if profile.emoji_frequency == "heavy":
                    emoji_suggestion += " (bastante, 3-5 por caption)"
                elif profile.emoji_frequency == "moderate":
                    emoji_suggestion += " (moderado, 1-2 por caption)"
                suggestions.append(emoji_suggestion)

            # Tom
            tone_tips = {
                "formal": "Use linguagem profissional e termos tecnicos",
                "casual": "Escreva como se estivesse conversando com um amigo",
                "humorous": "Adicione humor e referencias a memes",
                "inspirational": "Use frases motivacionais e palavras de encorajamento",
                "educational": "Estruture como dicas ou passo-a-passo",
                "provocative": "Use perguntas provocativas e afirmacoes fortes",
                "storytelling": "Conte uma historia, use narrativa",
            }
            if profile.primary_tone in tone_tips:
                suggestions.append(tone_tips[profile.primary_tone])

            # CTA
            if profile.uses_cta:
                suggestions.append("Adicione call-to-action (curta, comente, salve)")

            # Perguntas
            if profile.uses_questions:
                suggestions.append("Inclua uma pergunta para gerar engajamento")

            # Hashtags
            if profile.favorite_hashtags:
                top_hashtags = profile.favorite_hashtags[:5]
                suggestions.append(f"Use hashtags: {', '.join(top_hashtags)}")

            return {
                "styled_content": content,
                "profile_name": profile.name,
                "profile_tone": profile.primary_tone,
                "suggestions": suggestions,
                "recommended_hashtags": profile.favorite_hashtags[:10] if profile.favorite_hashtags else [],
                "emoji_frequency": profile.emoji_frequency,
                "sentence_length": profile.sentence_length,
            }

        except Exception as e:
            print(f"[StyleCloner] Erro: {e}")
            return {
                "styled_content": content,
                "suggestions": [],
                "error": str(e),
            }
        finally:
            db.close()

    def get_all_profiles(self, active_only: bool = True) -> list[dict]:
        """Retorna todos os perfis de estilo.

        Args:
            active_only: Apenas perfis ativos

        Returns:
            Lista de perfis
        """
        db = get_sync_db()
        try:
            query = select(StyleProfile)
            if active_only:
                query = query.where(StyleProfile.is_active == True)
            query = query.order_by(StyleProfile.created_at.desc())

            profiles = db.execute(query).scalars().all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "primary_tone": p.primary_tone,
                    "confidence_score": float(p.confidence_score) if p.confidence_score else 0,
                    "sample_count": p.sample_count,
                    "is_default": p.is_default,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in profiles
            ]
        finally:
            db.close()


# Factory function
def get_style_cloner() -> StyleClonerAgent:
    """Retorna instancia do StyleClonerAgent."""
    return StyleClonerAgent()
