"""Settings window for application configuration."""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import ComputeType, ConfigManager, HotkeyMode, ModelSize, TranscriptionBackend


class SettingsWindow(QWidget):
    """
    Settings window for configuring the application.
    
    Provides tabs for general, model, and advanced settings.
    """
    
    def __init__(self) -> None:
        """Initialize the settings window."""
        super().__init__()
        
        self._config_manager = ConfigManager()
        
        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("Settings - SuperWhisper")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Tabs
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        self._setup_general_tab()
        self._setup_model_tab()
        self._setup_advanced_tab()
        
        # Buttons
        self._setup_buttons(layout)

    def _setup_general_tab(self) -> None:
        """Set up the General settings tab."""
        tab = QWidget()
        layout = QFormLayout()
        
        config = self._config_manager.config
        
        # Hotkey
        self._hotkey_input = QLineEdit(config.get("hotkey", "<f2>"))
        self._hotkey_input.setPlaceholderText("e.g. <f2>, <ctrl>+<space>")
        layout.addRow("Hotkey:", self._hotkey_input)
        
        # Hotkey Mode
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([m.value for m in HotkeyMode])
        self._mode_combo.setCurrentText(config.get("hotkey_mode", HotkeyMode.TOGGLE.value))
        layout.addRow("Trigger Mode:", self._mode_combo)
        
        tab.setLayout(layout)
        self._tabs.addTab(tab, "General")

    def _setup_model_tab(self) -> None:
        """Set up the Model settings tab."""
        tab = QWidget()
        layout = QVBoxLayout()

        config = self._config_manager.config

        # Backend selection
        backend_layout = QFormLayout()
        self._backend_combo = QComboBox()
        self._backend_combo.addItems([TranscriptionBackend.LOCAL.value, TranscriptionBackend.GROQ.value])
        self._backend_combo.setCurrentText(config.get("transcription_backend", "local"))
        self._backend_combo.currentTextChanged.connect(self._on_backend_changed)
        backend_layout.addRow("Backend:", self._backend_combo)
        layout.addLayout(backend_layout)

        # Local (GPU) settings group
        self._local_group = QGroupBox("Local (GPU) Settings")
        local_layout = QFormLayout()

        # Model Size
        self._model_combo = QComboBox()
        self._model_combo.addItems([m.value for m in ModelSize])
        self._model_combo.setCurrentText(config.get("model_size", ModelSize.BASE.value))
        local_layout.addRow("Model Size:", self._model_combo)

        # Compute Type
        self._compute_combo = QComboBox()
        self._compute_combo.addItems([c.value for c in ComputeType])
        self._compute_combo.setCurrentText(config.get("compute_type", ComputeType.FLOAT16.value))
        local_layout.addRow("Compute Type:", self._compute_combo)

        self._local_group.setLayout(local_layout)
        layout.addWidget(self._local_group)

        # Groq API settings group
        self._groq_group = QGroupBox("Groq API Settings")
        groq_layout = QFormLayout()

        # API Key status
        api_key_status = "✓ Set" if os.environ.get("GROQ_API_KEY") else "✗ Not set"
        self._api_key_status_label = QLabel(f"API Key: {api_key_status}")
        groq_layout.addRow("", self._api_key_status_label)

        # Note about environment variable
        env_note = QLabel("Set GROQ_API_KEY environment variable")
        env_note.setStyleSheet("color: gray; font-size: 10px;")
        groq_layout.addRow("", env_note)

        # Groq Model
        self._groq_model_combo = QComboBox()
        self._groq_model_combo.addItems([
            "whisper-large-v3-turbo",
            "whisper-large-v3",
            "distil-whisper-large-v3-en"
        ])
        self._groq_model_combo.setCurrentText(config.get("groq_model", "whisper-large-v3-turbo"))
        groq_layout.addRow("Model:", self._groq_model_combo)

        self._groq_group.setLayout(groq_layout)
        layout.addWidget(self._groq_group)

        # Language (common to both backends)
        common_layout = QFormLayout()
        self._lang_input = QLineEdit(config.get("language", "ja"))
        common_layout.addRow("Language:", self._lang_input)
        layout.addLayout(common_layout)

        # Spacer
        layout.addStretch()

        tab.setLayout(layout)
        self._tabs.addTab(tab, "Model")

        # Initialize UI state
        self._on_backend_changed(self._backend_combo.currentText())

    def _on_backend_changed(self, backend: str) -> None:
        """Handle backend selection change."""
        is_local = (backend == TranscriptionBackend.LOCAL.value)
        self._local_group.setEnabled(is_local)
        self._groq_group.setEnabled(not is_local)

    def _setup_advanced_tab(self) -> None:
        """Set up the Advanced settings tab."""
        tab = QWidget()
        layout = QFormLayout()
        
        config = self._config_manager.config
        
        # VAD Filter
        self._vad_check = QCheckBox("Enable VAD Filter")
        self._vad_check.setChecked(config.get("vad_filter", True))
        layout.addRow("Voice Activity Detection:", self._vad_check)
        
        # Release Memory Delay
        self._memory_spin = QSpinBox()
        self._memory_spin.setRange(0, 3600)
        self._memory_spin.setValue(config.get("release_memory_delay", 300))
        self._memory_spin.setSuffix(" sec")
        layout.addRow("Release VRAM after:", self._memory_spin)
        
        tab.setLayout(layout)
        self._tabs.addTab(tab, "Advanced")

    def _setup_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Set up the Save and Cancel buttons."""
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        parent_layout.addLayout(button_layout)

    def _save_settings(self) -> None:
        """Save the current settings."""
        new_config = {
            "hotkey": self._hotkey_input.text(),
            "hotkey_mode": self._mode_combo.currentText(),
            "transcription_backend": self._backend_combo.currentText(),
            "model_size": self._model_combo.currentText(),
            "compute_type": self._compute_combo.currentText(),
            "groq_model": self._groq_model_combo.currentText(),
            "language": self._lang_input.text(),
            "vad_filter": self._vad_check.isChecked(),
            "release_memory_delay": self._memory_spin.value(),
        }

        if self._config_manager.save(new_config):
            QMessageBox.information(
                self,
                "Success",
                "Settings saved successfully.\nSome changes may require a restart."
            )
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
