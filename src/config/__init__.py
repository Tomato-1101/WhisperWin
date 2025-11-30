"""Configuration module for the application."""

from .types import HotkeyMode, ModelSize, ComputeType, AppConfig
from .constants import DEFAULT_CONFIG, SAMPLE_RATE, APP_NAME
from .config_manager import ConfigManager

__all__ = [
    "HotkeyMode",
    "ModelSize", 
    "ComputeType",
    "AppConfig",
    "DEFAULT_CONFIG",
    "SAMPLE_RATE",
    "APP_NAME",
    "ConfigManager",
]
