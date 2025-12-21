"""Tools para controle de orcamento e custos."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models.tracking import BudgetTracking, DailyCounter

settings = get_settings()


class BudgetExceededError(Exception):
    """Erro lancado quando o orcamento e excedido."""

    pass


class BudgetTools:
    """Gerenciador de orcamento e custos."""

    SERVICE_COSTS = {
        "apify": settings.cost_apify_per_1k / 1000,  # Por resultado
        "gemini": settings.cost_gemini_per_video,
        "openai": settings.cost_gpt4o_per_strategy,
        "veo_test": settings.cost_veo_test,
        "veo_production": settings.cost_veo_production,
        "elevenlabs": settings.cost_elevenlabs_per_1k_chars / 1000,  # Por caractere
    }

    def __init__(self):
        """Inicializa budget tools."""
        self.daily_limit = settings.daily_budget_limit_usd
        self.monthly_limit = settings.monthly_budget_limit_usd
        self.abort_on_exceed = settings.abort_on_budget_exceed
        self.warning_threshold = settings.budget_warning_threshold

    def get_today_budget(self, db: Optional[Session] = None) -> BudgetTracking:
        """Obtem ou cria registro de budget do dia.

        Args:
            db: Sessao do banco (opcional)

        Returns:
            BudgetTracking do dia atual
        """
        should_close = False
        if db is None:
            db = get_sync_db()
            should_close = True

        try:
            today = date.today()

            # Busca registro existente
            stmt = select(BudgetTracking).where(BudgetTracking.date == today)
            budget = db.execute(stmt).scalar_one_or_none()

            if budget is None:
                # Cria novo registro
                budget = BudgetTracking(
                    date=today,
                    daily_budget_limit_usd=self.daily_limit,
                    monthly_budget_limit_usd=self.monthly_limit,
                )
                db.add(budget)
                db.commit()
                db.refresh(budget)

            return budget
        finally:
            if should_close:
                db.close()

    def get_today_counter(self, db: Optional[Session] = None) -> DailyCounter:
        """Obtem ou cria contador do dia.

        Args:
            db: Sessao do banco (opcional)

        Returns:
            DailyCounter do dia atual
        """
        should_close = False
        if db is None:
            db = get_sync_db()
            should_close = True

        try:
            today = date.today()

            stmt = select(DailyCounter).where(DailyCounter.date == today)
            counter = db.execute(stmt).scalar_one_or_none()

            if counter is None:
                counter = DailyCounter(date=today)
                db.add(counter)
                db.commit()
                db.refresh(counter)

            return counter
        finally:
            if should_close:
                db.close()

    def check_budget(
        self,
        service: str,
        quantity: int = 1,
        mode: Optional[Literal["test", "production"]] = None,
    ) -> tuple[bool, Decimal, str]:
        """Verifica se ha orcamento para uma operacao.

        Args:
            service: Nome do servico (apify, gemini, openai, veo, elevenlabs)
            quantity: Quantidade de operacoes
            mode: Modo para Veo (test/production)

        Returns:
            Tuple (pode_executar, custo_estimado, mensagem)
        """
        db = get_sync_db()
        try:
            budget = self.get_today_budget(db)

            # Calcula custo estimado
            if service == "veo":
                service_key = f"veo_{mode or settings.veo_mode}"
            else:
                service_key = service

            unit_cost = self.SERVICE_COSTS.get(service_key, Decimal("0"))
            estimated_cost = unit_cost * quantity

            # Verifica limite diario
            projected_total = budget.total_cost_usd + estimated_cost

            if projected_total > budget.daily_budget_limit_usd:
                msg = (
                    f"Orcamento excedido! "
                    f"Limite: ${budget.daily_budget_limit_usd}, "
                    f"Atual: ${budget.total_cost_usd}, "
                    f"Operacao: ${estimated_cost}"
                )
                return False, estimated_cost, msg

            # Verifica warning threshold
            usage_ratio = float(projected_total / budget.daily_budget_limit_usd)
            if usage_ratio >= self.warning_threshold:
                msg = f"Aviso: Orcamento em {usage_ratio*100:.1f}% do limite"
            else:
                msg = "OK"

            return True, estimated_cost, msg
        finally:
            db.close()

    def register_cost(
        self,
        service: str,
        cost: Decimal,
        quantity: int = 1,
        db: Optional[Session] = None,
    ) -> BudgetTracking:
        """Registra custo de uma operacao.

        Args:
            service: Nome do servico
            cost: Custo em USD
            quantity: Quantidade de operacoes
            db: Sessao do banco (opcional)

        Returns:
            BudgetTracking atualizado

        Raises:
            BudgetExceededError: Se abort_on_exceed=True e limite excedido
        """
        should_close = False
        if db is None:
            db = get_sync_db()
            should_close = True

        try:
            budget = self.get_today_budget(db)

            # Adiciona custo ao servico correto
            budget.add_cost(service, cost)
            budget.api_calls_count += quantity

            # Verifica se excedeu
            if budget.budget_exceeded and self.abort_on_exceed:
                db.commit()
                raise BudgetExceededError(
                    f"Orcamento diario excedido! Total: ${budget.total_cost_usd}"
                )

            db.commit()
            db.refresh(budget)

            return budget
        finally:
            if should_close:
                db.close()

    def increment_counter(
        self,
        counter_name: str,
        amount: int = 1,
        db: Optional[Session] = None,
    ) -> DailyCounter:
        """Incrementa contador diario.

        Args:
            counter_name: Nome do contador (veo_generations, videos_analyzed, etc.)
            amount: Quantidade a incrementar
            db: Sessao do banco

        Returns:
            DailyCounter atualizado
        """
        should_close = False
        if db is None:
            db = get_sync_db()
            should_close = True

        try:
            counter = self.get_today_counter(db)
            counter.increment(counter_name, amount)
            db.commit()
            db.refresh(counter)
            return counter
        finally:
            if should_close:
                db.close()

    def get_daily_status(self) -> dict:
        """Retorna status completo do orcamento diario.

        Returns:
            Dict com status do budget e contadores
        """
        db = get_sync_db()
        try:
            budget = self.get_today_budget(db)
            counter = self.get_today_counter(db)

            return {
                "date": str(budget.date),
                "budget": {
                    "limit_usd": float(budget.daily_budget_limit_usd),
                    "spent_usd": float(budget.total_cost_usd),
                    "remaining_usd": float(budget.budget_remaining),
                    "usage_percent": budget.budget_usage_percent,
                    "exceeded": budget.budget_exceeded,
                },
                "costs_by_service": {
                    "apify": float(budget.apify_cost_usd),
                    "gemini": float(budget.gemini_cost_usd),
                    "openai": float(budget.openai_cost_usd),
                    "veo": float(budget.veo_cost_usd),
                    "elevenlabs": float(budget.elevenlabs_cost_usd),
                },
                "counters": {
                    "veo_generations": counter.veo_generations,
                    "scraping_runs": counter.scraping_runs,
                    "videos_collected": counter.videos_collected,
                    "videos_analyzed": counter.videos_analyzed,
                    "strategies_generated": counter.strategies_generated,
                    "videos_produced": counter.videos_produced,
                    "tts_characters": counter.tts_characters_used,
                },
                "api_calls": budget.api_calls_count,
            }
        finally:
            db.close()

    def estimate_production_cost(
        self,
        num_scenes: int,
        script_chars: int,
        tts_provider: str = "edge-tts",
        veo_mode: str = "test",
    ) -> dict:
        """Estima custo de producao de um video.

        Args:
            num_scenes: Numero de cenas Veo
            script_chars: Caracteres do roteiro
            tts_provider: Provider TTS
            veo_mode: Modo Veo

        Returns:
            Dict com custos detalhados
        """
        veo_cost = float(self.SERVICE_COSTS[f"veo_{veo_mode}"]) * num_scenes

        if tts_provider == "edge-tts":
            tts_cost = 0.0
        else:
            tts_cost = float(self.SERVICE_COSTS["elevenlabs"]) * script_chars

        total = veo_cost + tts_cost

        return {
            "veo_cost_usd": veo_cost,
            "tts_cost_usd": tts_cost,
            "total_usd": total,
            "num_scenes": num_scenes,
            "script_chars": script_chars,
            "tts_provider": tts_provider,
            "veo_mode": veo_mode,
        }

    def can_produce_video(
        self,
        num_scenes: int,
        script_chars: int,
        tts_provider: str = "edge-tts",
        veo_mode: str = "test",
    ) -> tuple[bool, str]:
        """Verifica se e possivel produzir um video com o orcamento atual.

        Args:
            num_scenes: Numero de cenas
            script_chars: Caracteres do roteiro
            tts_provider: Provider TTS
            veo_mode: Modo Veo

        Returns:
            Tuple (pode_produzir, mensagem)
        """
        estimate = self.estimate_production_cost(
            num_scenes, script_chars, tts_provider, veo_mode
        )

        db = get_sync_db()
        try:
            budget = self.get_today_budget(db)
            remaining = float(budget.budget_remaining)

            if estimate["total_usd"] > remaining:
                return False, (
                    f"Orcamento insuficiente. "
                    f"Necessario: ${estimate['total_usd']:.2f}, "
                    f"Disponivel: ${remaining:.2f}"
                )

            return True, f"OK - Custo estimado: ${estimate['total_usd']:.2f}"
        finally:
            db.close()


# Singleton para uso global
budget_tools = BudgetTools()
