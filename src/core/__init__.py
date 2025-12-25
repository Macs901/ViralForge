"""Core modules for ViralForge."""

from src.core.database import (
    AsyncSessionLocal,
    SyncSessionLocal,
    async_engine,
    get_db,
    get_sync_db,
    init_db,
    sync_engine,
)

# Backward compatibility aliases
engine = sync_engine
async_session = AsyncSessionLocal

__all__ = [
    "get_db",
    "get_sync_db",
    "init_db",
    "sync_engine",
    "async_engine",
    "SyncSessionLocal",
    "AsyncSessionLocal",
    "engine",
    "async_session",
]
