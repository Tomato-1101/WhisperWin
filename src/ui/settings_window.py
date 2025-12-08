"""Settings window for application configuration."""

import os
import math
from typing import Optional

from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRectF, QPointF
from PySide6.QtGui import QIcon, QAction, QKeyEvent, QKeySequence, QPainter, QPainterPath, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QToolButton
)

from ..config import ComputeType, ConfigManager, HotkeyMode, ModelSize, TranscriptionBackend
from .styles import MacTheme


class ThemeToggleButton(QPushButton):
    """
    Animated Theme Toggle Button (Sun/Moon).
    """
    def __init__(self, parent=None, is_dark: bool = False):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_dark = is_dark
        self._angle = 0  # For rotation animation
        
        # Setup animation
        self._anim = QPropertyAnimation(self, b"angle")
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        self.clicked.connect(self._animate_toggle)
        
        # Remove default styling to draw custom
        self.setStyleSheet("border: none; background: transparent;")

    def _animate_toggle(self):
        self._is_dark = not self._is_dark
        
        # Rotate 180 degrees
        start = self._angle
        end = start + 180
        
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()
        
        self.update()

    def get_angle(self):
        return self._angle

    def set_angle(self, value):
        self._angle = value
        self.update()

    angle = property(get_angle, set_angle)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Determine color based on theme (inverse of background usually, or constant accent)
        # Using a fixed color like dark gray/white depending on state
        color = QColor("#FFD60A") if not self._is_dark else QColor("#F2F2F7") # Sun yellow / Moon white
        
        width = self.width()
        height = self.height()
        center = QPointF(width / 2, height / 2)
        
        painter.translate(center)
        painter.rotate(self._angle)
        
        if not self._is_dark:
            # Draw Sun
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), 6, 6)
            
            # Rays
            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(8):
                painter.rotate(45)
                painter.drawLine(0, 9, 0, 11)
                
        else:
            # Draw Moon
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Draw circles to form crescent
            path = QPainterPath()
            path.addEllipse(QPointF(0, 0), 8, 8)
            
            cutout = QPainterPath()
            cutout.addEllipse(QPointF(4, -2), 7, 7)
            
            final_path = path.subtracted(cutout)
            painter.drawPath(final_path)


