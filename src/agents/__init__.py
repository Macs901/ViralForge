"""Agents do ViralForge."""

from src.agents.analyst_agent import AnalystAgent, AnalystResult, get_analyst_agent
from src.agents.producer_agent import ProducerAgent, ProducerResult, producer_agent
from src.agents.scheduler_agent import ContentScheduler, get_scheduler
from src.agents.strategist_agent import StrategistAgent, StrategistResult, strategist_agent
from src.agents.trend_hunter_agent import TrendHunterAgent, TrendHunterResult, get_trend_hunter
from src.agents.style_cloner_agent import StyleClonerAgent, StyleClonerResult, get_style_cloner
from src.agents.performance_tracker_agent import PerformanceTrackerAgent, PerformanceTrackerResult, get_performance_tracker
from src.agents.competitor_intel_agent import CompetitorIntelAgent, CompetitorIntelResult, get_competitor_intel
from src.agents.watcher_agent import WatcherAgent, WatcherResult, watcher_agent

__all__ = [
    # Watcher
    "WatcherAgent",
    "WatcherResult",
    "watcher_agent",
    # Analyst
    "AnalystAgent",
    "AnalystResult",
    "get_analyst_agent",
    # Strategist
    "StrategistAgent",
    "StrategistResult",
    "strategist_agent",
    # Producer
    "ProducerAgent",
    "ProducerResult",
    "producer_agent",
    # Trend Hunter
    "TrendHunterAgent",
    "TrendHunterResult",
    "get_trend_hunter",
    # Scheduler
    "ContentScheduler",
    "get_scheduler",
    # Style Cloner
    "StyleClonerAgent",
    "StyleClonerResult",
    "get_style_cloner",
    # Performance Tracker
    "PerformanceTrackerAgent",
    "PerformanceTrackerResult",
    "get_performance_tracker",
    # Competitor Intel
    "CompetitorIntelAgent",
    "CompetitorIntelResult",
    "get_competitor_intel",
]
