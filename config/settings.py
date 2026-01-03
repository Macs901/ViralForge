"""Configuracoes centralizadas do ViralForge usando Pydantic Settings."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracoes unificadas do ViralForge v2.0."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === APP ===
    app_name: str = "ViralForge"
    app_env: Literal["development", "production", "testing"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    log_level: str = "INFO"
    timezone: str = Field(default="America/Sao_Paulo", alias="TZ")
    api_token: Optional[str] = Field(default=None, alias="API_TOKEN")
    api_rate_limit_window_seconds: int = Field(
        default=60, alias="API_RATE_LIMIT_WINDOW"
    )
    api_rate_limit_max_requests: int = Field(
        default=120, alias="API_RATE_LIMIT_MAX"
    )

    # === DATABASE ===
    database_url: str = Field(
        default="postgresql+asyncpg://viral_admin:senha@postgres-prd:5432/viral_videos",
        alias="DATABASE_URL"
    )
    database_url_sync: Optional[str] = Field(default=None, alias="DATABASE_URL_SYNC")

    # === REDIS ===
    redis_url: str = Field(
        default="redis://redis-node-1-prd:6379/0",
        alias="REDIS_URL"
    )

    # === STORAGE (MinIO) ===
    minio_endpoint: str = Field(default="minio-prd:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="viral-videos", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # === EXTERNAL APIs ===
    # Apify - Instagram Scraping
    apify_token: str = Field(default="", alias="APIFY_TOKEN")

    # Meta Graph API - Instagram Business (optional, for downloader fallback)
    meta_access_token: Optional[str] = Field(default=None, alias="META_ACCESS_TOKEN")

    # Google Gemini - Video Analysis
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-pro", alias="GEMINI_MODEL")
    google_service_account_json: Optional[str] = Field(
        default=None, alias="GOOGLE_SERVICE_ACCOUNT_JSON"
    )
    google_service_account_file: Optional[str] = Field(
        default=None, alias="GOOGLE_SERVICE_ACCOUNT_FILE"
    )
    google_sheets_spreadsheet_id: Optional[str] = Field(
        default=None, alias="GOOGLE_SHEETS_SPREADSHEET_ID"
    )
    google_sheets_tab_videos: str = Field(default="Videos", alias="GOOGLE_SHEETS_TAB_VIDEOS")
    google_sheets_tab_strategies: str = Field(
        default="Strategies", alias="GOOGLE_SHEETS_TAB_STRATEGIES"
    )
    google_sheets_tab_productions: str = Field(
        default="Productions", alias="GOOGLE_SHEETS_TAB_PRODUCTIONS"
    )
    google_sheets_tab_status: str = Field(default="Status", alias="GOOGLE_SHEETS_TAB_STATUS")

    # Anthropic - Claude (Video Analysis alternative)
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL")

    # Video Analysis Provider (gemini | claude)
    video_analysis_provider: Literal["gemini", "claude"] = Field(
        default="gemini",
        alias="VIDEO_ANALYSIS_PROVIDER"
    )

    # OpenAI - Strategy Generation
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    # Fal.ai - Veo 3.1 Video Generation
    fal_key: str = Field(default="", alias="FAL_KEY")
    veo_mode: Literal["test", "production"] = Field(default="test", alias="VEO_MODE")

    # ElevenLabs - Premium TTS (optional)
    elevenlabs_api_key: Optional[str] = Field(default=None, alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(
        default="pNInz6obpgDQGcFmaJgB",
        alias="ELEVENLABS_VOICE_ID"
    )

    # === DAILY LIMITS ===
    max_daily_veo_generations: int = Field(default=10, alias="MAX_DAILY_VEO_GENERATIONS")
    max_daily_scraping_profiles: int = Field(default=20, alias="MAX_DAILY_SCRAPING_PROFILES")
    max_daily_analyses: int = Field(default=50, alias="MAX_DAILY_ANALYSES")
    max_daily_tts_characters: int = Field(default=50000, alias="MAX_DAILY_TTS_CHARACTERS")

    # === QUALITY THRESHOLDS ===
    min_views_threshold: int = Field(default=10000, alias="MIN_VIEWS_THRESHOLD")
    min_likes_threshold: int = Field(default=1000, alias="MIN_LIKES_THRESHOLD")
    min_comments_threshold: int = Field(default=100, alias="MIN_COMMENTS_THRESHOLD")
    min_statistical_score: float = Field(default=0.6, alias="MIN_STATISTICAL_SCORE")
    min_virality_score: float = Field(default=0.7, alias="MIN_VIRALITY_SCORE")

    # === BUDGET CONTROL ===
    daily_budget_limit_usd: Decimal = Field(
        default=Decimal("20.00"),
        alias="DAILY_BUDGET_LIMIT_USD"
    )
    monthly_budget_limit_usd: Decimal = Field(
        default=Decimal("500.00"),
        alias="MONTHLY_BUDGET_LIMIT_USD"
    )
    budget_warning_threshold: float = Field(default=0.8, alias="BUDGET_WARNING_THRESHOLD")
    abort_on_budget_exceed: bool = Field(default=True, alias="ABORT_ON_BUDGET_EXCEED")

    # === TEXT-TO-SPEECH ===
    tts_provider: Literal["edge-tts", "elevenlabs"] = Field(
        default="edge-tts",
        alias="TTS_PROVIDER"
    )
    tts_fallback_provider: Literal["edge-tts", "elevenlabs"] = Field(
        default="elevenlabs",
        alias="TTS_FALLBACK_PROVIDER"
    )
    tts_voice_pt_br: str = Field(
        default="pt-BR-FranciscaNeural",
        alias="TTS_VOICE_PT_BR"
    )
    tts_voice_en_us: str = Field(
        default="en-US-JennyNeural",
        alias="TTS_VOICE_EN_US"
    )
    tts_rate: str = Field(default="+0%", alias="TTS_RATE")
    tts_pitch: str = Field(default="+0Hz", alias="TTS_PITCH")

    # === WHISPER ===
    whisper_provider: Literal["local", "groq"] = Field(
        default="local",
        alias="WHISPER_PROVIDER",
        description="Provider de transcricao: local (Whisper local) ou groq (Groq API, gratis e mais rapido)"
    )
    whisper_model: Literal["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"] = Field(
        default="medium",
        alias="WHISPER_MODEL"
    )
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_whisper_model: str = Field(
        default="whisper-large-v3",
        alias="GROQ_WHISPER_MODEL",
        description="Modelo Whisper no Groq: whisper-large-v3 ou whisper-large-v3-turbo"
    )

    # === CELERY ===
    celery_concurrency: int = Field(default=2, alias="CELERY_CONCURRENCY")

    # === PATHS ===
    base_path: Path = Path(".")
    data_path: Path = Field(default=Path("data"), alias="DATA_PATH")
    temp_path: Path = Field(default=Path("data/temp"), alias="TEMP_PATH")
    music_path: Path = Field(default=Path("assets/music"), alias="MUSIC_PATH")
    video_output_dir: Path = Field(default=Path("data/videos"), alias="VIDEO_OUTPUT_DIR")

    # === COST CONFIGURATION (USD) ===
    cost_veo_test: Decimal = Decimal("0.25")
    cost_veo_production: Decimal = Decimal("0.50")
    cost_gemini_per_video: Decimal = Decimal("0.002")
    cost_claude_per_video: Decimal = Decimal("0.005")  # Claude Sonnet ~$3/1M input tokens
    cost_gpt4o_per_strategy: Decimal = Decimal("0.01")
    cost_elevenlabs_per_1k_chars: Decimal = Decimal("0.30")
    cost_apify_per_1k: Decimal = Decimal("2.30")

    @field_validator("data_path", "temp_path", "music_path", "video_output_dir", mode="before")
    @classmethod
    def parse_path(cls, v):
        """Converte string para Path."""
        if isinstance(v, str):
            return Path(v)
        return v

    @field_validator("daily_budget_limit_usd", "monthly_budget_limit_usd", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        """Converte string para Decimal."""
        if isinstance(v, str):
            return Decimal(v)
        return v

    @property
    def is_development(self) -> bool:
        """Verifica se esta em ambiente de desenvolvimento."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Verifica se esta em ambiente de producao."""
        return self.app_env == "production"

    @property
    def veo_cost_per_scene(self) -> Decimal:
        """Retorna custo por cena baseado no modo."""
        return self.cost_veo_test if self.veo_mode == "test" else self.cost_veo_production

    @property
    def video_analysis_cost(self) -> Decimal:
        """Retorna custo por analise baseado no provider."""
        return self.cost_claude_per_video if self.video_analysis_provider == "claude" else self.cost_gemini_per_video

    def ensure_directories(self) -> None:
        """Garante que todos os diretorios necessarios existem."""
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        self.music_path.mkdir(parents=True, exist_ok=True)
        self.video_output_dir.mkdir(parents=True, exist_ok=True)

    def validate_api_keys(self) -> None:
        """Valida que as API keys necessarias estao configuradas."""
        missing = []

        if not self.apify_token:
            missing.append("APIFY_TOKEN")

        # Valida key do provider de analise escolhido
        if self.video_analysis_provider == "claude":
            if not self.anthropic_api_key:
                missing.append("ANTHROPIC_API_KEY")
        else:
            if not self.google_api_key:
                missing.append("GOOGLE_API_KEY")

        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.fal_key:
            missing.append("FAL_KEY")

        if self.is_production and missing:
            raise ValueError(f"API keys obrigatorias faltando: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    """Retorna instancia cacheada das configuracoes."""
    settings = Settings()
    settings.ensure_directories()
    return settings
