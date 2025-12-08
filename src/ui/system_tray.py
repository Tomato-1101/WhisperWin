"""System tray icon with status indication and menu."""

from typing import Union

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from ..config.types import AppState


class SystemTray(QSystemTrayIcon):
    """
    System tray icon with dynamic status indication.
    
    Provides status display via colored icon and context menu
    for settings and quit actions.
    """
    
    # Signals for menu actions
    open_settings = pyqtSignal()
    quit_app = pyqtSignal()
    
    # Icon colors for different states
    ICON_COLORS = {
        AppState.IDLE: QColor("dodgerblue"),
        AppState.RECORDING: QColor("red"),
        AppState.TRANSCRIBING: QColor("orange"),
    }
    
    # Icon size
    ICON_SIZE = 64
    
    def __init__(self, parent=None) -> None:
        """Initialize the system tray icon."""
        super().__init__(parent)
        
        self._setup_icon()
        self._setup_menu()
        self._setup_click_handler()
        
        self.show()

    def _setup_icon(self) -> None:
        """Set up the initial icon."""
        self._set_icon_color(self.ICON_COLORS[AppState.IDLE])

    def _setup_menu(self) -> None:
        """Set up the context menu."""
        self._menu = QMenu()
        
        # Settings action
        settings_action = self._menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings.emit)
        
        self._menu.addSeparator()
        
        # Quit action
        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app.emit)
        
        self.setContextMenu(self._menu)

    def _setup_click_handler(self) -> None:
        """Set up the click handler."""
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Handle tray icon activation.

        Args:
            reason: The type of activation that occurred (click, double-click, etc.).
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_settings.emit()

    def set_status(self, status: Union[str, AppState]) -> None:
        """
        Update icon based on application status.
        
        Args:
            status: Current application state.
        """
        # Convert string to AppState if needed
        if isinstance(status, str):
            status = AppState(status)
        
        color = self.ICON_COLORS.get(status, self.ICON_COLORS[AppState.IDLE])
        tooltip = self._get_tooltip(status)
        
        self._set_icon_color(color)
        self.setToolTip(tooltip)

    def _get_tooltip(self, status: AppState) -> str:
        """
        Get tooltip text for the given status.

        Args:
            status: Current application state.

        Returns:
            Tooltip text string for the system tray icon.
        """
        tooltips = {
            AppState.IDLE: "SuperWhisper - Ready",
            AppState.RECORDING: "SuperWhisper - Recording",
            AppState.TRANSCRIBING: "SuperWhisper - Transcribing",
        }
        return tooltips.get(status, "SuperWhisper")

    def _set_icon_color(self, color: QColor) -> None:
        """
        Generate and set a colored circle icon.
        
        Args:
            color: The color for the icon.
        """
        size = self.ICON_SIZE
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, size - 8, size - 8)
        
        painter.end()
        
        self.setIcon(QIcon(pixmap))