class HotkeyInput(QLineEdit):
    """
    Custom widget to record hotkeys by pressing them.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click to record shortcut...")
        # Style handles mostly everything, but we ensure focus rect is nice
        pass

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        # Ignore standalone modifier presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        parts = []

        # Mods
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("<ctrl>")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("<shift>")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("<alt>")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("<cmd>")

        # Key
        key_text = self._get_key_text(key)
        if key_text:
            parts.append(key_text)
            
        self.setText("+".join(parts))
        event.accept()

    def _get_key_text(self, key: int) -> str:
        # Special keys mapping to pynput format
        mapping = {
            Qt.Key.Key_F1: "<f1>", Qt.Key.Key_F2: "<f2>", Qt.Key.Key_F3: "<f3>",
            Qt.Key.Key_F4: "<f4>", Qt.Key.Key_F5: "<f5>", Qt.Key.Key_F6: "<f6>",
            Qt.Key.Key_F7: "<f7>", Qt.Key.Key_F8: "<f8>", Qt.Key.Key_F9: "<f9>",
            Qt.Key.Key_F10: "<f10>", Qt.Key.Key_F11: "<f11>", Qt.Key.Key_F12: "<f12>",
            Qt.Key.Key_Space: "<space>",
            Qt.Key.Key_Tab: "<tab>",
            Qt.Key.Key_Return: "<enter>",
            Qt.Key.Key_Enter: "<enter>",
            Qt.Key.Key_Backspace: "<backspace>",
            Qt.Key.Key_Delete: "<delete>",
            Qt.Key.Key_Escape: "<esc>",
            Qt.Key.Key_Home: "<home>",
            Qt.Key.Key_End: "<end>",
            Qt.Key.Key_PageUp: "<page_up>",
            Qt.Key.Key_PageDown: "<page_down>",
            Qt.Key.Key_Up: "<up>",
            Qt.Key.Key_Down: "<down>",
            Qt.Key.Key_Left: "<left>",
            Qt.Key.Key_Right: "<right>",
            Qt.Key.Key_Insert: "<insert>",
        }
        
        if key in mapping:
            return mapping[key]
        
        text = QKeySequence(key).toString().lower()
        if not text:
            return ""
        if len(text) == 1:
            return text
        else:
            return f"<{text}>"


class SettingsWindow(QWidget):
    """
    Settings window for configuring the application.
    Refactored to match macOS System Settings style with Theme Toggle.
    """

    def __init__(self) -> None:
        """Initialize the settings window."""
        super().__init__()

        self._config_manager = ConfigManager()
        
        # Load theme preference (default to False/Light)
        config = self._config_manager.config
        self._is_dark_mode = config.get("dark_mode", False)

        self._setup_window()
        self._setup_ui()
        self._load_current_settings()
        
        # Apply initial theme
        self._apply_theme(self._is_dark_mode)

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("Settings")
        self.resize(720, 480)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(200)
        self._sidebar.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self._sidebar.setFrameShape(QFrame.Shape.NoFrame)
        self._sidebar.currentRowChanged.connect(self._change_page)
        main_layout.addWidget(self._sidebar)

        # --- Content Area ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(20)

        # Header (Title + Theme Toggle)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        self._page_title = QLabel("General")
        self._page_title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 5px;")
        
        # Theme Toggle
        self._theme_toggle = ThemeToggleButton(is_dark=self._is_dark_mode)
        self._theme_toggle.clicked.connect(self._toggle_theme)
        
        header_layout.addWidget(self._page_title)
        header_layout.addStretch()
        header_layout.addWidget(self._theme_toggle)
        
        content_layout.addLayout(header_layout)

        # Stacked Widget for pages
        self._pages_stack = QStackedWidget()
        content_layout.addWidget(self._pages_stack)
        
        # Buttons area (Save/Cancel) - Bottom of content
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.close)
        
        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setProperty("class", "primary") # For styling
        self._save_btn.clicked.connect(self._save_settings)
        
        button_layout.addWidget(self._cancel_btn)
        button_layout.addWidget(self._save_btn)
        
        content_layout.addLayout(button_layout)
        
        main_layout.addWidget(content_container)

        # Add pages
        self._setup_pages()

    def _setup_pages(self) -> None:
        """Create and add pages to the stack."""
        self._add_page("General", self._create_general_page())
        self._add_page("Model", self._create_model_page())
        self._add_page("Advanced", self._create_advanced_page())
        self._add_page("LLM", self._create_llm_page())

        # Select first item
        self._sidebar.setCurrentRow(0)

    def _add_page(self, name: str, widget: QWidget) -> None:
        """Add a page to the sidebar and stack."""
        item = QListWidgetItem(name)
        self._sidebar.addItem(item)
        self._pages_stack.addWidget(widget)

    def _change_page(self, index: int) -> None:
        """Handle page switching."""
        self._pages_stack.setCurrentIndex(index)
        item = self._sidebar.item(index)
        if item:
            self._page_title.setText(item.text())

    def _create_general_page(self) -> QWidget:
        """Create General settings page."""
        page = QWidget()
        layout = QFormLayout(page)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Hotkey - using custom recorder widget
        self._hotkey_input = HotkeyInput()
        layout.addRow("Global Hotkey:", self._hotkey_input)

        # Hotkey Mode
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([m.value for m in HotkeyMode])
        layout.addRow("Trigger Mode:", self._mode_combo)
        
        # Language
        self._lang_input = QLineEdit()
        self._lang_input.setPlaceholderText("e.g. ja, en")
        layout.addRow("Language:", self._lang_input)

        return page

    def _create_model_page(self) -> QWidget:
        """Create Model settings page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # Backend selection
        backend_layout = QFormLayout()
        self._backend_combo = QComboBox()
        self._backend_combo.addItems([TranscriptionBackend.LOCAL.value, TranscriptionBackend.GROQ.value])
        self._backend_combo.currentTextChanged.connect(self._on_backend_changed)
        backend_layout.addRow("Transcription Engine:", self._backend_combo)
        layout.addLayout(backend_layout)
        
        # Local Settings Group
        self._local_group = QGroupBox("Local Engine Settings (GPU)")
        local_layout = QFormLayout()
        
        self._model_combo = QComboBox()
        self._model_combo.addItems([m.value for m in ModelSize])
        local_layout.addRow("Model Size:", self._model_combo)

        self._compute_combo = QComboBox()
        self._compute_combo.addItems([c.value for c in ComputeType])
        local_layout.addRow("Compute Type:", self._compute_combo)
        
        self._local_group.setLayout(local_layout)
        layout.addWidget(self._local_group)

        # Groq Settings Group
        self._groq_group = QGroupBox("Groq API Settings (Cloud)")
        groq_layout = QFormLayout()
        
        self._api_key_status_label = QLabel()
        groq_layout.addRow("API Key Status:", self._api_key_status_label)
        
        self._groq_model_combo = QComboBox()
        self._groq_model_combo.addItems([
            "whisper-large-v3-turbo",
            "whisper-large-v3",
            "distil-whisper-large-v3-en"
        ])
        groq_layout.addRow("Cloud Model:", self._groq_model_combo)
        
        self._groq_group.setLayout(groq_layout)
        layout.addWidget(self._groq_group)
        
        layout.addStretch()
        return page

    def _create_advanced_page(self) -> QWidget:
        """Create Advanced settings page."""
        page = QWidget()
        layout = QFormLayout(page)
        layout.setSpacing(15)

        # VAD
        self._vad_check = QCheckBox("Enable Voice Activity Detection")
        layout.addRow("", self._vad_check)

        # Memory Release
        self._memory_spin = QSpinBox()
        self._memory_spin.setRange(0, 3600)
        self._memory_spin.setSuffix(" sec")
        layout.addRow("Release Memory Delay:", self._memory_spin)

        return page

    def _create_llm_page(self) -> QWidget:
        """Create LLM post-processing settings page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        # ===== LLM Settings Group =====
        llm_settings_group = QGroupBox("LLM Post-Processing Settings")
        llm_layout = QFormLayout()
        llm_layout.setSpacing(15)
        llm_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Enable checkbox
        self._llm_enabled_check = QCheckBox("Enable LLM Post-Processing")
        self._llm_enabled_check.stateChanged.connect(self._on_llm_enabled_changed)
        llm_layout.addRow("", self._llm_enabled_check)

        # Provider selection
        self._llm_provider_combo = QComboBox()
        self._llm_provider_combo.addItems(["groq", "cerebras"])
        self._llm_provider_combo.currentTextChanged.connect(self._on_llm_provider_changed)
        llm_layout.addRow("Provider:", self._llm_provider_combo)

        # Model selection (dynamic based on provider)
        self._llm_model_combo = QComboBox()
        llm_layout.addRow("Model:", self._llm_model_combo)

        # Timeout
        self._llm_timeout_spin = QDoubleSpinBox()
        self._llm_timeout_spin.setRange(1.0, 30.0)
        self._llm_timeout_spin.setSingleStep(0.5)
        self._llm_timeout_spin.setSuffix(" sec")
        self._llm_timeout_spin.setDecimals(1)
        llm_layout.addRow("Timeout:", self._llm_timeout_spin)

        # Fallback on error
        self._llm_fallback_check = QCheckBox("Use original text if LLM fails")
        llm_layout.addRow("", self._llm_fallback_check)

        llm_settings_group.setLayout(llm_layout)
        layout.addWidget(llm_settings_group)

        # ===== API Keys Status Group =====
        api_keys_group = QGroupBox("API Keys Status")
        api_keys_layout = QFormLayout()
        api_keys_layout.setSpacing(10)
        api_keys_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._groq_llm_key_status = QLabel()
        api_keys_layout.addRow("Groq API Key:", self._groq_llm_key_status)

        self._cerebras_key_status = QLabel()
        api_keys_layout.addRow("Cerebras API Key:", self._cerebras_key_status)

        api_keys_group.setLayout(api_keys_layout)
        layout.addWidget(api_keys_group)

        # ===== System Prompt Group =====
        prompt_group = QGroupBox("System Prompt")
        prompt_layout = QVBoxLayout()

        prompt_label = QLabel("Define how the LLM should transform transcription results:")
        prompt_label.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 5px;")
        prompt_layout.addWidget(prompt_label)

        self._llm_prompt_edit = QTextEdit()
        self._llm_prompt_edit.setPlaceholderText(
            "Example:\n"
            "音声認識結果を以下のルールで変換してください:\n"
            "1. 数式: 「いち たす にー」→「1 + 2」\n"
            "2. カタカナ英語: 「アップル」→「Apple」\n"
            "変換後のテキストのみ返してください。"
        )
        self._llm_prompt_edit.setMinimumHeight(150)
        prompt_layout.addWidget(self._llm_prompt_edit)

        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        layout.addStretch()
        return page

    def _load_current_settings(self) -> None:
        """Load values from config into UI."""
        config = self._config_manager.config
        
        # General
        self._hotkey_input.setText(config.get("hotkey", "<f2>"))
        self._mode_combo.setCurrentText(config.get("hotkey_mode", HotkeyMode.TOGGLE.value))
        self._lang_input.setText(config.get("language", "ja"))
        
        # Model
        self._backend_combo.setCurrentText(config.get("transcription_backend", "local"))
        self._model_combo.setCurrentText(config.get("model_size", ModelSize.BASE.value))
        self._compute_combo.setCurrentText(config.get("compute_type", ComputeType.FLOAT16.value))
        self._groq_model_combo.setCurrentText(config.get("groq_model", "whisper-large-v3-turbo"))
        
        # API Key Status
        has_key = bool(os.environ.get("GROQ_API_KEY"))
        status_text = "✓ Ready" if has_key else "✗ Not Set (Check Environment)"
        status_color = "green" if has_key else "red"
        # Since we use global stylesheet, we use inline for specific color status or just classes
        # But inline works fine for simple label colors
        self._api_key_status_label.setText(status_text)
        self._api_key_status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        
        # Advanced
        self._vad_check.setChecked(config.get("vad_filter", True))
        self._memory_spin.setValue(config.get("release_memory_delay", 300))

        # LLM Settings
        llm_config = config.get("llm_postprocess", {})
        self._llm_enabled_check.setChecked(llm_config.get("enabled", False))
        self._llm_provider_combo.setCurrentText(llm_config.get("provider", "groq"))
        self._llm_timeout_spin.setValue(llm_config.get("timeout", 5.0))
        self._llm_fallback_check.setChecked(llm_config.get("fallback_on_error", True))
        self._llm_prompt_edit.setPlainText(llm_config.get("system_prompt", ""))

        # Update model list and select current model
        self._on_llm_provider_changed(self._llm_provider_combo.currentText())
        self._llm_model_combo.setCurrentText(llm_config.get("model", "llama-3.3-70b-versatile"))

        # Initialize enabled state
        self._on_llm_enabled_changed(self._llm_enabled_check.checkState().value)

        # Update API key status
        self._update_api_key_status()

        # Initialize visibility state
        self._on_backend_changed(self._backend_combo.currentText())

    def _on_backend_changed(self, backend: str) -> None:
        """Handle backend selection state."""
        is_local = (backend == TranscriptionBackend.LOCAL.value)
        self._local_group.setVisible(is_local)
        self._groq_group.setVisible(not is_local)

    def _on_llm_enabled_changed(self, state: int) -> None:
        """Handle LLM enabled state change."""
        enabled = (state == Qt.CheckState.Checked.value)

        # Enable/disable all LLM-related widgets
        self._llm_provider_combo.setEnabled(enabled)
        self._llm_model_combo.setEnabled(enabled)
        self._llm_timeout_spin.setEnabled(enabled)
        self._llm_fallback_check.setEnabled(enabled)
        self._llm_prompt_edit.setEnabled(enabled)

    def _on_llm_provider_changed(self, provider: str) -> None:
        """Update model list based on selected provider."""
        self._llm_model_combo.clear()

        if provider == "groq":
            models = [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768"
            ]
        elif provider == "cerebras":
            models = [
                "llama3.1-8b",
                "llama3.1-70b"
            ]
        else:
            models = []

        self._llm_model_combo.addItems(models)

    def _update_api_key_status(self) -> None:
        """Update API key status labels."""
        # Groq
        has_groq = bool(os.environ.get("GROQ_API_KEY"))
        groq_text = "✓ Ready" if has_groq else "✗ Not Set"
        groq_color = "green" if has_groq else "red"
        self._groq_llm_key_status.setText(groq_text)
        self._groq_llm_key_status.setStyleSheet(f"color: {groq_color}; font-weight: bold;")

        # Cerebras
        has_cerebras = bool(os.environ.get("CEREBRAS_API_KEY"))
        cerebras_text = "✓ Ready" if has_cerebras else "✗ Not Set"
        cerebras_color = "green" if has_cerebras else "red"
        self._cerebras_key_status.setText(cerebras_text)
        self._cerebras_key_status.setStyleSheet(f"color: {cerebras_color}; font-weight: bold;")

    def _toggle_theme(self) -> None:
        """Switch between dark and light mode."""
        self._is_dark_mode = not self._is_dark_mode
        self._apply_theme(self._is_dark_mode)

    def _apply_theme(self, is_dark: bool) -> None:
        """Apply the global stylesheet based on theme mode."""
        stylesheet = MacTheme.get_stylesheet(is_dark)
        self.setStyleSheet(stylesheet)
        
        # In a real app we might need to update specific non-Qt-styled elements if any,
        # but here the stylesheet covers almost everything.
        
        # We might want to save this state immediately or just on save
        # Saving immediately is better UX for theme

    def _save_settings(self) -> None:
        """Save settings to config file."""
        new_config = {
            "hotkey": self._hotkey_input.text(),
            "hotkey_mode": self._mode_combo.currentText(),
            "language": self._lang_input.text(),
            "transcription_backend": self._backend_combo.currentText(),
            "model_size": self._model_combo.currentText(),
            "compute_type": self._compute_combo.currentText(),
            "groq_model": self._groq_model_combo.currentText(),
            "vad_filter": self._vad_check.isChecked(),
            "release_memory_delay": self._memory_spin.value(),
            "dark_mode": self._is_dark_mode,  # Save theme preference

            # LLM Post-Processing
            "llm_postprocess": {
                "enabled": self._llm_enabled_check.isChecked(),
                "provider": self._llm_provider_combo.currentText(),
                "model": self._llm_model_combo.currentText(),
                "timeout": self._llm_timeout_spin.value(),
                "fallback_on_error": self._llm_fallback_check.isChecked(),
                "system_prompt": self._llm_prompt_edit.toPlainText(),
            },
        }

        if self._config_manager.save(new_config):
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
