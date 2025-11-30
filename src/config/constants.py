"""Application constants and default configuration values."""

from typing import Dict, Any
from .types import HotkeyMode, ModelSize, ComputeType

# Application metadata
APP_NAME = "SuperWhisper"
APP_VERSION = "1.0.0"

# Audio settings
SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_DTYPE = "float32"

# UI settings
OVERLAY_BASE_WIDTH = 120
OVERLAY_BASE_HEIGHT = 35
OVERLAY_EXPANDED_WIDTH = 300
OVERLAY_EXPANDED_HEIGHT = 60
OVERLAY_TOP_MARGIN = 10
ANIMATION_DURATION_MS = 400

# Timing
CONFIG_CHECK_INTERVAL_SEC = 1
DEFAULT_MEMORY_RELEASE_DELAY_SEC = 300

# Default configuration (used when settings.yaml is missing or incomplete)
DEFAULT_CONFIG: Dict[str, Any] = {
    # Hotkey settings
    "hotkey": "<f2>",
    "hotkey_mode": HotkeyMode.TOGGLE.value,
    
    # Model settings
    "model_size": ModelSize.BASE.value,
    "compute_type": ComputeType.FLOAT16.value,
    "language": "ja",
    "model_cache_dir": "",
    
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
SETTINGS_FILE_NAME = "settings.yaml"
