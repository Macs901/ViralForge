"""Analyst Agent - Responsavel por analisar videos usando Gemini ou Claude."""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import tempfile
import time
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

import anthropic
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
    """Schema para analise do hook (0-3 segundos)."""

    opening_type: str = Field(description="Tipo: pergunta|afirmacao|visual|choque|curiosidade|comando|vulnerabilidade")
    attention_technique: str = Field(description="Tecnica de captura de atencao usada")
    first_words: str = Field(description="Primeiras palavras exatas ou descricao visual")
    visual_hook: str = Field(default="", description="Descricao do gancho visual inicial")
    hook_score: float = Field(ge=0, le=1, description="Score do hook (0-1)")


class VisualElements(BaseModel):
    """Schema para elementos visuais do video."""

    dominant_colors: list[str] = Field(description="Cores dominantes (ex: azul, branco, vermelho)")
    framing: str = Field(description="Enquadramento: close|medio|aberto|variado")
    lighting: str = Field(description="Iluminacao: natural|artificial|ring_light|mista")
    scenario: str = Field(description="Cenario: casa|escritorio|externo|estudio|neutro")
    text_on_screen: bool = Field(description="Tem texto na tela?")
    text_style: str = Field(default="", description="Estilo do texto: fonte, cor, posicao")
    text_timing: str = Field(default="", description="Timing: antes_fala|junto_fala|depois_fala")
    transitions: list[str] = Field(default=[], description="Tipos de transicoes usadas")
    cuts_per_minute: int = Field(default=0, description="Estimativa de cortes por minuto")
    thumbnail_elements: str = Field(default="", description="Elementos que funcionariam como thumbnail")


class AudioElements(BaseModel):
    """Schema para elementos de audio."""

    voice_type: str = Field(description="Tipo: direta|voz_off|mista|sem_voz")
    voice_tone: str = Field(description="Tom: intimo|energetico|didatico|humorado|serio|provocativo")
    music_present: bool = Field(description="Tem musica de fundo?")
    music_type: str = Field(default="", description="Tipo de musica: trending|instrumental|dramatica|alegre")
    music_volume: str = Field(default="", description="Volume: baixo|medio|alto|compete_com_voz")
    sound_effects: bool = Field(default=False, description="Usa efeitos sonoros?")


class PerformanceElements(BaseModel):
    """Schema para elementos de performance/apresentacao."""

    facial_expressions: list[str] = Field(description="Expressoes faciais predominantes")
    body_language: str = Field(description="Linguagem corporal: estatico|gestual|muito_expressivo")
    eye_contact: str = Field(description="Contato visual: direto|desvia|misto")
    energy_level: str = Field(description="Nivel de energia: baixo|medio|alto")
    authenticity_feel: str = Field(description="Sensacao de autenticidade: ensaiado|natural|espontaneo")
    catchphrases: list[str] = Field(default=[], description="Bordoes ou frases de efeito usadas")


class DevelopmentAnalysis(BaseModel):
    """Schema para analise do desenvolvimento (3s ate 80%)."""

    structure: str = Field(description="Estrutura: problema_solucao|antes_depois|lista|storytelling|tutorial|dor_virada")
    key_points: list[str] = Field(description="Pontos principais abordados")
    pacing: str = Field(description="Ritmo: rapido|moderado|lento|variado")
    retention_techniques: list[str] = Field(description="Tecnicas de retencao usadas")
    narrative_arc: str = Field(default="", description="Arco narrativo: linear|crescente|surpresa|ciclico")


class CTAAnalysis(BaseModel):
    """Schema para analise do CTA (ultimos 20%)."""

    cta_type: str = Field(description="Tipo: seguir|curtir|comentar|compartilhar|salvar|link|multiplo|nenhum")
    cta_text: str = Field(description="Texto exato do CTA")
    cta_technique: str = Field(default="", description="Tecnica: comando|convite|gatilho_escassez|prova_social")
    urgency_level: str = Field(description="Urgencia: baixo|medio|alto")
    cta_score: float = Field(ge=0, le=1, description="Score do CTA (0-1)")


class ViralFactors(BaseModel):
    """Schema para fatores de viralizacao."""

    emotional_triggers: list[str] = Field(description="Gatilhos emocionais ativados")
    shareability_factors: list[str] = Field(description="Por que alguem compartilharia")
    trend_alignment: str = Field(description="Alinhamento com tendencias atuais")
    controversy_level: float = Field(ge=0, le=1, description="Nivel de controversia (0-1)")
    relatability: str = Field(default="", description="Nivel de identificacao do publico")
    novelty_factor: str = Field(default="", description="Fator novidade/surpresa")
    save_worthy: bool = Field(default=False, description="Conteudo que vale salvar?")


