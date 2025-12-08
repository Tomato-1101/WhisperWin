"""Type definitions for the application configuration."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class HotkeyMode(str, Enum):
    """Hotkey trigger mode."""
    TOGGLE = "toggle"  # Press once to start, press again to stop
    HOLD = "hold"      # Hold to record, release to stop


class ModelSize(str, Enum):
    """Available Whisper model sizes."""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"
    DISTIL_LARGE_V2 = "distil-large-v2"
    DISTIL_MEDIUM_EN = "distil-medium.en"


class ComputeType(str, Enum):
    """Computation precision types for model inference."""
    FLOAT16 = "float16"
    INT8_FLOAT16 = "int8_float16"
    INT8 = "int8"


class AppState(str, Enum):
    """Application state enumeration."""
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class TranscriptionBackend(str, Enum):
    """Transcription backend type."""
    LOCAL = "local"  # faster-whisper (GPU)
    GROQ = "groq"    # Groq Cloud API


@dataclass
class TranscriberConfig:
    """Configuration for the transcriber module."""
    model_size: str = ModelSize.BASE.value
    compute_type: str = ComputeType.FLOAT16.value
    language: str = "ja"
    release_memory_delay: int = 300
    vad_filter: bool = True
    vad_min_silence_duration_ms: int = 500
    condition_on_previous_text: bool = False
    no_speech_threshold: float = 0.6
    log_prob_threshold: float = -1.0
    no_speech_prob_cutoff: float = 0.7
    beam_size: int = 5
    model_cache_dir: str = ""


@dataclass
class HotkeyConfig:
    """Configuration for hotkey settings."""
    hotkey: str = "<f2>"
    hotkey_mode: str = HotkeyMode.TOGGLE.value


@dataclass
class AppConfig:
    """Complete application configuration."""
    # Hotkey settings
    hotkey: str = "<f2>"
    hotkey_mode: str = HotkeyMode.TOGGLE.value
    
    # Model settings
    model_size: str = ModelSize.BASE.value
    compute_type: str = ComputeType.FLOAT16.value
    language: str = "ja"
    model_cache_dir: str = ""
    
    # Transcription settings
    release_memory_delay: int = 300
    vad_filter: bool = True
    vad_min_silence_duration_ms: int = 500
    condition_on_previous_text: bool = False
    no_speech_threshold: float = 0.6
    log_prob_threshold: float = -1.0
    no_speech_prob_cutoff: float = 0.7
    beam_size: int = 5
