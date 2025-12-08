# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhisperWin (SuperWhisper) is a Windows desktop application for real-time speech-to-text transcription using faster-whisper. It runs as a system tray application with a Dynamic Island-style overlay UI, activated by global hotkeys.

## Development Commands

### Running the Application

```bash
# Development mode
python run.py

# Build executable (creates dist/SuperWhisperLike/SuperWhisperLike.exe)
pyinstaller SuperWhisperLike.spec --clean --noconfirm
```

### Setup

```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Install PyTorch with CUDA 12.1 (required for GPU acceleration)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## System Requirements

- **CUDA-capable NVIDIA GPU required** - The application uses GPU acceleration exclusively via faster-whisper
- Python 3.8+
- ffmpeg must be installed and available in PATH

## Architecture

### Core Application Flow

1. **Hotkey Detection** (`src/app.py`): Keyboard listener runs in background thread, monitoring for configured hotkey (hold or toggle mode)
2. **Audio Recording** (`src/core/audio_recorder.py`): Captures audio using sounddevice when hotkey triggered
3. **Transcription** (`src/core/transcriber.py`): Processes audio with faster-whisper/WhisperModel on CUDA
4. **Text Input** (`src/core/input_handler.py`): Injects transcribed text into active window using pynput
5. **UI Updates**: PyQt6 signals/slots coordinate updates to overlay and system tray

### Key Components

**SuperWhisperApp** (`src/app.py`):
- Central controller integrating all components
- Manages two background daemon threads:
  - Keyboard listener for hotkey detection
  - Config monitor for hot-reload support
- Thread-safe communication via PyQt6 signals (status_changed, text_ready)
- Handles recording cancellation when new recording starts during transcription

**Transcriber** (`src/core/transcriber.py`):
- Lazy-loads WhisperModel on first transcription or preloads during recording
- Auto-unloads model after configurable delay (release_memory_delay) to free VRAM
- Thread-safe model management with locks and timer cancellation
- Filters transcription segments by no_speech_prob to prevent hallucinations
- **CRITICAL**: Always checks torch.cuda.is_available() and raises RuntimeError if CUDA unavailable

**ConfigManager** (`src/config/config_manager.py`):
- Loads settings.yaml from project root (or executable directory when frozen)
- Monitors file mtime and triggers hot-reload without restart
- Merges user config with DEFAULT_CONFIG from constants.py

**DynamicIslandOverlay** (`src/ui/overlay.py`):
- Frameless, always-on-top window at screen top-center
- Three states: idle (hidden), recording (red pulse animation), transcribing
- Custom paintEvent for pill-shaped background with pulse effect
- Animates size changes with QPropertyAnimation

### Configuration System

**settings.yaml** controls all runtime behavior:
- Hotkey configuration (e.g., `<ctrl>+<space>`, `<f2>`)
- Hotkey mode: `hold` (press-and-hold) or `toggle` (press-to-start/stop)
- Model settings: size (tiny to large-v3), compute_type (float16/int8), language
- VRAM management: release_memory_delay (seconds)
- Hallucination mitigation: VAD filter, no_speech_threshold, no_speech_prob_cutoff
- Advanced: beam_size, log_prob_threshold, condition_on_previous_text

Changes are detected automatically by config monitor thread and applied without restart.

### Threading Model

- **Main Thread**: PyQt6 event loop for UI
- **Keyboard Listener Thread**: pynput keyboard listener (daemon)
- **Config Monitor Thread**: Polls settings.yaml mtime every CONFIG_CHECK_INTERVAL_SEC (daemon)
- **Transcription Workers**: Short-lived daemon threads spawned per transcription request
- **Model Preload**: Background thread started during recording to reduce latency

### PyInstaller Packaging

**SuperWhisperLike.spec**:
- One-Dir mode (not One-File) for faster startup
- Bundles settings.yaml into dist
- Collects faster_whisper and ctranslate2 dependencies with collect_all
- Hidden imports for all src modules
- Console=False for windowed app

## Hallucination Prevention

The app implements multiple strategies to prevent Whisper from generating phantom text:

1. **VAD Filter**: Voice Activity Detection removes silent segments before transcription
2. **no_speech_threshold**: Model's internal threshold during inference (default 0.6)
3. **no_speech_prob_cutoff**: Post-processing filter that discards segments with high no_speech_prob (default 0.7)
4. **condition_on_previous_text=false**: Prevents model from continuing previous patterns

Users experiencing hallucinations like "ご視聴ありがとうございました" should:
- Increase no_speech_threshold (0.7-0.8)
- Decrease no_speech_prob_cutoff (0.5-0.6)
- Enable vad_filter if disabled

## Common Issues

### WinError 1314 (Symbolic Link Privilege)
Set `model_cache_dir` in settings.yaml to avoid HuggingFace Hub trying to create symlinks. Example: `D:/whisper_cache`

### Text Not Inserting
- App needs admin privileges to inject text into admin-elevated windows
- Check for hotkey conflicts with other applications

### VRAM Management
- Model unloads after release_memory_delay seconds of inactivity
- Reduce model_size or use int8 compute_type for lower VRAM usage
- Model preloads during recording to minimize transcription delay

## Code Style Notes

- Type hints used throughout (from typing import)
- Enums defined in src/config/types.py (HotkeyMode, ModelSize, ComputeType, AppState)
- Constants in src/config/constants.py (UI dimensions, intervals, default config)
- Logger via src/utils/logger.py (get_logger(__name__))
- PyQt6 signals for thread-safe UI updates (never manipulate UI from worker threads directly)
