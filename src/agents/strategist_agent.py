"""Strategist Agent - Responsavel por gerar estrategias de conteudo usando GPT-4o."""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models import (
    GeneratedStrategy,
    PromptVersion,
    RunMetrics,
    StrategyStatus,
    VideoAnalysis,
    ViralVideo,
)
from src.tools import budget_tools

settings = get_settings()


# === Schemas de Validacao ===


class VeoScenePrompt(BaseModel):
    """Schema para prompt de cena Veo."""

    scene_number: int = Field(description="Numero da cena")
    duration_seconds: int = Field(ge=3, le=10, description="Duracao em segundos")
    visual_description: str = Field(description="Descricao visual detalhada")
    camera_movement: str = Field(description="Movimento de camera")
    mood: str = Field(description="Clima/atmosfera da cena")


class TTSConfig(BaseModel):
    """Schema para configuracao TTS."""

    provider: str = Field(default="edge-tts")
    voice: str = Field(default="pt-BR-FranciscaNeural")
    rate: str = Field(default="+0%")
    pitch: str = Field(default="+0Hz")


class StrategyOutput(BaseModel):
    """Schema completo de output da estrategia."""

    title: str = Field(description="Titulo do video")
    concept: str = Field(description="Conceito geral")
    target_niche: str = Field(description="Nicho alvo")

    hook_script: str = Field(description="Roteiro do hook (0-3s)")
    development_script: str = Field(description="Roteiro do desenvolvimento (3-25s)")
    cta_script: str = Field(description="Roteiro do CTA (25-30s)")

    veo_prompts: list[VeoScenePrompt] = Field(description="Prompts para Veo")

    suggested_hashtags: list[str] = Field(description="Hashtags sugeridas")
    suggested_caption: str = Field(description="Caption sugerida")
    best_posting_time: str = Field(description="Melhor horario de postagem")
    suggested_music: str = Field(description="Sugestao de musica de fundo")

    estimated_scenes: int = Field(description="Numero de cenas")


@dataclass
class StrategistResult:
    """Resultado de geracao de estrategia."""

    run_id: str
    strategy_id: int
    title: str
    num_scenes: int
    estimated_cost_usd: float
    is_valid: bool
    cost_usd: float
    duration_seconds: float
    error: Optional[str] = None


