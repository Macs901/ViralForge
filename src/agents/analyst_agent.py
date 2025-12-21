"""Analyst Agent - Responsavel por analisar videos usando Gemini."""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models import (
    PromptVersion,
    RunMetrics,
    VideoAnalysis,
    ViralVideo,
)
from src.tools import budget_tools, storage_tools, whisper_tools

settings = get_settings()


# === Schemas de Validacao ===


class HookAnalysis(BaseModel):
    """Schema para analise do hook."""

    opening_type: str = Field(description="Tipo de abertura (pergunta, afirmacao, visual)")
    attention_technique: str = Field(description="Tecnica de captura de atencao")
    first_words: str = Field(description="Primeiras palavras/segundos")
    hook_score: float = Field(ge=0, le=1, description="Score do hook (0-1)")


class DevelopmentAnalysis(BaseModel):
    """Schema para analise do desenvolvimento."""

    structure: str = Field(description="Estrutura narrativa")
    key_points: list[str] = Field(description="Pontos principais")
    pacing: str = Field(description="Ritmo do conteudo")
    retention_techniques: list[str] = Field(description="Tecnicas de retencao")


class CTAAnalysis(BaseModel):
    """Schema para analise do CTA."""

    cta_type: str = Field(description="Tipo de CTA")
    cta_text: str = Field(description="Texto do CTA")
    urgency_level: str = Field(description="Nivel de urgencia")
    cta_score: float = Field(ge=0, le=1, description="Score do CTA (0-1)")


class ViralFactors(BaseModel):
    """Schema para fatores de viralizacao."""

    emotional_triggers: list[str] = Field(description="Gatilhos emocionais")
    shareability_factors: list[str] = Field(description="Fatores de compartilhamento")
    trend_alignment: str = Field(description="Alinhamento com tendencias")
    controversy_level: float = Field(ge=0, le=1, description="Nivel de controversia")


class GeminiAnalysisOutput(BaseModel):
    """Schema completo de output do Gemini."""

    hook_analysis: HookAnalysis
    development: DevelopmentAnalysis
    cta_analysis: CTAAnalysis
    viral_factors: ViralFactors
    virality_score: float = Field(ge=0, le=1, description="Score de viralidade")
    replicability_score: float = Field(ge=0, le=1, description="Score de replicabilidade")
    production_quality_score: float = Field(ge=0, le=1, description="Score de qualidade")
    summary: str = Field(description="Resumo da analise")


@dataclass
class AnalystResult:
    """Resultado de uma analise."""

    run_id: str
    video_id: int
    virality_score: float
    replicability_score: float
    is_valid: bool
    cost_usd: float
    duration_seconds: float
    error: Optional[str] = None


