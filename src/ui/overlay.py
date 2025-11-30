"""Dynamic Island-style overlay window for status display."""

from typing import Union

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from ..config.constants import (
    ANIMATION_DURATION_MS,
    OVERLAY_BASE_HEIGHT,
    OVERLAY_BASE_WIDTH,
    OVERLAY_EXPANDED_HEIGHT,
    OVERLAY_EXPANDED_WIDTH,
    OVERLAY_TOP_MARGIN,
)
from ..config.types import AppState


class DynamicIslandOverlay(QMainWindow):
    """
    A frameless, always-on-top window that mimics Apple's Dynamic Island.
    
    Displays recording and transcription status with smooth animations.
    """
    
    # UI Constants
    BACKGROUND_COLOR = QColor(0, 0, 0, 220)
    PULSE_COLOR = QColor(255, 50, 50)
    PULSE_INTERVAL_MS = 50
    
    def __init__(self) -> None:
        """Initialize the overlay window."""
        super().__init__()
        
        self._setup_window()
        self._setup_ui()
        self._setup_animations()
        self._setup_pulse_timer()
        
        self._state = AppState.IDLE
        self._pulse_factor = 0.0
        self._pulse_direction = 1
        
        self.set_state(AppState.IDLE)

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Hide from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Position at top center of screen
        screen = QApplication.primaryScreen().geometry()
        x_pos = (screen.width() - OVERLAY_BASE_WIDTH) // 2
        self.setGeometry(x_pos, OVERLAY_TOP_MARGIN, OVERLAY_BASE_WIDTH, OVERLAY_BASE_HEIGHT)

    def _setup_ui(self) -> None:
        """Set up UI components."""
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        layout = QVBoxLayout(self._central_widget)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            "color: white; font-weight: bold; font-family: 'Segoe UI', sans-serif;"
        )
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

    def _setup_animations(self) -> None:
        """Set up property animations."""
        self._geometry_animation = QPropertyAnimation(self, b"geometry")
        self._geometry_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self._geometry_animation.setDuration(ANIMATION_DURATION_MS)

    def _setup_pulse_timer(self) -> None:
        """Set up the pulse animation timer."""
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self.update)

    def paintEvent(self, event) -> None:
        """Custom paint event for pill-shaped background with pulse effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        radius = rect.height() / 2
        
        if self._state == AppState.RECORDING:
            self._draw_recording_state(painter, rect, radius)
        else:
            self._draw_normal_state(painter, rect, radius)

    def _draw_recording_state(self, painter: QPainter, rect: QRect, radius: float) -> None:
        """Draw the recording state with pulse effect."""
        # Update pulse animation
        self._pulse_factor += 0.1 * self._pulse_direction
        if self._pulse_factor >= 1.0:
            self._pulse_direction = -1
        if self._pulse_factor <= 0.0:
            self._pulse_direction = 1
        
        # Draw glow
        glow_alpha = int(100 * self._pulse_factor)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 50, 50, glow_alpha), 4))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), radius, radius)
        
        # Draw background
        painter.setBrush(QBrush(self.BACKGROUND_COLOR))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), radius - 2, radius - 2)

    def _draw_normal_state(self, painter: QPainter, rect: QRect, radius: float) -> None:
        """Draw the normal state."""
        painter.setBrush(QBrush(self.BACKGROUND_COLOR))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

    def set_state(self, state: Union[str, AppState]) -> None:
        """
        Update the overlay state.
        
        Args:
            state: New state (idle, recording, or transcribing).
        """
        # Convert string to AppState if needed
        if isinstance(state, str):
            state = AppState(state)
        
        self._state = state
        
        if state == AppState.IDLE:
            self._set_idle_state()
        elif state == AppState.RECORDING:
            self._set_recording_state()
        elif state == AppState.TRANSCRIBING:
            self._set_transcribing_state()

    def _set_idle_state(self) -> None:
        """Configure idle state."""
        self._animate_resize(OVERLAY_BASE_WIDTH, OVERLAY_BASE_HEIGHT)
        self._status_label.setText("Ready")
        self._status_label.hide()
        self._pulse_timer.stop()
        self.hide()

    def _set_recording_state(self) -> None:
        """Configure recording state."""
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._status_label.setText("Listening...")
        self._status_label.show()
        self._pulse_timer.start(self.PULSE_INTERVAL_MS)

    def _set_transcribing_state(self) -> None:
        """Configure transcribing state."""
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._status_label.setText("Thinking...")
        self._status_label.show()
        self._pulse_timer.stop()
        self.update()

    def _animate_resize(self, target_width: int, target_height: int) -> None:
        """Animate window resize."""
        screen = QApplication.primaryScreen().geometry()
        target_x = (screen.width() - target_width) // 2
        
        start_rect = self.geometry()
        end_rect = QRect(target_x, OVERLAY_TOP_MARGIN, target_width, target_height)
        
        self._geometry_animation.setStartValue(start_rect)
        self._geometry_animation.setEndValue(end_rect)
        self._geometry_animation.start()