class StrategistAgent:
    """Agent responsavel por gerar estrategias de conteudo usando GPT-4o.

    Pipeline:
    1. Selecao de video analisado de alta qualidade
    2. Geracao de estrategia com GPT-4o
    3. Validacao JSON com Pydantic
    4. Estimativa de custo de producao
    5. Armazenamento no banco
    """

    STRATEGY_PROMPT = """Voce e um estrategista de conteudo viral especializado em videos curtos para Instagram/TikTok.
Baseado na analise de um video viral, crie uma estrategia de conteudo original que replique os elementos de sucesso.

## Analise do Video de Referencia

**Metricas de Sucesso:**
- Views: {views}
- Likes: {likes}
- Virality Score: {virality_score}
- Replicability Score: {replicability_score}

**Analise do Hook:**
{hook_analysis}

**Analise do Desenvolvimento:**
{development_analysis}

**Fatores Virais:**
{viral_factors}

**Transcricao Original:**
{transcription}

**Nicho:**
{niche}

## Instrucoes

Crie uma estrategia de conteudo ORIGINAL (nao copie o video, mas replique os elementos de sucesso).
O video final deve ter aproximadamente 30 segundos no formato vertical (9:16).

Retorne um JSON com a seguinte estrutura EXATA:

```json
{{
    "title": "titulo atrativo do video",
    "concept": "conceito geral do video em 1-2 frases",
    "target_niche": "nicho alvo especifico",

    "hook_script": "roteiro completo do hook (0-3 segundos) - texto para narracao",
    "development_script": "roteiro do desenvolvimento (3-25 segundos) - texto para narracao",
    "cta_script": "roteiro do CTA (25-30 segundos) - texto para narracao",

    "veo_prompts": [
        {{
            "scene_number": 1,
            "duration_seconds": 3,
            "visual_description": "descricao visual detalhada para geracao de video AI",
            "camera_movement": "estatico|zoom in|zoom out|pan left|pan right|tracking",
            "mood": "clima/atmosfera da cena"
        }},
        // ... mais cenas (4-6 total para 30 segundos)
    ],

    "suggested_hashtags": ["hashtag1", "hashtag2", "hashtag3"],
    "suggested_caption": "caption otimizada para engajamento",
    "best_posting_time": "horario sugerido (ex: 19h-21h)",
    "suggested_music": "estilo de musica de fundo recomendado",

    "estimated_scenes": 5
}}
```

IMPORTANTE:
- Retorne APENAS o JSON, sem texto adicional
- Os scripts devem ser em portugues brasileiro
- Cada cena Veo deve ter 3-10 segundos
- Total de cenas: 4-6 para cobrir ~30 segundos
- Visual descriptions devem ser detalhadas para AI gerar video
- Foque em replicar os ELEMENTOS de sucesso, nao o conteudo
"""

    def __init__(self):
        """Inicializa Strategist Agent."""
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY nao configurado")

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.budget = budget_tools

    def generate(
        self,
        video_id: int,
        niche: Optional[str] = None,
    ) -> StrategistResult:
        """Gera estrategia baseada em um video analisado.

        Args:
            video_id: ID do video de referencia
            niche: Nicho alvo (opcional, usa nicho do video)

        Returns:
            StrategistResult com estrategia gerada
        """
        run_id = str(uuid4())
        start_time = datetime.now()

        db = get_sync_db()
        try:
            # Busca video e analise
            video = db.get(ViralVideo, video_id)
            if not video:
                raise ValueError(f"Video {video_id} nao encontrado")

            if not video.analysis:
                raise ValueError(f"Video {video_id} nao foi analisado")

            analysis = video.analysis

            # Verifica qualidade minima
            if float(analysis.virality_score or 0) < settings.min_virality_score:
                raise ValueError(
                    f"Video com virality_score abaixo do minimo "
                    f"({analysis.virality_score} < {settings.min_virality_score})"
                )

            # Cria metrica de run
            run_metric = RunMetrics(
                run_id=run_id,
                task_name="strategist_generation",
                agent_name="strategist",
            )
            db.add(run_metric)

            # Verifica budget
            can_run, cost, msg = self.budget.check_budget("openai", 1)
            if not can_run:
                raise RuntimeError(f"Budget insuficiente: {msg}")

            # Determina nicho
            target_niche = niche or video.profile.niche if video.profile else "geral"

            # Gera estrategia
            print(f"[Strategist] Gerando estrategia para video {video_id}...")
            strategy_output, tokens_used = self._call_gpt4o(video, analysis, target_niche)

            # Valida output
            is_valid, validated_output, validation_errors = self._validate_output(strategy_output)

            if not is_valid or not validated_output:
                raise ValueError(f"Output invalido: {validation_errors}")

            # Busca versao do prompt
            prompt_version = self._get_prompt_version(db)

            # Calcula custo estimado de producao
            estimated_cost = self.budget.estimate_production_cost(
                num_scenes=validated_output.estimated_scenes,
                script_chars=len(validated_output.hook_script or "")
                + len(validated_output.development_script or "")
                + len(validated_output.cta_script or ""),
            )

            # Cria estrategia
            strategy = GeneratedStrategy(
                source_video_id=video_id,
                prompt_version_id=prompt_version.id if prompt_version else None,
                title=validated_output.title,
                concept=validated_output.concept,
                target_niche=validated_output.target_niche,
                hook_script=validated_output.hook_script,
                development_script=validated_output.development_script,
                cta_script=validated_output.cta_script,
                full_script=(
                    f"{validated_output.hook_script} "
                    f"{validated_output.development_script} "
                    f"{validated_output.cta_script}"
                ),
                veo_prompts=[p.model_dump() for p in validated_output.veo_prompts],
                suggested_hashtags=validated_output.suggested_hashtags,
                suggested_caption=validated_output.suggested_caption,
                best_posting_time=validated_output.best_posting_time,
                suggested_music=validated_output.suggested_music,
                estimated_production_cost_usd=Decimal(str(estimated_cost["total_usd"])),
                tokens_used=tokens_used,
                generation_cost_usd=Decimal(str(settings.cost_gpt4o_per_strategy)),
                status=StrategyStatus.DRAFT.value,
            )

            db.add(strategy)

            # Registra custo
            self.budget.register_cost(
                "openai", Decimal(str(settings.cost_gpt4o_per_strategy)), 1, db
            )
            self.budget.increment_counter("strategies_generated", 1, db)

            # Finaliza metrica
            run_metric.items_processed = 1
            run_metric.actual_cost_usd = Decimal(str(settings.cost_gpt4o_per_strategy))
            run_metric.complete(success=True)

            db.commit()
            db.refresh(strategy)

            duration = (datetime.now() - start_time).total_seconds()

            print(f"[Strategist] Estrategia '{strategy.title}' criada com sucesso!")

            return StrategistResult(
                run_id=run_id,
                strategy_id=strategy.id,
                title=strategy.title,
                num_scenes=validated_output.estimated_scenes,
                estimated_cost_usd=estimated_cost["total_usd"],
                is_valid=True,
                cost_usd=float(settings.cost_gpt4o_per_strategy),
                duration_seconds=duration,
            )

        except Exception as e:
            if "run_metric" in locals():
                run_metric.complete(success=False, error=str(e))
                db.commit()
            raise
        finally:
            db.close()

    def generate_from_best_videos(
        self,
        niche: str,
        limit: int = 3,
    ) -> list[StrategistResult]:
        """Gera estrategias a partir dos melhores videos de um nicho.

        Args:
            niche: Nicho para filtrar videos
            limit: Numero de estrategias a gerar

        Returns:
            Lista de StrategistResult
        """
        db = get_sync_db()
        try:
            # Busca melhores videos analisados do nicho
            stmt = (
                select(ViralVideo)
                .join(VideoAnalysis)
                .where(
                    ViralVideo.is_analyzed == True,
                    VideoAnalysis.virality_score >= Decimal(str(settings.min_virality_score)),
                    VideoAnalysis.replicability_score >= Decimal("0.6"),
                )
                .order_by(VideoAnalysis.virality_score.desc())
                .limit(limit * 2)  # Busca mais para ter margem
            )
            videos = db.execute(stmt).scalars().all()

            # Filtra videos que ainda nao tem estrategia
            videos_without_strategy = [
                v for v in videos if not v.strategies
            ][:limit]

            results = []
            for video in videos_without_strategy:
                try:
                    # Verifica budget
                    status = self.budget.get_daily_status()
                    if status["budget"]["exceeded"]:
                        print("[Strategist] Budget excedido, parando geracao")
                        break

                    result = self.generate(video.id, niche=niche)
                    results.append(result)

                except Exception as e:
                    print(f"[Strategist] Erro ao gerar estrategia para video {video.id}: {e}")

            return results
        finally:
            db.close()

    def _call_gpt4o(
        self,
        video: ViralVideo,
        analysis: VideoAnalysis,
        niche: str,
    ) -> tuple[str, int]:
        """Chama GPT-4o para geracao de estrategia.

        Returns:
            Tuple (response_text, tokens_used)
        """
        prompt = self.STRATEGY_PROMPT.format(
            views=video.views_count,
            likes=video.likes_count,
            virality_score=analysis.virality_score,
            replicability_score=analysis.replicability_score,
            hook_analysis=json.dumps(analysis.hook_analysis, ensure_ascii=False, indent=2),
            development_analysis=json.dumps(analysis.development, ensure_ascii=False, indent=2),
            viral_factors=json.dumps(analysis.viral_factors, ensure_ascii=False, indent=2),
            transcription=video.transcription or "Nao disponivel",
            niche=niche,
        )

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Voce e um estrategista de conteudo viral. Responda apenas em JSON valido.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2500,
        )

        tokens = response.usage.total_tokens if response.usage else 0

        return response.choices[0].message.content or "", tokens

    def _validate_output(
        self, output: str
    ) -> tuple[bool, Optional[StrategyOutput], list[str]]:
        """Valida output do GPT-4o com Pydantic."""
        errors = []

        try:
            json_str = output.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            errors.append(f"JSON invalido: {e}")
            return False, None, errors

        try:
            validated = StrategyOutput(**data)
            return True, validated, []
        except ValidationError as e:
            for err in e.errors():
                errors.append(f"{err['loc']}: {err['msg']}")
            return False, None, errors

    def _get_prompt_version(self, db: Session) -> Optional[PromptVersion]:
        """Busca versao ativa do prompt de estrategia."""
        stmt = select(PromptVersion).where(
            PromptVersion.prompt_type == "strategy",
            PromptVersion.is_active == True,
        )
        return db.execute(stmt).scalar_one_or_none()


# Singleton para uso global
strategist_agent = StrategistAgent()
