"""Configuration module for the application."""

from .config_manager import ConfigManager
from .constants import APP_NAME, DEFAULT_CONFIG, SAMPLE_RATE
from .types import AppConfig, ComputeType, HotkeyMode, ModelSize, TranscriptionBackend

__all__ = [
    "HotkeyMode",
    "ModelSize",
    "ComputeType",
    "AppConfig",
    "TranscriptionBackend",
    "DEFAULT_CONFIG",
    "SAMPLE_RATE",
    "APP_NAME",
    "ConfigManager",
]