class AnalystAgent:
    """Agent responsavel por analisar videos virais usando Gemini.

    Pipeline:
    1. Download do video (se necessario)
    2. Transcricao com Whisper (se necessario)
    3. Analise com Gemini 1.5 Pro
    4. Validacao JSON com Pydantic
    5. Armazenamento no banco
    """

    ANALYSIS_PROMPT = """Voce e um especialista em analise de videos virais para redes sociais.
Analise o video/transcricao fornecido e retorne uma analise detalhada em formato JSON.

## Video a Analisar

**Transcricao:**
{transcription}

**Metricas:**
- Views: {views}
- Likes: {likes}
- Comentarios: {comments}
- Duracao: {duration}s

**Caption:**
{caption}

## Instrucoes

Analise o conteudo e retorne um JSON com a seguinte estrutura EXATA:

```json
{{
    "hook_analysis": {{
        "opening_type": "pergunta|afirmacao|visual|choque|curiosidade",
        "attention_technique": "descricao da tecnica usada",
        "first_words": "primeiras palavras ou descricao visual",
        "hook_score": 0.0-1.0
    }},
    "development": {{
        "structure": "descricao da estrutura narrativa",
        "key_points": ["ponto 1", "ponto 2", "ponto 3"],
        "pacing": "rapido|moderado|lento",
        "retention_techniques": ["tecnica 1", "tecnica 2"]
    }},
    "cta_analysis": {{
        "cta_type": "seguir|curtir|comentar|compartilhar|link|nenhum",
        "cta_text": "texto exato do CTA ou descricao",
        "urgency_level": "baixo|medio|alto",
        "cta_score": 0.0-1.0
    }},
    "viral_factors": {{
        "emotional_triggers": ["emocao 1", "emocao 2"],
        "shareability_factors": ["fator 1", "fator 2"],
        "trend_alignment": "descricao do alinhamento com tendencias",
        "controversy_level": 0.0-1.0
    }},
    "virality_score": 0.0-1.0,
    "replicability_score": 0.0-1.0,
    "production_quality_score": 0.0-1.0,
    "summary": "resumo da analise em 2-3 frases"
}}
```

IMPORTANTE:
- Retorne APENAS o JSON, sem texto adicional
- Todos os scores devem estar entre 0.0 e 1.0
- Seja especifico nas descricoes
- Considere o contexto brasileiro de redes sociais
"""

    def __init__(self):
        """Inicializa Analyst Agent."""
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY nao configurado")

        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.budget = budget_tools
        self.whisper = whisper_tools
        self.storage = storage_tools

    def analyze(self, video_id: int, force: bool = False) -> AnalystResult:
        """Analisa um video especifico.

        Args:
            video_id: ID do video no banco
            force: Se True, reanalisa mesmo se ja analisado

        Returns:
            AnalystResult com resultado da analise
        """
        run_id = str(uuid4())
        start_time = datetime.now()

        db = get_sync_db()
        try:
            # Busca video
            video = db.get(ViralVideo, video_id)
            if not video:
                raise ValueError(f"Video {video_id} nao encontrado")

            # Verifica se ja foi analisado
            if video.is_analyzed and not force:
                return AnalystResult(
                    run_id=run_id,
                    video_id=video_id,
                    virality_score=float(video.analysis.virality_score) if video.analysis else 0,
                    replicability_score=float(video.analysis.replicability_score) if video.analysis else 0,
                    is_valid=True,
                    cost_usd=0,
                    duration_seconds=0,
                    error="Video ja analisado (use force=True para reanalisar)",
                )

            # Cria metrica de run
            run_metric = RunMetrics(
                run_id=run_id,
                task_name="analyst_analysis",
                agent_name="analyst",
            )
            db.add(run_metric)

            # Verifica budget
            can_run, cost, msg = self.budget.check_budget("gemini", 1)
            if not can_run:
                raise RuntimeError(f"Budget insuficiente: {msg}")

            # Garante que video tem transcricao
            if not video.transcription:
                if not video.is_transcribed and video.video_file_path:
                    print(f"[Analyst] Transcrevendo video {video_id}...")
                    self._transcribe_video(video, db)
                else:
                    raise ValueError("Video sem transcricao disponivel")

            # Executa analise
            print(f"[Analyst] Analisando video {video_id}...")
            analysis_output, tokens_used = self._call_gemini(video)

            # Valida output
            is_valid, validated_output, validation_errors = self._validate_output(analysis_output)

            # Busca versao do prompt
            prompt_version = self._get_prompt_version(db)

            # Cria ou atualiza analise
            analysis = video.analysis or VideoAnalysis(video_id=video_id)

            if validated_output:
                analysis.hook_analysis = validated_output.hook_analysis.model_dump()
                analysis.development = validated_output.development.model_dump()
                analysis.cta_analysis = validated_output.cta_analysis.model_dump()
                analysis.viral_factors = validated_output.viral_factors.model_dump()
                analysis.virality_score = Decimal(str(validated_output.virality_score))
                analysis.replicability_score = Decimal(str(validated_output.replicability_score))
                analysis.production_quality_score = Decimal(str(validated_output.production_quality_score))

            analysis.is_valid_json = is_valid
            analysis.validation_errors = {"errors": validation_errors} if validation_errors else None
            analysis.raw_gemini_response = analysis_output
            analysis.prompt_version_id = prompt_version.id if prompt_version else None
            analysis.tokens_used = tokens_used
            analysis.analysis_cost_usd = Decimal(str(settings.cost_gemini_per_video))

            if not video.analysis:
                db.add(analysis)

            # Atualiza video
            video.is_analyzed = True

            # Registra custo
            self.budget.register_cost("gemini", Decimal(str(settings.cost_gemini_per_video)), 1, db)
            self.budget.increment_counter("videos_analyzed", 1, db)

            # Finaliza metrica
            run_metric.items_input = 1
            run_metric.items_processed = 1 if is_valid else 0
            run_metric.actual_cost_usd = Decimal(str(settings.cost_gemini_per_video))
            run_metric.complete(success=is_valid)

            db.commit()

            duration = (datetime.now() - start_time).total_seconds()

            return AnalystResult(
                run_id=run_id,
                video_id=video_id,
                virality_score=float(analysis.virality_score) if analysis.virality_score else 0,
                replicability_score=float(analysis.replicability_score) if analysis.replicability_score else 0,
                is_valid=is_valid,
                cost_usd=float(settings.cost_gemini_per_video),
                duration_seconds=duration,
            )

        except Exception as e:
            if "run_metric" in locals():
                run_metric.complete(success=False, error=str(e))
                db.commit()
            raise
        finally:
            db.close()

    def analyze_pending(self, limit: int = 10) -> list[AnalystResult]:
        """Analisa videos pendentes que passaram no pre-filtro.

        Args:
            limit: Maximo de videos a analisar

        Returns:
            Lista de AnalystResult
        """
        db = get_sync_db()
        try:
            # Busca videos prontos para analise
            stmt = (
                select(ViralVideo)
                .where(
                    ViralVideo.passes_prefilter == True,
                    ViralVideo.is_analyzed == False,
                    ViralVideo.is_transcribed == True,
                )
                .order_by(ViralVideo.statistical_viral_score.desc())
                .limit(limit)
            )
            videos = db.execute(stmt).scalars().all()

            results = []
            for video in videos:
                try:
                    # Verifica budget
                    status = self.budget.get_daily_status()
                    if status["budget"]["exceeded"]:
                        print("[Analyst] Budget excedido, parando analises")
                        break

                    result = self.analyze(video.id)
                    results.append(result)

                except Exception as e:
                    print(f"[Analyst] Erro ao analisar video {video.id}: {e}")

            return results
        finally:
            db.close()

    def _call_gemini(self, video: ViralVideo) -> tuple[str, int]:
        """Chama Gemini para analise.

        Returns:
            Tuple (response_text, tokens_used)
        """
        prompt = self.ANALYSIS_PROMPT.format(
            transcription=video.transcription or "Nao disponivel",
            views=video.views_count,
            likes=video.likes_count,
            comments=video.comments_count,
            duration=video.duration_seconds or "Desconhecida",
            caption=video.caption or "Sem caption",
        )

        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2000,
            ),
        )

        tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0

        return response.text, tokens

    def _validate_output(
        self, output: str
    ) -> tuple[bool, Optional[GeminiAnalysisOutput], list[str]]:
        """Valida output do Gemini com Pydantic.

        Returns:
            Tuple (is_valid, validated_output, errors)
        """
        errors = []

        # Tenta extrair JSON do output
        try:
            # Remove possivel markdown
            json_str = output.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            errors.append(f"JSON invalido: {e}")
            return False, None, errors

        # Valida com Pydantic
        try:
            validated = GeminiAnalysisOutput(**data)
            return True, validated, []
        except ValidationError as e:
            for err in e.errors():
                errors.append(f"{err['loc']}: {err['msg']}")
            return False, None, errors

    def _get_prompt_version(self, db: Session) -> Optional[PromptVersion]:
        """Busca versao ativa do prompt de analise."""
        stmt = select(PromptVersion).where(
            PromptVersion.prompt_type == "analysis",
            PromptVersion.is_active == True,
        )
        return db.execute(stmt).scalar_one_or_none()

    def _transcribe_video(self, video: ViralVideo, db: Session) -> None:
        """Transcreve video usando Whisper."""
        if not video.video_file_path:
            raise ValueError("Video sem arquivo para transcrever")

        # Download do MinIO se necessario
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = Path(tmp_dir) / "video.mp4"
            self.storage.download_file(video.video_file_path, local_path)

            # Transcreve
            result = self.whisper.transcribe_video(local_path)

            video.transcription = result.text
            video.transcription_language = result.language
            video.transcription_confidence = Decimal(str(result.confidence))
            video.is_transcribed = True


# Singleton para uso global
analyst_agent = AnalystAgent()
