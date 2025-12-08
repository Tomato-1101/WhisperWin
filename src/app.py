"""Main application controller."""

import threading
import time
from typing import Any, Optional, Set

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication
from pynput import keyboard

from .config import ConfigManager, HotkeyMode, TranscriptionBackend
from .config.constants import CONFIG_CHECK_INTERVAL_SEC
from .core import AudioRecorder, GroqTranscriber, InputHandler, Transcriber
from .ui import DynamicIslandOverlay, SettingsWindow, SystemTray
from .utils.logger import get_logger

logger = get_logger(__name__)


class SuperWhisperApp(QObject):
    """
    Main application controller.
    
    Integrates all components: audio recording, transcription,
    UI overlay, settings, and hotkey handling.
    """
    
    # Signals for thread-safe UI updates
    status_changed = Signal(str)
    text_ready = Signal(str)
    
    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        logger.info("Initializing SuperWhisper...")
        
        self._setup_config()
        self._setup_core_components()
        self._setup_ui_components()
        self._setup_signals()
        self._setup_state()
        self._start_background_threads()
        
        logger.info("App Ready.")
        self.status_changed.emit("idle")

    def _setup_config(self) -> None:
        """Initialize configuration manager."""
        self._config = ConfigManager()

    def _setup_core_components(self) -> None:
        """Initialize core business logic components."""
        self._recorder = AudioRecorder()

        # Initialize transcriber based on backend selection
        backend_type = self._config.get("transcription_backend", "local")
        self._transcriber = self._create_transcriber(backend_type)

        self._input_handler = InputHandler()

    def _create_transcriber(self, backend_type: str):
        """
        Create appropriate transcriber based on backend type.

        Args:
            backend_type: "local" or "groq"

        Returns:
            Transcriber instance (either Transcriber or GroqTranscriber).
        """
        if backend_type == TranscriptionBackend.GROQ.value:
            transcriber = GroqTranscriber(
                model=self._config.get("groq_model", "whisper-large-v3-turbo"),
                language=self._config.get("language", "ja"),
                vad_filter=self._config.get("vad_filter", True),
                vad_min_silence_duration_ms=self._config.get("vad_min_silence_duration_ms", 500),
            )

            if not transcriber.is_available():
                logger.warning(
                    "Groq API not available (SDK not installed or GROQ_API_KEY not set). "
                    "Falling back to local GPU transcription."
                )
                self._show_backend_warning("groq_unavailable")
                return self._create_local_transcriber()

            logger.info(f"Using Groq API backend with model: {transcriber.model}")
            return transcriber
        else:
            return self._create_local_transcriber()

    def _create_local_transcriber(self) -> Transcriber:
        """Create local GPU transcriber."""
        logger.info("Using local GPU backend (faster-whisper)")
        return Transcriber(
            model_size=self._config.get("model_size"),
            compute_type=self._config.get("compute_type", "float16"),
            language=self._config.get("language"),
            release_memory_delay=self._config.get("release_memory_delay", 300),
            vad_filter=self._config.get("vad_filter", True),
            vad_min_silence_duration_ms=self._config.get("vad_min_silence_duration_ms", 500),
            condition_on_previous_text=self._config.get("condition_on_previous_text", False),
            no_speech_threshold=self._config.get("no_speech_threshold", 0.6),
            log_prob_threshold=self._config.get("log_prob_threshold", -1.0),
            no_speech_prob_cutoff=self._config.get("no_speech_prob_cutoff", 0.7),
            beam_size=self._config.get("beam_size", 5),
            model_cache_dir=self._config.get("model_cache_dir", ""),
        )

    def _show_backend_warning(self, warning_type: str) -> None:
        """
        Show warning message to user about backend issues.

        Args:
            warning_type: Type of warning ("groq_unavailable", etc.)
        """
        if warning_type == "groq_unavailable":
            self._overlay.show_temporary_message(
                "Groq API unavailable\nUsing local GPU",
                duration_ms=3000,
                is_error=False
            )

    def _setup_ui_components(self) -> None:
        """Initialize UI components."""
        self._overlay = DynamicIslandOverlay()
        self._settings_window = SettingsWindow()
        self._tray = SystemTray()

    def _setup_signals(self) -> None:
        """Connect signals to slots."""
        self._tray.open_settings.connect(self._open_settings)
        self._tray.quit_app.connect(self._quit_app)
        self.status_changed.connect(self._update_ui_status)
        self.text_ready.connect(self._handle_transcription_result)

    def _setup_state(self) -> None:
        """Initialize application state."""
        self._is_recording = False
        self._is_transcribing = False
        self._cancel_transcription = False
        
        # Hotkey configuration
        self._hotkey = self._config.get("hotkey", "<f2>")
        self._hotkey_mode = self._config.get("hotkey_mode", HotkeyMode.TOGGLE.value)
        self._pressed_keys: Set[str] = set()
        self._required_keys: Set[str] = self._parse_hotkey(self._hotkey)
        
        # Thread control
        self._monitoring = True

    def _start_background_threads(self) -> None:
        """Start background threads for hotkey and config monitoring."""
        # Hotkey listener
        self._listener_thread = threading.Thread(
            target=self._start_keyboard_listener,
            daemon=True
        )
        self._listener_thread.start()
        
        # Config monitor
        self._monitor_thread = threading.Thread(
            target=self._monitor_config,
            daemon=True
        )
        self._monitor_thread.start()

    # -------------------------------------------------------------------------
    # UI Actions
    # -------------------------------------------------------------------------

    def _open_settings(self) -> None:
        """Open the settings window."""
        self._settings_window.show()
        self._settings_window.activateWindow()

    def _quit_app(self) -> None:
        """Quit the application."""
        logger.info("Quitting...")
        self._monitoring = False
        QApplication.quit()

    def _update_ui_status(self, status: str) -> None:
        """Update UI components with new status."""
        self._overlay.set_state(status)
        self._tray.set_status(status)

    def _handle_transcription_result(self, text: str) -> None:
        """Handle transcription result."""
        if not text:
            logger.info("No text detected.")
            self._overlay.show_temporary_message("No Speech")
            return

        if text.startswith("Error:"):
            logger.error(f"Transcription failed: {text}")
            self._overlay.show_temporary_message("Error", is_error=True)
            return

        logger.info(f"Result: {text}")
        self._input_handler.insert_text(text)
        
        # Return to idle after a short delay
        QTimer.singleShot(1000, lambda: self.status_changed.emit("idle"))

    # -------------------------------------------------------------------------
    # Recording and Transcription
    # -------------------------------------------------------------------------

    def start_recording(self) -> None:
        """Start audio recording."""
        if self._is_recording:
            return
        
        # Cancel any ongoing transcription
        if self._is_transcribing:
            logger.info("New recording started - cancelling current transcription")
            self._cancel_transcription = True
        
        logger.info("Start Recording")
        self._is_recording = True
        self.status_changed.emit("recording")
        
        # Preload model in background
        threading.Thread(target=self._transcriber.load_model, daemon=True).start()
        self._recorder.start()

    def stop_and_transcribe(self) -> None:
        """Stop recording and start transcription."""
        if not self._is_recording:
            return
        
        logger.info("Stop Recording")
        self._is_recording = False
        self._is_transcribing = True
        self._cancel_transcription = False
        self.status_changed.emit("transcribing")
        
        audio_data = self._recorder.stop()
        
        # Run transcription in background
        threading.Thread(
            target=self._transcribe_worker,
            args=(audio_data,),
            daemon=True
        ).start()

    def _transcribe_worker(self, audio_data) -> None:
        """Worker thread for transcription."""
        try:
            if len(audio_data) == 0:
                self.text_ready.emit("")
                return

            # Check if cancelled before starting
            if self._cancel_transcription:
                logger.info("Transcription cancelled before processing")
                return

            text = self._transcriber.transcribe(audio_data)
            
            # Check if cancelled after processing
            if self._cancel_transcription:
                logger.info("Transcription cancelled - discarding result")
                return
            
            self.text_ready.emit(text)
        finally:
            self._is_transcribing = False

    # -------------------------------------------------------------------------
    # Hotkey Handling
    # -------------------------------------------------------------------------

    def _parse_hotkey(self, hotkey_str: str) -> Set[str]:
        """Parse hotkey string into a set of key names."""
        keys = hotkey_str.replace('<', '').replace('>', '').split('+')
        return set(keys)

    def _start_keyboard_listener(self) -> None:
        """Start the keyboard listener based on hotkey mode."""
        if self._hotkey_mode == HotkeyMode.HOLD.value:
            with keyboard.Listener(
                on_press=self._handle_key_press,
                on_release=self._handle_key_release
            ) as listener:
                listener.join()
        else:
            hotkey_map = {self._hotkey: self._on_activate_toggle}
            with keyboard.GlobalHotKeys(hotkey_map) as h:
                h.join()

    def _on_activate_toggle(self) -> None:
        """Handle toggle mode activation."""
        if not self._is_recording:
            self.start_recording()
        else:
            self.stop_and_transcribe()

    def _handle_key_press(self, key: Any) -> None:
        """Handle key press events."""
        try:
            key_str = self._normalize_key(key)
            if key_str:
                self._pressed_keys.add(key_str)
                if self._required_keys.issubset(self._pressed_keys) and not self._is_recording:
                    self.start_recording()
        except Exception:
            pass

    def _handle_key_release(self, key: Any) -> None:
        """Handle key release events."""
        try:
            key_str = self._normalize_key(key)
            if key_str and key_str in self._pressed_keys:
                self._pressed_keys.remove(key_str)
                if self._is_recording and key_str in self._required_keys:
                    self.stop_and_transcribe()
        except Exception:
            pass

    def _normalize_key(self, key: Any) -> Optional[str]:
        """Normalize key to a standard string representation."""
        try:
            if hasattr(key, 'name'):
                name = key.name.lower()
                if name in ('ctrl_l', 'ctrl_r'):
                    return 'ctrl'
                if name in ('alt_l', 'alt_r'):
                    return 'alt'
                if name in ('shift_l', 'shift_r'):
                    return 'shift'
                return name
            elif hasattr(key, 'char') and key.char:
                return key.char.lower()
        except Exception:
            pass
        return None

    # -------------------------------------------------------------------------
    # Configuration Monitoring
    # -------------------------------------------------------------------------

    def _monitor_config(self) -> None:
        """Monitor configuration file for changes."""
        while self._monitoring:
            time.sleep(CONFIG_CHECK_INTERVAL_SEC)
            
            if self._config.reload_if_changed():
                self._apply_config_changes()
                logger.info("Config reloaded and applied.")

    def _apply_config_changes(self) -> None:
        """Apply configuration changes."""
        # Update hotkey settings
        new_hotkey = self._config.get("hotkey", "<f2>")
        new_mode = self._config.get("hotkey_mode", HotkeyMode.TOGGLE.value)
        
        if new_hotkey != self._hotkey or new_mode != self._hotkey_mode:
            self._hotkey = new_hotkey
            self._hotkey_mode = new_mode
            self._required_keys = self._parse_hotkey(self._hotkey)
            logger.info(f"Hotkey updated: {self._hotkey}")
        
        # Update transcriber settings
        self._update_transcriber_settings()

    def _update_transcriber_settings(self) -> None:
        """Update transcriber settings from config."""
        new_backend = self._config.get("transcription_backend", "local")
        current_backend = "groq" if isinstance(self._transcriber, GroqTranscriber) else "local"

        # Backend changed - recreate transcriber
        if new_backend != current_backend:
            logger.info(f"Switching transcription backend: {current_backend} -> {new_backend}")

            # Unload old transcriber
            if hasattr(self._transcriber, 'unload_model'):
                self._transcriber.unload_model()

            # Create new transcriber
            self._transcriber = self._create_transcriber(new_backend)
            return

        # Same backend - update settings
        if current_backend == "local":
            self._update_local_transcriber_settings()
        else:
            self._update_groq_transcriber_settings()

    def _update_local_transcriber_settings(self) -> None:
        """Update local transcriber settings."""
        if not isinstance(self._transcriber, Transcriber):
            return

        new_model_size = self._config.get("model_size")
        model_changed = new_model_size != self._transcriber.model_size

        # Update settings
        self._transcriber.model_size = new_model_size
        self._transcriber.compute_type = self._config.get("compute_type", "float16")
        self._transcriber.language = self._config.get("language")
        self._transcriber.release_memory_delay = self._config.get("release_memory_delay", 300)
        self._transcriber.vad_filter = self._config.get("vad_filter", True)
        self._transcriber.vad_min_silence_duration_ms = self._config.get("vad_min_silence_duration_ms", 500)
        self._transcriber.condition_on_previous_text = self._config.get("condition_on_previous_text", False)
        self._transcriber.no_speech_threshold = self._config.get("no_speech_threshold", 0.6)
        self._transcriber.log_prob_threshold = self._config.get("log_prob_threshold", -1.0)
        self._transcriber.no_speech_prob_cutoff = self._config.get("no_speech_prob_cutoff", 0.7)
        self._transcriber.beam_size = self._config.get("beam_size", 5)

        new_cache_dir = self._config.get("model_cache_dir", "")
        self._transcriber.model_cache_dir = new_cache_dir or None

        # Unload model if settings changed
        if model_changed:
            if self._transcriber.model is not None:
                logger.info("Model settings changed, unloading model for reload...")
                self._transcriber.unload_model()

    def _update_groq_transcriber_settings(self) -> None:
        """Update Groq transcriber settings."""
        if not isinstance(self._transcriber, GroqTranscriber):
            return

        # Update Groq settings
        self._transcriber.model = self._config.get("groq_model", "whisper-large-v3-turbo")
        self._transcriber.language = self._config.get("language", "ja")
        
        # Update VAD settings
        vad_filter_enabled = self._config.get("vad_filter", True)
        vad_min_silence = self._config.get("vad_min_silence_duration_ms", 500)
        
        # Check if VAD settings changed
        if vad_filter_enabled != self._transcriber.vad_enabled:
            self._transcriber.vad_enabled = vad_filter_enabled
            if vad_filter_enabled and self._transcriber._vad_filter is None:
                from .core.vad import VadFilter
                self._transcriber._vad_filter = VadFilter(
                    min_silence_duration_ms=vad_min_silence,
                    use_cuda=True
                )
            elif not vad_filter_enabled:
                self._transcriber._vad_filter = None
        
        logger.debug(f"Updated Groq settings: model={self._transcriber.model}, vad={vad_filter_enabled}")
