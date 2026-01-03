"""Google Sheets integration for reporting/export."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models import GeneratedStrategy, ProducedVideo, ViralVideo
from src.tools.budget_tools import budget_tools

settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsExporter:
    """Exportador de dados principais do ViralForge para Google Sheets."""

    def __init__(self) -> None:
        self._client: gspread.Client | None = None
        self._spreadsheet: gspread.Spreadsheet | None = None
        self.spreadsheet_id = settings.google_sheets_spreadsheet_id
        self.tab_videos = settings.google_sheets_tab_videos
        self.tab_strategies = settings.google_sheets_tab_strategies
        self.tab_productions = settings.google_sheets_tab_productions
        self.tab_status = settings.google_sheets_tab_status

    # === Public API ===

    def export_all(
        self,
        videos_limit: int = 50,
        strategies_limit: int = 50,
        productions_limit: int = 50,
        include_status: bool = True,
    ) -> dict[str, Any]:
        """Exporta videos, estrategias, producoes e status para a planilha."""
        sheet = self._get_spreadsheet()

        summary = {}
        summary["videos"] = self.export_videos(sheet, limit=videos_limit)
        summary["strategies"] = self.export_strategies(sheet, limit=strategies_limit)
        summary["productions"] = self.export_productions(sheet, limit=productions_limit)
        if include_status:
            summary["status"] = self.export_status(sheet)

        return summary

    def export_videos(
        self, sheet: gspread.Spreadsheet | None = None, limit: int = 50
    ) -> dict[str, Any]:
        """Exporta videos recentes para a aba configurada."""
        sheet = sheet or self._get_spreadsheet()

        db = get_sync_db()
        try:
            stmt = (
                select(ViralVideo)
                .options(
                    joinedload(ViralVideo.profile),
                    joinedload(ViralVideo.analysis),
                )
                .order_by(ViralVideo.scraped_at.desc())
                .limit(limit)
            )
            videos = db.execute(stmt).scalars().all()
        finally:
            db.close()

        header = [
            "video_id",
            "profile",
            "platform_id",
            "url",
            "views",
            "likes",
            "comments",
            "shares",
            "saves",
            "statistical_score",
            "prefilter_pass",
            "virality_score",
            "replicability_score",
            "production_quality_score",
            "duration_seconds",
            "posted_at",
            "scraped_at",
            "analyzed_at",
            "caption",
        ]
        rows = [self._video_row(v) for v in videos]
        self._update_sheet(sheet, self.tab_videos, header, rows)

        return {"worksheet": self.tab_videos, "rows": len(rows)}

    def export_strategies(
        self, sheet: gspread.Spreadsheet | None = None, limit: int = 50
    ) -> dict[str, Any]:
        """Exporta estrategias recentes."""
        sheet = sheet or self._get_spreadsheet()

        db = get_sync_db()
        try:
            stmt = (
                select(GeneratedStrategy)
                .options(
                    joinedload(GeneratedStrategy.source_video),
                    joinedload(GeneratedStrategy.productions),
                )
                .order_by(GeneratedStrategy.created_at.desc())
                .limit(limit)
            )
            strategies = db.execute(stmt).scalars().all()
        finally:
            db.close()

        header = [
            "strategy_id",
            "source_video_id",
            "title",
            "niche",
            "status",
            "scene_count",
            "estimated_cost_usd",
            "tts_provider",
            "music_track",
            "best_posting_time",
            "created_at",
            "updated_at",
        ]
        rows = [self._strategy_row(s) for s in strategies]
        self._update_sheet(sheet, self.tab_strategies, header, rows)

        return {"worksheet": self.tab_strategies, "rows": len(rows)}

    def export_productions(
        self, sheet: gspread.Spreadsheet | None = None, limit: int = 50
    ) -> dict[str, Any]:
        """Exporta producoes recentes."""
        sheet = sheet or self._get_spreadsheet()

        db = get_sync_db()
        try:
            stmt = (
                select(ProducedVideo)
                .options(joinedload(ProducedVideo.strategy))
                .order_by(ProducedVideo.created_at.desc())
                .limit(limit)
            )
            productions = db.execute(stmt).scalars().all()
        finally:
            db.close()

        header = [
            "production_id",
            "strategy_id",
            "status",
            "final_video_path",
            "duration_seconds",
            "resolution",
            "veo_cost_usd",
            "tts_cost_usd",
            "total_cost_usd",
            "is_published",
            "published_platform",
            "published_url",
            "published_at",
            "post_views",
            "post_likes",
            "post_comments",
            "post_shares",
            "created_at",
            "updated_at",
        ]
        rows = [self._production_row(p) for p in productions]
        self._update_sheet(sheet, self.tab_productions, header, rows)

        return {"worksheet": self.tab_productions, "rows": len(rows)}

    def export_status(self, sheet: gspread.Spreadsheet | None = None) -> dict[str, Any]:
        """Exporta status diario de budget e contadores."""
        sheet = sheet or self._get_spreadsheet()

        status = budget_tools.get_daily_status()
        budget = status["budget"]
        counters = status["counters"]
        costs = status["costs_by_service"]

        header = [
            "exported_at",
            "date",
            "budget_limit_usd",
            "budget_spent_usd",
            "budget_remaining_usd",
            "budget_usage_pct",
            "budget_exceeded",
            "api_calls",
            "scraping_runs",
            "videos_collected",
            "videos_analyzed",
            "strategies_generated",
            "videos_produced",
            "veo_generations",
            "tts_characters",
            "apify_cost_usd",
            "gemini_cost_usd",
            "openai_cost_usd",
            "veo_cost_usd",
            "elevenlabs_cost_usd",
        ]

        rows = [
            [
                self._format_dt(datetime.now()),
                status["date"],
                budget["limit_usd"],
                budget["spent_usd"],
                budget["remaining_usd"],
                budget["usage_percent"],
                budget["exceeded"],
                status.get("api_calls"),
                counters["scraping_runs"],
                counters["videos_collected"],
                counters["videos_analyzed"],
                counters["strategies_generated"],
                counters["videos_produced"],
                counters["veo_generations"],
                counters["tts_characters"],
                costs["apify"],
                costs["gemini"],
                costs["openai"],
                costs["veo"],
                costs["elevenlabs"],
            ]
        ]

        self._update_sheet(sheet, self.tab_status, header, rows)
        return {"worksheet": self.tab_status, "rows": len(rows)}

    # === Helpers ===

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """Inicializa cliente e retorna planilha alvo."""
        if self._spreadsheet:
            return self._spreadsheet

        if not self.spreadsheet_id:
            raise RuntimeError("Configure GOOGLE_SHEETS_SPREADSHEET_ID no .env.")

        credentials = self._load_credentials()
        self._client = gspread.authorize(credentials)
        self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)
        return self._spreadsheet

    def _load_credentials(self) -> Credentials:
        """Carrega credenciais da service account."""
        if settings.google_service_account_json:
            info = json.loads(settings.google_service_account_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)

        if settings.google_service_account_file:
            path = Path(settings.google_service_account_file)
            if not path.exists():
                raise FileNotFoundError(f"Arquivo de credenciais nao encontrado: {path}")
            return Credentials.from_service_account_file(path, scopes=SCOPES)

        raise RuntimeError(
            "Configure GOOGLE_SERVICE_ACCOUNT_JSON ou GOOGLE_SERVICE_ACCOUNT_FILE para exportar ao Sheets."
        )

    def _update_sheet(
        self,
        sheet: gspread.Spreadsheet,
        name: str,
        header: Sequence[str],
        rows: list[Sequence[Any]],
    ) -> None:
        """Limpa e sobrescreve uma worksheet."""
        ws = self._get_or_create_worksheet(sheet, name, cols=len(header))
        ws.clear()
        values = [list(header)] + [list(self._normalize_row(r)) for r in rows]
        ws.update(values, value_input_option="USER_ENTERED")

    def _get_or_create_worksheet(
        self, sheet: gspread.Spreadsheet, name: str, rows: int = 100, cols: int = 20
    ) -> gspread.Worksheet:
        """Busca worksheet existente ou cria se nao existir."""
        try:
            return sheet.worksheet(name)
        except WorksheetNotFound:
            return sheet.add_worksheet(title=name, rows=rows, cols=cols)

    def _normalize_row(self, row: Sequence[Any]) -> list[Any]:
        """Converte valores para formatos suportados pelo Sheets."""
        return [self._normalize_value(v) for v in row]

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return self._format_dt(value)
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        if value is None:
            return ""
        return value

    def _format_dt(self, value: datetime | None) -> str:
        return value.isoformat() if value else ""

    def _truncate(self, text: str | None, limit: int = 300) -> str:
        if not text:
            return ""
        return text if len(text) <= limit else f"{text[:limit]}..."

    def _video_row(self, video: ViralVideo) -> list[Any]:
        analysis = video.analysis
        return [
            video.id,
            video.profile.username if video.profile else "",
            video.platform_id,
            video.source_url,
            video.views_count,
            video.likes_count,
            video.comments_count,
            video.shares_count,
            video.saves_count,
            self._normalize_value(video.statistical_viral_score),
            video.passes_prefilter,
            self._normalize_value(analysis.virality_score) if analysis else "",
            self._normalize_value(analysis.replicability_score) if analysis else "",
            self._normalize_value(analysis.production_quality_score) if analysis else "",
            video.duration_seconds or "",
            self._format_dt(video.posted_at),
            self._format_dt(video.scraped_at),
            self._format_dt(analysis.analyzed_at) if analysis else "",
            self._truncate(video.caption),
        ]

    def _strategy_row(self, strategy: GeneratedStrategy) -> list[Any]:
        tts_provider = ""
        if strategy.tts_config:
            tts_provider = strategy.tts_config.get("provider", "")
        return [
            strategy.id,
            strategy.source_video_id or "",
            strategy.title,
            strategy.target_niche or "",
            strategy.status,
            strategy.scene_count,
            self._normalize_value(strategy.estimated_production_cost_usd),
            tts_provider,
            strategy.music_track or "",
            strategy.best_posting_time or "",
            self._format_dt(strategy.created_at),
            self._format_dt(strategy.updated_at),
        ]

    def _production_row(self, production: ProducedVideo) -> list[Any]:
        return [
            production.id,
            production.strategy_id or "",
            production.status,
            production.final_video_path or "",
            production.final_duration_seconds or "",
            production.final_resolution or "",
            self._normalize_value(production.veo_cost_usd),
            self._normalize_value(production.tts_cost_usd),
            self._normalize_value(production.total_production_cost_usd),
            production.is_published,
            production.published_platform or "",
            production.published_url or "",
            self._format_dt(production.published_at),
            production.post_views,
            production.post_likes,
            production.post_comments,
            production.post_shares,
            self._format_dt(production.created_at),
            self._format_dt(production.updated_at),
        ]


# Singleton para uso global
sheets_exporter = GoogleSheetsExporter()