class ReplicationGuide(BaseModel):
    """Schema para guia de replicacao."""

    equipment_needed: list[str] = Field(default=[], description="Equipamentos necessarios")
    difficulty_level: str = Field(default="facil", description="Dificuldade: facil|medio|dificil")
    time_to_produce: str = Field(default="", description="Tempo estimado de producao")
    key_elements_to_copy: list[str] = Field(default=[], description="Elementos essenciais para replicar")
    adaptations_suggested: list[str] = Field(default=[], description="Sugestoes de adaptacao")


class GeminiAnalysisOutput(BaseModel):
    """Schema completo de output da analise."""

    hook_analysis: HookAnalysis
    visual_elements: VisualElements
    audio_elements: AudioElements
    performance_elements: PerformanceElements
    development: DevelopmentAnalysis
    cta_analysis: CTAAnalysis
    viral_factors: ViralFactors
    replication_guide: ReplicationGuide
    virality_score: float = Field(ge=0, le=1, description="Score de viralidade")
    replicability_score: float = Field(ge=0, le=1, description="Score de replicabilidade")
    production_quality_score: float = Field(ge=0, le=1, description="Score de qualidade")
    summary: str = Field(description="Resumo da analise em 2-3 frases")
    script_suggestion: str = Field(default="", description="Sugestao de roteiro baseado neste video")


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
    """Agent responsavel por analisar videos virais usando Gemini ou Claude.

    Pipeline:
    1. Download do video (se necessario)
    2. Transcricao com Whisper (se necessario)
    3. Analise com Gemini ou Claude (configuravel)
    4. Validacao JSON com Pydantic
    5. Armazenamento no banco
    """

    ANALYSIS_PROMPT = """Voce e um ANALISTA ESPECIALISTA em videos virais para Instagram Reels, TikTok e YouTube Shorts.
Sua missao e fazer uma ANALISE SEMANTICA COMPLETA do video, extraindo todos os padroes de viralizacao.

## METODOLOGIA DE ANALISE

### ESTRUTURA TEMPORAL (Analise por partes)
- **HOOK (0-3 segundos)**: O que aparece/e dito para prender atencao
- **DESENVOLVIMENTO (3s ate 80%)**: Estrutura e entrega do conteudo
- **CTA (ultimos 20%)**: Como finaliza e pede acao

### ELEMENTOS VISUAIS (Analise detalhada)
- Cores dominantes e paleta cromatica
- Enquadramento (close, medio, aberto)
- Iluminacao (natural, artificial, ring light)
- Cenario e ambiente
- Texto na tela (fonte, cor, posicao, timing)
- Transicoes e cortes (ritmo de edicao)

### ELEMENTOS DE AUDIO
- Fala direta vs voz em off
- Tom de voz (intimo, energetico, didatico)
- Musica (tipo, volume, timing)
- Efeitos sonoros

### ELEMENTOS DE PERFORMANCE
- Expressoes faciais
- Linguagem corporal
- Contato visual com camera
- Bordoes ou frases de efeito

---

## VIDEO A ANALISAR

**Transcricao:**
{transcription}

**Metricas (prova social):**
- Views: {views:,}
- Likes: {likes:,}
- Comentarios: {comments:,}
- Duracao: {duration}s

**Caption Original:**
{caption}

---

## PADROES DE VIRALIZACAO QUE VOCE CONHECE

### Hooks que Funcionam:
- Pergunta direta ("Voce sabia que...")
- Afirmacao chocante ("Ninguem fala sobre isso")
- Comando ("Para um segundo")
- Inicio no meio ("Sabe quando...")
- Promessa de valor ("3 coisas que...")
- Vulnerabilidade ("Teve um dia que...")

### Estruturas que Viralizam:
- Problema -> Solucao
- Antes -> Depois
- Dor -> Identificacao -> Virada -> Convite
- Lista (3-5 itens)
- Storytelling (jornada)
- Tutorial passo a passo

### CTAs que Geram Acao:
- "Comenta [PALAVRA] que eu te mando..."
- "Salva pra nao esquecer"
- "Envia pra alguem que precisa"
- "Segue pra mais..."

---

## OUTPUT ESPERADO

Retorne um JSON com a seguinte estrutura EXATA:

```json
{{
    "hook_analysis": {{
        "opening_type": "pergunta|afirmacao|visual|choque|curiosidade|comando|vulnerabilidade",
        "attention_technique": "descricao detalhada da tecnica usada",
        "first_words": "primeiras palavras exatas ditas",
        "visual_hook": "descricao do gancho visual nos primeiros segundos",
        "hook_score": 0.0-1.0
    }},
    "visual_elements": {{
        "dominant_colors": ["cor1", "cor2", "cor3"],
        "framing": "close|medio|aberto|variado",
        "lighting": "natural|artificial|ring_light|mista",
        "scenario": "casa|escritorio|externo|estudio|neutro",
        "text_on_screen": true|false,
        "text_style": "descricao: fonte grande branca centralizada",
        "text_timing": "antes_fala|junto_fala|depois_fala",
        "transitions": ["corte_seco", "zoom", "fade"],
        "cuts_per_minute": 10,
        "thumbnail_elements": "elementos que funcionariam como thumb"
    }},
    "audio_elements": {{
        "voice_type": "direta|voz_off|mista|sem_voz",
        "voice_tone": "intimo|energetico|didatico|humorado|serio|provocativo",
        "music_present": true|false,
        "music_type": "trending|instrumental|dramatica|alegre",
        "music_volume": "baixo|medio|alto|compete_com_voz",
        "sound_effects": true|false
    }},
    "performance_elements": {{
        "facial_expressions": ["sorriso", "surpresa", "seriedade"],
        "body_language": "estatico|gestual|muito_expressivo",
        "eye_contact": "direto|desvia|misto",
        "energy_level": "baixo|medio|alto",
        "authenticity_feel": "ensaiado|natural|espontaneo",
        "catchphrases": ["bordao1", "bordao2"]
    }},
    "development": {{
        "structure": "problema_solucao|antes_depois|lista|storytelling|tutorial|dor_virada",
        "key_points": ["ponto principal 1", "ponto principal 2"],
        "pacing": "rapido|moderado|lento|variado",
        "retention_techniques": ["tecnica1", "tecnica2"],
        "narrative_arc": "linear|crescente|surpresa|ciclico"
    }},
    "cta_analysis": {{
        "cta_type": "seguir|curtir|comentar|compartilhar|salvar|link|multiplo|nenhum",
        "cta_text": "texto exato do CTA",
        "cta_technique": "comando|convite|gatilho_escassez|prova_social",
        "urgency_level": "baixo|medio|alto",
        "cta_score": 0.0-1.0
    }},
    "viral_factors": {{
        "emotional_triggers": ["curiosidade", "identificacao", "surpresa"],
        "shareability_factors": ["por que alguem compartilharia"],
        "trend_alignment": "descricao do alinhamento com trends",
        "controversy_level": 0.0-1.0,
        "relatability": "descricao do nivel de identificacao",
        "novelty_factor": "o que tem de novo/unico",
        "save_worthy": true|false
    }},
    "replication_guide": {{
        "equipment_needed": ["celular", "ring light", "microfone"],
        "difficulty_level": "facil|medio|dificil",
        "time_to_produce": "30 minutos",
        "key_elements_to_copy": ["elemento essencial 1", "elemento 2"],
        "adaptations_suggested": ["adaptacao para outro nicho"]
    }},
    "virality_score": 0.0-1.0,
    "replicability_score": 0.0-1.0,
    "production_quality_score": 0.0-1.0,
    "summary": "resumo da analise em 2-3 frases explicando o que faz esse video funcionar",
    "script_suggestion": "sugestao de roteiro de 30-60s baseado nos padroes deste video"
}}
```

REGRAS CRITICAS:
- Retorne APENAS o JSON, sem texto antes ou depois
- Todos os scores entre 0.0 e 1.0
- Seja ESPECIFICO nas descricoes, nao generico
- Analise o VIDEO visualmente (cores, enquadramento, expressoes)
- Considere contexto BRASILEIRO de redes sociais
- O script_suggestion deve ser um roteiro PRONTO para gravar
"""

    def __init__(self, provider: Optional[Literal["gemini", "claude"]] = None):
        """Inicializa Analyst Agent.

        Args:
            provider: Provider de analise (gemini ou claude). Se None, usa config.
        """
        self.provider = provider or settings.video_analysis_provider
        self.gemini_model = None
        self.claude_client = None

        # Inicializa o provider apropriado
        if self.provider == "claude":
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY nao configurado")
            self.claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            if not settings.google_api_key:
                raise RuntimeError("GOOGLE_API_KEY nao configurado")
            genai.configure(api_key=settings.google_api_key)
            self.gemini_model = genai.GenerativeModel(settings.gemini_model)

        self.budget = budget_tools
        self.whisper = whisper_tools
        self.storage = storage_tools

    def analyze(
        self,
        video_id: int,
        force: bool = False,
        retry_on_invalid: bool = True,
    ) -> AnalystResult:
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
            budget_key = "claude" if self.provider == "claude" else "gemini"
            can_run, cost, msg = self.budget.check_budget(budget_key, 1)
            if not can_run:
                raise RuntimeError(f"Budget insuficiente: {msg}")

            # Garante que video tem transcricao
            if not video.transcription:
                if not video.is_transcribed and video.video_file_path:
                    print(f"[Analyst] Transcrevendo video {video_id}...")
                    self._transcribe_video(video, db)
                else:
                    raise ValueError("Video sem transcricao disponivel")

            prompt = self._build_prompt(video)

            # Executa analise
            print(f"[Analyst] Analisando video {video_id} com {self.provider}...")
            analysis_output, tokens_used = self._call_model(video, prompt)

            # Valida output
            is_valid, validated_output, validation_errors = self._validate_output(analysis_output)

            # Retry uma vez se JSON vier invalido
            if not is_valid and retry_on_invalid:
                retry_output, retry_tokens = self._retry_invalid(prompt, validation_errors)
                if retry_output:
                    analysis_output = retry_output
                    tokens_used = (tokens_used or 0) + (retry_tokens or 0)
                    is_valid, validated_output, validation_errors = self._validate_output(analysis_output)

            # Busca versao do prompt
            prompt_version = self._get_prompt_version(db)

            # Cria ou atualiza analise
            analysis = video.analysis or VideoAnalysis(video_id=video_id)

            if validated_output:
                # Analise estrutural
                analysis.hook_analysis = validated_output.hook_analysis.model_dump()
                analysis.development = validated_output.development.model_dump()
                analysis.cta_analysis = validated_output.cta_analysis.model_dump()
                analysis.viral_factors = validated_output.viral_factors.model_dump()

                # Elementos visuais/audio/performance (analise semantica completa)
                analysis.visual_elements = validated_output.visual_elements.model_dump()
                analysis.audio_elements = validated_output.audio_elements.model_dump()
                analysis.performance_elements = validated_output.performance_elements.model_dump()
                analysis.replication_guide = validated_output.replication_guide.model_dump()
                analysis.script_suggestion = validated_output.script_suggestion

                # Scores
                analysis.virality_score = Decimal(str(validated_output.virality_score))
                analysis.replicability_score = Decimal(str(validated_output.replicability_score))
                analysis.production_quality_score = Decimal(str(validated_output.production_quality_score))

            analysis.is_valid_json = is_valid
            analysis.validation_errors = {"errors": validation_errors} if validation_errors else None
            analysis.raw_gemini_response = analysis_output  # Campo mantido por compatibilidade
            analysis.prompt_version_id = prompt_version.id if prompt_version else None
            analysis.tokens_used = tokens_used
            analysis.analysis_cost_usd = Decimal(str(settings.video_analysis_cost))

            if not video.analysis:
                db.add(analysis)

            # Atualiza video
            video.is_analyzed = True

            # Registra custo
            self.budget.register_cost(budget_key, Decimal(str(settings.video_analysis_cost)), 1, db)
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
                cost_usd=float(settings.video_analysis_cost),
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

    def _build_prompt(self, video: ViralVideo) -> str:
        """Monta prompt base de analise."""
        return self.ANALYSIS_PROMPT.format(
            transcription=video.transcription or "Nao disponivel",
            views=video.views_count,
            likes=video.likes_count,
            comments=video.comments_count,
            duration=video.duration_seconds or "Desconhecida",
            caption=video.caption or "Sem caption",
        )

    def _call_model(self, video: ViralVideo, prompt: str) -> tuple[str, int]:
        """Dispatcher: chama o provider configurado (Gemini ou Claude)."""
        if self.provider == "claude":
            return self._call_claude(video, prompt)
        return self._call_gemini(video, prompt)

    def _call_gemini(self, video: ViralVideo, prompt: str) -> tuple[str, int]:
        """Chama Gemini; tenta vision com video e faz fallback para texto."""
        response = None
        tokens_used = 0

        # Tenta Gemini Vision usando o video bruto se estiver armazenado
        if video.video_file_path:
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    local_path = Path(tmp_dir) / "video.mp4"
                    self.storage.download_file(video.video_file_path, local_path)
                    uploaded_file = genai.upload_file(path=str(local_path))
                    try:
                        while uploaded_file.state.name == "PROCESSING":
                            time.sleep(2)
                            uploaded_file = genai.get_file(uploaded_file.name)
                        response = self.gemini_model.generate_content(
                            [uploaded_file, prompt],
                            generation_config=genai.GenerationConfig(
                                temperature=0.3,
                                max_output_tokens=2000,
                            ),
                        )
                    finally:
                        try:
                            genai.delete_file(uploaded_file.name)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Analyst] Gemini Vision falhou, usando transcricao: {e}")

        # Fallback para prompt textual se Vision falhar ou video nao existir
        if response is None:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2000,
                ),
            )

        tokens_used = (
            response.usage_metadata.total_token_count if response.usage_metadata else 0
        )

        return response.text or "", tokens_used

    def _call_claude(self, video: ViralVideo, prompt: str) -> tuple[str, int]:
        """Chama Claude; suporta vision com video se disponivel."""
        messages_content = []

        # Se tiver video armazenado, tenta usar vision
        if video.video_file_path:
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    local_path = Path(tmp_dir) / "video.mp4"
                    self.storage.download_file(video.video_file_path, local_path)

                    # Le o video e converte para base64
                    with open(local_path, "rb") as f:
                        video_data = base64.standard_b64encode(f.read()).decode("utf-8")

                    messages_content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "video/mp4",
                            "data": video_data,
                        },
                    })
            except Exception as e:
                print(f"[Analyst] Claude Vision falhou, usando transcricao: {e}")

        # Adiciona prompt de texto
        messages_content.append({"type": "text", "text": prompt})

        response = self.claude_client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2000,
            messages=[{"role": "user", "content": messages_content}],
        )

        # Extrai texto da resposta
        text_output = ""
        for block in response.content:
            if block.type == "text":
                text_output += block.text

        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return text_output, tokens_used

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
            json_str = self._extract_json(output)
            if not json_str:
                errors.append("JSON nao encontrado no output")
                return False, None, errors
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            errors.append(f"JSON invalido: {e}")
            return False, None, errors
        except Exception as e:
            errors.append(str(e))
            return False, None, errors

        # Valida com Pydantic
        try:
            validated = GeminiAnalysisOutput(**data)
            return True, validated, []
        except ValidationError as e:
            for err in e.errors():
                path = ".".join(str(p) for p in err.get("loc", []))
                errors.append(f"{path}: {err['msg']}")
            return False, None, errors

    def _retry_invalid(self, prompt: str, errors: list[str]) -> tuple[Optional[str], int]:
        """Reforca prompt e tenta novamente quando JSON vem invalido."""
        retry_prompt = (
            f"{prompt}\n\n"
            "ATENCAO: sua resposta anterior veio com erros de validacao:\n"
            f"- {'; '.join(errors)}\n\n"
            "Retorne APENAS o JSON valido conforme o schema solicitado, sem markdown."
        )

        if self.provider == "claude":
            response = self.claude_client.messages.create(
                model=settings.anthropic_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": retry_prompt}],
            )
            text_output = ""
            for block in response.content:
                if block.type == "text":
                    text_output += block.text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            return text_output, tokens_used
        else:
            response = self.gemini_model.generate_content(
                retry_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                ),
            )
            tokens_used = (
                response.usage_metadata.total_token_count if response.usage_metadata else 0
            )
            return response.text or "", tokens_used

    @staticmethod
    def _extract_json(response_text: str) -> Optional[str]:
        """Extrai blob JSON de texto, aceitando cercas markdown."""
        if not response_text:
            return None
        text = response_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                candidate = parts[1].strip()
                if candidate.lower().startswith("json"):
                    candidate = candidate[4:].strip()
                text = candidate
        if text.startswith("{") and text.endswith("}"):
            return text
        # Busca primeiro bloco JSON
        import re

        match = re.search(r"(\{[\s\S]*\})", text)
        return match.group(1).strip() if match else None

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


# Lazy initialization - instanciado sob demanda
_analyst_agent_instance: Optional[AnalystAgent] = None


def get_analyst_agent(provider: Optional[Literal["gemini", "claude"]] = None) -> AnalystAgent:
    """Retorna instancia do AnalystAgent (lazy init).

    Args:
        provider: Provider especifico (gemini ou claude). Se None, usa config.
    """
    global _analyst_agent_instance

    # Se provider especifico, cria nova instancia
    if provider:
        return AnalystAgent(provider=provider)

    # Singleton para provider padrao
    if _analyst_agent_instance is None:
        _analyst_agent_instance = AnalystAgent()
    return _analyst_agent_instance
