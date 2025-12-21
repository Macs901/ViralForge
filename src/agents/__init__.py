"""Agents do ViralForge."""

from src.agents.analyst_agent import AnalystAgent, AnalystResult, analyst_agent
from src.agents.producer_agent import ProducerAgent, ProducerResult, producer_agent
from src.agents.strategist_agent import StrategistAgent, StrategistResult, strategist_agent
from src.agents.watcher_agent import WatcherAgent, WatcherResult, watcher_agent

__all__ = [
    # Watcher
    "WatcherAgent",
    "WatcherResult",
    "watcher_agent",
    # Analyst
    "AnalystAgent",
    "AnalystResult",
    "analyst_agent",
    # Strategist
    "StrategistAgent",
    "StrategistResult",
    "strategist_agent",
    # Producer
    "ProducerAgent",
    "ProducerResult",
    "producer_agent",
]
