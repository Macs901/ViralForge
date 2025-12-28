"""Models do ViralForge."""

from src.db.models.analysis import PromptVersion, VideoAnalysis
from src.db.models.instagram import (
    ContentType,
    InstagramAudio,
    InstagramCarousel,
    InstagramComment,
    InstagramHashtag,
    InstagramProfile,
    InstagramStory,
)
from src.db.models.production import ProducedVideo, ProductionStatus
from src.db.models.profile import MonitoredProfile
from src.db.models.strategy import GeneratedStrategy, StrategyStatus
from src.db.models.tracking import (
    BudgetTracking,
    DailyCounter,
    ExecutionLog,
    RunMetrics,
    RunStatus,
    SystemConfig,
)
from src.db.models.trends import (
    Competitor,
    CompetitorAnalysis,
    ContentQueue,
    ContentStatus,
    PerformanceMetric,
    Platform,
    Trend,
    TrendStatus,
    TrendType,
)
from src.db.models.video import ViralVideo

__all__ = [
    # Profile
    "MonitoredProfile",
    # Video
    "ViralVideo",
    # Instagram
    "ContentType",
    "InstagramProfile",
    "InstagramStory",
    "InstagramCarousel",
    "InstagramComment",
    "InstagramHashtag",
    "InstagramAudio",
    # Trends & Scheduling
    "Platform",
    "TrendType",
    "TrendStatus",
    "Trend",
    "ContentStatus",
    "ContentQueue",
    "PerformanceMetric",
    "Competitor",
    "CompetitorAnalysis",
    # Analysis
    "VideoAnalysis",
    "PromptVersion",
    # Strategy
    "GeneratedStrategy",
    "StrategyStatus",
    # Production
    "ProducedVideo",
    "ProductionStatus",
    # Tracking
    "BudgetTracking",
    "RunMetrics",
    "RunStatus",
    "ExecutionLog",
    "DailyCounter",
    "SystemConfig",
]
