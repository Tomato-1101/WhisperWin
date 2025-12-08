"""Application constants and default configuration values."""

from typing import Any, Dict

from .types import ComputeType, HotkeyMode, ModelSize

# Application metadata
APP_NAME: str = "SuperWhisper"
APP_VERSION: str = "1.0.0"

# Audio settings
SAMPLE_RATE: int = 16000
AUDIO_CHANNELS: int = 1
AUDIO_DTYPE: str = "float32"

# UI settings
# UI settings
OVERLAY_BASE_WIDTH: int = 100
OVERLAY_BASE_HEIGHT: int = 32
OVERLAY_EXPANDED_WIDTH: int = 240
OVERLAY_EXPANDED_HEIGHT: int = 48
OVERLAY_TOP_MARGIN: int = 16
ANIMATION_DURATION_MS: int = 350

# Timing
CONFIG_CHECK_INTERVAL_SEC: int = 1
DEFAULT_MEMORY_RELEASE_DELAY_SEC: int = 300

# Default configuration (used when settings.yaml is missing or incomplete)
DEFAULT_CONFIG: Dict[str, Any] = {
    # Hotkey settings
    "hotkey": "<f2>",
    "hotkey_mode": HotkeyMode.TOGGLE.value,

    # Transcription backend
    "transcription_backend": "local",  # "local" or "groq"

    # Model settings (Local backend)
    "model_size": ModelSize.BASE.value,
    "compute_type": ComputeType.FLOAT16.value,
    "language": "ja",
    "model_cache_dir": "",

    # Groq API settings
    "groq_model": "whisper-large-v3-turbo",  # API key from GROQ_API_KEY env var

    # Transcription settings
    "release_memory_delay": DEFAULT_MEMORY_RELEASE_DELAY_SEC,
    "vad_filter": True,
    "vad_min_silence_duration_ms": 500,
    "condition_on_previous_text": False,
    "no_speech_threshold": 0.6,
    "log_prob_threshold": -1.0,
    "no_speech_prob_cutoff": 0.7,
    "beam_size": 5,
}

# Settings file name
SETTINGS_FILE_NAME: str = "settings.yaml"
