# 03 - Configurações, Schemas e Validação v2.0

## 3.1 Arquivo: `.env.example`

```env
# ============================================
# DATABASE
# ============================================
DB_USER=viral_admin
DB_PASSWORD=sua_senha_segura_aqui
DB_HOST=postgres
DB_PORT=5432
DB_NAME=viral_videos
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# ============================================
# REDIS
# ============================================
REDIS_URL=redis://redis:6379/0

# ============================================
# MINIO (Object Storage)
# ============================================
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=sua_senha_minio_aqui
MINIO_BUCKET=viral-videos
MINIO_SECURE=false

# ============================================
# APIs EXTERNAS
# ============================================
APIFY_TOKEN=apify_api_xxxxxxxxxx
GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
FAL_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# [NOVO] ElevenLabs (TTS Premium - Opcional)
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB

# ============================================
# LIMITES E CONFIGURAÇÕES
# ============================================
MAX_DAILY_VEO_GENERATIONS=10
MAX_DAILY_SCRAPING_PROFILES=20
MAX_DAILY_ANALYSES=50
MAX_DAILY_TTS_CHARACTERS=50000

# Thresholds de qualidade
MIN_VIEWS_THRESHOLD=10000
MIN_LIKES_THRESHOLD=1000
MIN_COMMENTS_THRESHOLD=100
MIN_STATISTICAL_SCORE=0.6
MIN_VIRALITY_SCORE=0.7

# Modo de teste
TEST_MODE=true

# ============================================
# [NOVO] ORÇAMENTO
# ============================================
DAILY_BUDGET_LIMIT_USD=20.00
MONTHLY_BUDGET_LIMIT_USD=500.00
BUDGET_WARNING_THRESHOLD=0.8
ABORT_ON_BUDGET_EXCEED=true

# ============================================
# [NOVO] TTS CONFIGURAÇÃO
# ============================================
TTS_PROVIDER=edge-tts
TTS_FALLBACK_PROVIDER=elevenlabs
TTS_VOICE_PT_BR=pt-BR-FranciscaNeural
TTS_VOICE_EN_US=en-US-JennyNeural
TTS_RATE=+0%
TTS_PITCH=+0Hz

# ============================================
# WHISPER (Transcrição Local)
# ============================================
# Para CPU-only com 15GB RAM, usar 'medium'
# Opções: tiny, base, small, medium, large, large-v2, large-v3
WHISPER_MODEL=medium

# ============================================
# CELERY
# ============================================
# Para 4 vCPUs e 15GB RAM, usar concurrency=2
CELERY_CONCURRENCY=2

# ============================================
# TIMEZONE
# ============================================
TZ=America/Sao_Paulo
```

---

## 3.2 Arquivo: `config/settings.py`

