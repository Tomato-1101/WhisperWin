"""Settings window for application configuration."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import ConfigManager, HotkeyMode, ModelSize, ComputeType


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
        layout = QFormLayout()
        
        config = self._config_manager.config
        
        # Model Size
        self._model_combo = QComboBox()
        self._model_combo.addItems([m.value for m in ModelSize])
        self._model_combo.setCurrentText(config.get("model_size", ModelSize.BASE.value))
        layout.addRow("Model Size:", self._model_combo)
        
        # Compute Type
        self._compute_combo = QComboBox()
        self._compute_combo.addItems([c.value for c in ComputeType])
        self._compute_combo.setCurrentText(config.get("compute_type", ComputeType.FLOAT16.value))
        layout.addRow("Compute Type:", self._compute_combo)
        
        # Language
        self._lang_input = QLineEdit(config.get("language", "ja"))
        layout.addRow("Language:", self._lang_input)
        
        tab.setLayout(layout)
        self._tabs.addTab(tab, "Model")

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
            "model_size": self._model_combo.currentText(),
            "compute_type": self._compute_combo.currentText(),
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
