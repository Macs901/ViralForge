"""Configuration module for ViralForge."""

from config.settings import get_settings

# Export settings singleton for backward compatibility
settings = get_settings()

__all__ = ["settings", "get_settings"]
