"""Models para tracking de budget, metricas e logs."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RunStatus(str, Enum):
    """Status possiveis de uma execucao."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class BudgetTracking(Base):
    """Controle de orcamento diario."""

    __tablename__ = "budget_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)

    # Limites configurados
    daily_budget_limit_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("20.00")
    )
    monthly_budget_limit_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("500.00")
    )

    # Gastos por servico
    apify_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    gemini_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    openai_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    veo_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    elevenlabs_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    # Totais
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    # Status
    budget_exceeded: Mapped[bool] = mapped_column(Boolean, default=False)
    budget_exceeded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Contadores
    api_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    videos_produced: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<BudgetTracking(date={self.date}, total=${self.total_cost_usd}, exceeded={self.budget_exceeded})>"

    @property
    def budget_remaining(self) -> Decimal:
        """Retorna orcamento restante do dia."""
        return self.daily_budget_limit_usd - self.total_cost_usd

    @property
    def budget_usage_percent(self) -> float:
        """Retorna percentual de uso do orcamento."""
        if self.daily_budget_limit_usd == 0:
            return 100.0
        return float(self.total_cost_usd / self.daily_budget_limit_usd * 100)

    def add_cost(self, service: str, amount: Decimal) -> None:
        """Adiciona custo a um servico especifico."""
        service_map = {
            "apify": "apify_cost_usd",
            "gemini": "gemini_cost_usd",
            "openai": "openai_cost_usd",
            "veo": "veo_cost_usd",
            "elevenlabs": "elevenlabs_cost_usd",
        }
        if service in service_map:
            attr = service_map[service]
            current = getattr(self, attr) or Decimal("0")
            setattr(self, attr, current + amount)
            self.total_cost_usd = (self.total_cost_usd or Decimal("0")) + amount
            self.api_calls_count += 1

            # Verifica se excedeu o limite
            if self.total_cost_usd > self.daily_budget_limit_usd and not self.budget_exceeded:
                self.budget_exceeded = True
                self.budget_exceeded_at = datetime.now()


class RunMetrics(Base):
    """Metricas de execucao de tasks."""

    __tablename__ = "run_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), default=lambda: str(uuid4()), index=True)

    # Identificacao
    task_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(50))

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))

    # Recursos processados
    items_input: Mapped[int] = mapped_column(Integer, default=0)
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Custos desta run
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    actual_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # Status
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.RUNNING.value, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Detalhes extras
    details: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<RunMetrics(task='{self.task_name}', status='{self.status}', processed={self.items_processed})>"

    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """Marca a execucao como completa."""
        self.completed_at = datetime.now()
        self.duration_seconds = Decimal(
            str((self.completed_at - self.started_at).total_seconds())
        )
        self.status = RunStatus.COMPLETED.value if success else RunStatus.FAILED.value
        if error:
            self.error_message = error


class ExecutionLog(Base):
    """Logs detalhados de execucao."""

    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(100))
    agent_name: Mapped[Optional[str]] = mapped_column(String(50))
    run_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))

    # Referencias
    related_video_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("viral_videos.id", ondelete="SET NULL")
    )
    related_strategy_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("generated_strategies.id", ondelete="SET NULL")
    )
    related_production_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("produced_videos.id", ondelete="SET NULL")
    )

    # Dados
    status: Mapped[Optional[str]] = mapped_column(String(20))
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    output_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text)

    # Metricas
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))

    executed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<ExecutionLog(task='{self.task_name}', status='{self.status}')>"


class DailyCounter(Base):
    """Contadores diarios de operacoes."""

    __tablename__ = "daily_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True, default=date.today, index=True)

    # Contadores de operacoes
    veo_generations: Mapped[int] = mapped_column(Integer, default=0)
    scraping_runs: Mapped[int] = mapped_column(Integer, default=0)
    videos_collected: Mapped[int] = mapped_column(Integer, default=0)
    videos_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    strategies_generated: Mapped[int] = mapped_column(Integer, default=0)
    videos_produced: Mapped[int] = mapped_column(Integer, default=0)

    # Contadores de TTS
    tts_characters_used: Mapped[int] = mapped_column(Integer, default=0)
    tts_edge_calls: Mapped[int] = mapped_column(Integer, default=0)
    tts_elevenlabs_calls: Mapped[int] = mapped_column(Integer, default=0)

    # Custos
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    # Budget status
    budget_warning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    budget_exceeded: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<DailyCounter(date={self.date}, videos_produced={self.videos_produced})>"

    def increment(self, counter: str, amount: int = 1) -> None:
        """Incrementa um contador especifico."""
        if hasattr(self, counter):
            current = getattr(self, counter) or 0
            setattr(self, counter, current + amount)


class SystemConfig(Base):
    """Configuracoes do sistema armazenadas no banco."""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SystemConfig(key='{self.key}')>"
