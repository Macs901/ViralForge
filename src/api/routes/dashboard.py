"""Rotas de Dashboard do ViralForge."""

from fastapi import APIRouter

from src.tools import budget_tools

router = APIRouter()


@router.get("/status")
async def get_status():
    """Retorna status geral do sistema."""
    return budget_tools.get_daily_status()


@router.get("/budget")
async def get_budget():
    """Retorna status detalhado do orcamento."""
    status = budget_tools.get_daily_status()
    return status["budget"]


@router.get("/counters")
async def get_counters():
    """Retorna contadores do dia."""
    status = budget_tools.get_daily_status()
    return status["counters"]


@router.get("/costs")
async def get_costs():
    """Retorna custos por servico."""
    status = budget_tools.get_daily_status()
    return status["costs_by_service"]
