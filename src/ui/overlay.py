"""Dynamic Island-style overlay window for status display."""

import math
import random
from typing import List, Union

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from ..config.constants import (
    ANIMATION_DURATION_MS,
    OVERLAY_BASE_HEIGHT,
    OVERLAY_BASE_WIDTH,
    OVERLAY_EXPANDED_HEIGHT,
    OVERLAY_EXPANDED_WIDTH,
    OVERLAY_TOP_MARGIN,
)
from ..config.types import AppState
from .styles import MacTheme


class WaveformWidget(QWidget):
    """Widget that displays a dynamic audio waveform animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(20)
        
        self._bars_count = 12
        self._amplitudes = [0.1] * self._bars_count
        self._target_amplitudes = [0.1] * self._bars_count
        self._phase = 0.0
        
        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_wave)
        self._timer.setInterval(16)  # ~60 FPS
        
        self._is_active = False

    def start_animation(self):
        """Start the waveform animation."""
        self._is_active = True
        self._timer.start()
        self.show()

    def stop_animation(self):
        """Stop the waveform animation."""
        self._is_active = False
        self._timer.stop()
        self.hide()

    def _update_wave(self):
        """Update wave physics."""
        self._phase += 0.2
        
        # Smoothly interpolate to target amplitudes
        for i in range(self._bars_count):
            # Generate new random target occasionally
            if random.random() < 0.1:
                self._target_amplitudes[i] = random.uniform(0.2, 1.0)
            
            # Interpolate
            diff = self._target_amplitudes[i] - self._amplitudes[i]
            self._amplitudes[i] += diff * 0.15

        self.update()

    def paintEvent(self, event):
        """Draw the waveform."""
        if not self._is_active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        bar_width = 3
        spacing = 4
        total_width = (bar_width + spacing) * self._bars_count
        start_x = (width - total_width) / 2
        
        # Draw bars
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i in range(self._bars_count):
            amp = self._amplitudes[i]
            
            # Apply a sine wave over the bars for a "breathing" look
            sine_mod = (math.sin(self._phase + i * 0.5) + 1) * 0.5
            current_height = height * amp * (0.5 + 0.5 * sine_mod)
            current_height = max(4, current_height)  # Min height
            
            x = start_x + i * (bar_width + spacing)
            y = (height - current_height) / 2
            
            # Gradient color (Blue to Cyan)
            color = QColor(MacTheme.Colors(False).ACCENT)
            painter.setBrush(QBrush(color))
            
            painter.drawRoundedRect(QRectF(x, y, bar_width, current_height), bar_width/2, bar_width/2)


class DynamicIslandOverlay(QMainWindow):
    """
    A frameless, naturally integrated overlay window.
    """
    
    def __init__(self) -> None:
        """Initialize the overlay window."""
        super().__init__()
        
        self._setup_window()
        self._setup_ui()
        self._setup_animations()
        
        self._state = AppState.IDLE
        self.set_state(AppState.IDLE)

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Shadow effect via drawing, so we keep widget size larger than visual rect if needed
        # For simple rounding, we draw normally.
        
        # Initial position
        screen = QApplication.primaryScreen().geometry()
        x_pos = (screen.width() - OVERLAY_BASE_WIDTH) // 2
        self.setGeometry(x_pos, OVERLAY_TOP_MARGIN, OVERLAY_BASE_WIDTH, OVERLAY_BASE_HEIGHT)

    def _setup_ui(self) -> None:
        """Set up UI components."""
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        layout = QVBoxLayout(self._central_widget)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Container for content
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status Label
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Style comes from styles.py logic, applied here for specific tweaks
        self._status_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px; font-family: 'Segoe UI';")
        
        # Waveform
        self._waveform = WaveformWidget()
        self._waveform.hide()
        
        self._content_layout.addWidget(self._status_label)
        self._content_layout.addWidget(self._waveform)
        
        layout.addWidget(self._content_container)

    def _setup_animations(self) -> None:
        """Set up property animations."""
        self._geometry_animation = QPropertyAnimation(self, b"geometry")
        self._geometry_animation.setEasingCurve(QEasingCurve.Type.InOutBack) # Smoother organic movement
        self._geometry_animation.setDuration(ANIMATION_DURATION_MS)

    def paintEvent(self, event) -> None:
        """Draw the pill shape."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        radius = rect.height() / 2
        
        # Draw background (black with transparency, typical for Dynamic Island)
        painter.setBrush(QBrush(QColor(0, 0, 0, 240)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

    def set_state(self, state: Union[str, AppState]) -> None:
        """Update the overlay state."""
        if isinstance(state, str):
            state = AppState(state)
        
        self._state = state
        
        if state == AppState.IDLE:
            self._set_idle_state()
        elif state == AppState.RECORDING:
            self._set_recording_state()
        elif state == AppState.TRANSCRIBING:
            self._set_transcribing_state()

    def show_temporary_message(self, message: str, duration_ms: int = 2000, is_error: bool = False) -> None:
        """Show a temporary message."""
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        
        self._status_label.setText(message)
        self._waveform.stop_animation()
        
        color = "#FF453A" if is_error else "white" # macOS Red
        self._status_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 13px;")
        self._status_label.show()
        
        QTimer.singleShot(duration_ms, lambda: self.set_state(AppState.IDLE))

    def _set_idle_state(self) -> None:
        """Configure idle state."""
        self._animate_resize(OVERLAY_BASE_WIDTH, OVERLAY_BASE_HEIGHT)
        self._status_label.hide()
        self._waveform.stop_animation()
        
        # Delay hiding to allow animation to start
        QTimer.singleShot(ANIMATION_DURATION_MS, self.hide)

    def _set_recording_state(self) -> None:
        """Configure recording state."""
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._status_label.setText("Listening...")
        self._status_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        self._status_label.show()
        self._waveform.start_animation()

    def _set_transcribing_state(self) -> None:
        """Configure transcribing state."""
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._status_label.setText("Processing...")
        self._status_label.show()
        self._waveform.stop_animation() # Or switch to a loading spinner

    def _animate_resize(self, target_width: int, target_height: int) -> None:
        """Animate window resize."""
        screen = QApplication.primaryScreen().geometry()
        target_x = (screen.width() - target_width) // 2
        
        current_rect = self.geometry()
        target_rect = QRect(target_x, OVERLAY_TOP_MARGIN, target_width, target_height)
        
        if current_rect == target_rect:
            return

        self._geometry_animation.setStartValue(current_rect)
        self._geometry_animation.setEndValue(target_rect)
        self._geometry_animation.start()