```python
"""
Configurações centralizadas do sistema v2.0.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional
from decimal import Decimal


class Settings(BaseSettings):
    """Configurações do sistema carregadas do .env"""
    
    # ========== Database ==========
    database_url: str = Field(..., description="URL de conexão PostgreSQL")
    
    # ========== Redis ==========
    redis_url: str = Field(default="redis://redis:6379/0")
    
    # ========== MinIO ==========
    minio_endpoint: str = Field(default="minio:9000")
    minio_access_key: str = Field(...)
    minio_secret_key: str = Field(...)
    minio_bucket: str = Field(default="viral-videos")
    minio_secure: bool = Field(default=False)
    
    # ========== APIs Externas ==========
    apify_token: str = Field(...)
    google_api_key: str = Field(...)
    openai_api_key: str = Field(...)
    fal_key: str = Field(...)
    
    # [NOVO] ElevenLabs
    elevenlabs_api_key: Optional[str] = Field(default=None)
    elevenlabs_voice_id: str = Field(default="pNInz6obpgDQGcFmaJgB")
    
    # ========== Limites Diários ==========
    max_daily_veo_generations: int = Field(default=10)
    max_daily_scraping_profiles: int = Field(default=20)
    max_daily_analyses: int = Field(default=50)
    max_daily_tts_characters: int = Field(default=50000)
    
    # ========== Thresholds de Qualidade ==========
    min_views_threshold: int = Field(default=10000)
    min_likes_threshold: int = Field(default=1000)
    min_comments_threshold: int = Field(default=100)
    min_statistical_score: float = Field(default=0.6)
    min_virality_score: float = Field(default=0.7)
    
    # ========== [NOVO] Orçamento ==========
    daily_budget_limit_usd: Decimal = Field(default=Decimal("20.00"))
    monthly_budget_limit_usd: Decimal = Field(default=Decimal("500.00"))
    budget_warning_threshold: float = Field(default=0.8)
    abort_on_budget_exceed: bool = Field(default=True)
    
    # ========== [NOVO] TTS ==========
    tts_provider: str = Field(default="edge-tts")
    tts_fallback_provider: str = Field(default="elevenlabs")
    tts_voice_pt_br: str = Field(default="pt-BR-FranciscaNeural")
    tts_voice_en_us: str = Field(default="en-US-JennyNeural")
    tts_rate: str = Field(default="+0%")
    tts_pitch: str = Field(default="+0Hz")
    
    # ========== Modo de Teste ==========
    test_mode: bool = Field(default=True)
    
    # ========== Whisper ==========
    whisper_model: str = Field(default="medium")
    
    # ========== Celery ==========
    celery_concurrency: int = Field(default=2)
    
    # ========== Timezone ==========
    tz: str = Field(default="America/Sao_Paulo")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    # ========== Propriedades Computadas ==========
    
    @property
    def veo_endpoint(self) -> str:
        if self.test_mode:
            return "fal-ai/veo3.1/fast"
        return "fal-ai/veo3.1"
    
    @property
    def veo_cost_per_generation(self) -> float:
        if self.test_mode:
            return 0.25
        return 0.50
    
    @property
    def elevenlabs_available(self) -> bool:
        return bool(self.elevenlabs_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

## 3.3 Arquivo: `models/schemas.py` [NOVO - Validação Pydantic]

```python
"""
Schemas Pydantic para validação de outputs estruturados.
Garante que outputs de Gemini e GPT-4o sejam válidos e consistentes.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum


# ============================================
# ENUMS
# ============================================

class HookTechnique(str, Enum):
    CURIOSITY_GAP = "curiosity_gap"
    PATTERN_INTERRUPT = "pattern_interrupt"
    BOLD_CLAIM = "bold_claim"
    QUESTION = "question"
    SHOCKING_STAT = "shocking_stat"
    CONTROVERSY = "controversy"
    TRANSFORMATION = "transformation"
    OTHER = "other"


class NarrativeStyle(str, Enum):
    TUTORIAL = "tutorial"
    STORY = "story"
    DEMONSTRATION = "demonstration"
    COMPARISON = "comparison"
    TRANSFORMATION = "transformation"
    BEHIND_SCENES = "behind_scenes"
    LISTICLE = "listicle"
    OTHER = "other"


class CTAType(str, Enum):
    COMMENT = "comment"
    LIKE = "like"
    SHARE = "share"
    FOLLOW = "follow"
    LINK = "link"
    SAVE = "save"
    OTHER = "other"


class TTSProvider(str, Enum):
    EDGE_TTS = "edge-tts"
    ELEVENLABS = "elevenlabs"


# ============================================
# SCHEMAS DE ANÁLISE (OUTPUT DO GEMINI)
# ============================================

class HookAnalysis(BaseModel):
    """Análise do hook (primeiros 3 segundos)"""
    duration_seconds: float = Field(ge=0, le=10, description="Duração do hook em segundos")
    technique: HookTechnique = Field(description="Técnica utilizada no hook")
    text_transcription: Optional[str] = Field(default=None, description="Texto falado no hook")
    visual_description: str = Field(description="Descrição visual do hook")
    effectiveness_score: float = Field(ge=0, le=1, description="Score de efetividade 0-1")


class DevelopmentAnalysis(BaseModel):
    """Análise do desenvolvimento do conteúdo"""
    narrative_style: NarrativeStyle = Field(description="Estilo narrativo")
    key_points: List[str] = Field(min_length=1, max_length=10, description="Pontos-chave")
    pacing: str = Field(description="Ritmo do conteúdo (fast, medium, slow)")
    retention_techniques: List[str] = Field(default=[], description="Técnicas de retenção")


class CTAAnalysis(BaseModel):
    """Análise do Call-to-Action"""
    type: CTAType = Field(description="Tipo de CTA")
    text: Optional[str] = Field(default=None, description="Texto do CTA")
    placement: str = Field(description="Posicionamento (start, middle, end)")
    effectiveness: float = Field(ge=0, le=1, default=0.5)


class VisualElements(BaseModel):
    """Análise dos elementos visuais"""
    lighting: str = Field(description="Descrição da iluminação")
    color_palette: List[str] = Field(default=[], description="Paleta de cores")
    camera_movements: List[str] = Field(default=[], description="Movimentos de câmera")
    text_overlays: bool = Field(default=False, description="Possui texto sobreposto")
    transitions: List[str] = Field(default=[], description="Tipos de transição")
    thumbnail_hook: Optional[str] = Field(default=None, description="Elemento de hook na thumbnail")


class AudioElements(BaseModel):
    """Análise dos elementos de áudio"""
    music_type: str = Field(description="Tipo de música (trending, original, none)")
    voice_tone: str = Field(description="Tom da voz (energetic, calm, serious)")
    sound_effects: bool = Field(default=False, description="Possui efeitos sonoros")
    music_bpm: Optional[int] = Field(default=None, ge=60, le=200)


class ViralFactors(BaseModel):
    """Fatores de viralização identificados"""
    trend_alignment: str = Field(description="Alinhamento com tendências")
    emotional_trigger: str = Field(description="Gatilho emocional principal")
    shareability_reason: str = Field(description="Motivo de compartilhamento")
    target_audience: str = Field(description="Público-alvo identificado")


class AnalysisScores(BaseModel):
    """Scores calculados pela análise"""
    virality_potential: float = Field(ge=0, le=1, description="Potencial de viralização")
    replicability: float = Field(ge=0, le=1, description="Facilidade de replicar")
    production_quality: float = Field(ge=0, le=1, description="Qualidade de produção")


class VideoAnalysisOutput(BaseModel):
    """Schema completo do output do Gemini"""
    hook: HookAnalysis
    development: DevelopmentAnalysis
    cta: CTAAnalysis
    visual_analysis: VisualElements
    audio_analysis: AudioElements
    viral_factors: ViralFactors
    scores: AnalysisScores
    transcription_full: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Ignora campos extras do Gemini


# ============================================
# SCHEMAS DE ESTRATÉGIA (OUTPUT DO GPT-4o)
# ============================================

class ScriptSection(BaseModel):
    """Seção do roteiro"""
    duracao: str = Field(description="Duração da seção (ex: '0-3s')")
    texto_falado: str = Field(min_length=1, description="Texto a ser narrado")
    acao_visual: Optional[str] = Field(default=None, description="Ação visual")


class VeoPrompt(BaseModel):
    """Prompt individual para o Veo 3.1"""
    scene: int = Field(ge=1, description="Número da cena")
    duration: str = Field(description="Duração (ex: '4s', '6s')")
    prompt: str = Field(min_length=10, description="Prompt descritivo")
    camera: Optional[str] = Field(default=None, description="Movimento de câmera")
    lighting: Optional[str] = Field(default=None, description="Iluminação")
    
    @validator('duration')
    def validate_duration(cls, v):
        # Remove 's' e verifica se é número válido
        num = v.replace('s', '').strip()
        try:
            seconds = float(num)
            if seconds > 8:
                raise ValueError("Veo 3.1 suporta máximo de 8 segundos por cena")
        except ValueError:
            raise ValueError(f"Duração inválida: {v}")
        return v


class PublicationConfig(BaseModel):
    """Configurações de publicação"""
    caption: str = Field(min_length=1, description="Legenda do post")
    hashtags: List[str] = Field(min_length=1, max_length=30, description="Hashtags")
    melhor_horario: Optional[str] = Field(default=None, description="Melhor horário")
    primeira_frase_hook: Optional[str] = Field(default=None)


class StrategyOutput(BaseModel):
    """Schema completo do output de estratégia"""
    titulo: str = Field(min_length=1, max_length=255)
    conceito_central: str = Field(min_length=10)
    roteiro: Dict[str, ScriptSection] = Field(description="Seções: hook, desenvolvimento, cta")
    veo_prompts: List[VeoPrompt] = Field(min_length=1, max_length=10)
    publicacao: PublicationConfig
    
    @validator('veo_prompts')
    def validate_total_duration(cls, v):
        total = 0
        for prompt in v:
            num = prompt.duration.replace('s', '').strip()
            total += float(num)
        if total > 60:
            raise ValueError(f"Duração total ({total}s) excede 60 segundos")
        return v
    
    class Config:
        extra = "ignore"


# ============================================
# SCHEMAS DE TTS [NOVO]
# ============================================

class TTSConfig(BaseModel):
    """Configuração de Text-to-Speech"""
    provider: TTSProvider = Field(default=TTSProvider.EDGE_TTS)
    voice: str = Field(default="pt-BR-FranciscaNeural")
    rate: str = Field(default="+0%", description="Velocidade (-50% a +50%)")
    pitch: str = Field(default="+0Hz", description="Tom (-50Hz a +50Hz)")
    
    @validator('rate')
    def validate_rate(cls, v):
        if not v.endswith('%'):
            raise ValueError("Rate deve terminar com % (ex: +10%)")
        return v


class TTSResult(BaseModel):
    """Resultado da geração de TTS"""
    provider_used: TTSProvider
    audio_path: str
    duration_seconds: float
    characters_used: int
    cost_usd: Decimal = Field(default=Decimal("0"))


# ============================================
# SCHEMAS DE PRODUÇÃO [NOVO]
# ============================================

class ProductionClip(BaseModel):
    """Informações de um clipe gerado"""
    scene: int
    prompt: str
    video_path: str
    duration_seconds: float
    cost_usd: Decimal
    status: str = "success"
    error: Optional[str] = None


class ProductionResult(BaseModel):
    """Resultado completo da produção"""
    production_id: int
    strategy_id: int
    
    # TTS
    tts_result: TTSResult
    
    # Vídeo
    clips: List[ProductionClip]
    concatenated_path: str
    final_path: str
    
    # Custos
    tts_cost_usd: Decimal
    veo_cost_usd: Decimal
    total_cost_usd: Decimal
    
    # Metadados
    final_duration_seconds: float
    status: str
```

---

## 3.4 Arquivo: `models/validators.py` [NOVO]

```python
"""
Validadores para garantir outputs estruturados e consistentes.
"""

import json
import re
from typing import Tuple, Optional, Any, Type
from pydantic import BaseModel, ValidationError

from models.schemas import VideoAnalysisOutput, StrategyOutput


def extract_json_from_response(response: str) -> str:
    """
    Extrai JSON de uma resposta que pode conter markdown ou texto extra.
    """
    # Remove blocos de código markdown
    response = response.strip()
    
    # Tenta extrair JSON de blocos ```json
    json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
    if json_block_match:
        return json_block_match.group(1).strip()
    
    # Tenta extrair JSON de blocos ``` genéricos
    code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    # Tenta encontrar JSON puro (começa com { e termina com })
    json_match = re.search(r'(\{[\s\S]*\})', response)
    if json_match:
        return json_match.group(1).strip()
    
    return response


def validate_analysis_output(response: str) -> Tuple[bool, Optional[VideoAnalysisOutput], Optional[str]]:
    """
    Valida o output do Gemini contra o schema de análise.
    
    Returns:
        Tuple[is_valid, parsed_output, error_message]
    """
    try:
        # Extrai JSON
        json_str = extract_json_from_response(response)
        
        # Tenta parsear
        data = json.loads(json_str)
        
        # Valida contra schema
        output = VideoAnalysisOutput(**data)
        
        return True, output, None
        
    except json.JSONDecodeError as e:
        return False, None, f"JSON inválido: {str(e)}"
    except ValidationError as e:
        errors = e.errors()
        error_messages = [f"{err['loc']}: {err['msg']}" for err in errors]
        return False, None, f"Validação falhou: {'; '.join(error_messages)}"
    except Exception as e:
        return False, None, f"Erro inesperado: {str(e)}"


def validate_strategy_output(response: str) -> Tuple[bool, Optional[StrategyOutput], Optional[str]]:
    """
    Valida o output do GPT-4o contra o schema de estratégia.
    
    Returns:
        Tuple[is_valid, parsed_output, error_message]
    """
    try:
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)
        output = StrategyOutput(**data)
        return True, output, None
        
    except json.JSONDecodeError as e:
        return False, None, f"JSON inválido: {str(e)}"
    except ValidationError as e:
        errors = e.errors()
        error_messages = [f"{err['loc']}: {err['msg']}" for err in errors]
        return False, None, f"Validação falhou: {'; '.join(error_messages)}"
    except Exception as e:
        return False, None, f"Erro inesperado: {str(e)}"


def safe_parse_json(response: str, schema: Type[BaseModel]) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Parser genérico que valida qualquer response contra um schema Pydantic.
    """
    try:
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)
        output = schema(**data)
        return True, output, None
    except Exception as e:
        return False, None, str(e)
```

---

## 3.5 Arquivo: `requirements.txt` [ATUALIZADO]

```text
# Core
python-dotenv==1.0.1
pydantic==2.5.3
pydantic-settings==2.1.0

# Framework de Agentes
agno>=0.1.0

# AI/ML
openai==1.6.1
google-generativeai==0.3.2
fal-client==0.3.0
openai-whisper==20231117

# [NOVO] TTS
edge-tts==6.1.9
elevenlabs==0.2.27

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23

# Storage
minio==7.2.0

# Task Queue
celery==5.3.4
redis==5.0.1

# API
fastapi==0.104.1
uvicorn==0.24.0.post1

# HTTP
requests==2.31.0
httpx==0.25.2

# Audio/Video
pydub==0.25.1
mutagen==1.47.0

# Utilities
python-multipart==0.0.6
aiofiles==23.2.1

# Dev/Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```
