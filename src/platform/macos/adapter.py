"""
macOS向けプラットフォーム実装。
"""

from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSystemTrayIcon
from pynput.keyboard import Key

from ..base import PlatformAdapter
from ..common import normalize_listener_key, qt_key_to_hotkey_token


class MacOSPlatformAdapter(PlatformAdapter):
    """macOS差分実装。"""

    name = "macos"
    font_css_stack = "'Helvetica Neue', '.AppleSystemUIFont', 'Arial'"

    _MODIFIER_VK_MAP = {
        59: "<ctrl_l>",
        62: "<ctrl_r>",
        56: "<shift_l>",
        60: "<shift_r>",
        58: "<alt_l>",
        61: "<alt_r>",
        55: "<cmd_l>",
        54: "<cmd_r>",
    }

    _MODIFIER_SCAN_MAP = {
        59: "<ctrl_l>",
        62: "<ctrl_r>",
        56: "<shift_l>",
        60: "<shift_r>",
        58: "<alt_l>",
        61: "<alt_r>",
        55: "<cmd_l>",
        54: "<cmd_r>",
    }

    _QT_FALLBACK_MODIFIERS = {
        Qt.Key.Key_Control: "<ctrl>",
        Qt.Key.Key_Shift: "<shift>",
        Qt.Key.Key_Alt: "<alt>",
        Qt.Key.Key_Meta: "<cmd>",
    }

    @property
    def paste_modifier(self) -> Key:
        return Key.cmd

    @property
    def tray_open_reasons(self) -> Sequence[QSystemTrayIcon.ActivationReason]:
        return (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        )

    def normalize_listener_key(self, key) -> Optional[str]:
        return normalize_listener_key(key)

    def modifier_hotkey_from_native(
        self,
        virtual_key: int,
        scan_code: int = 0,
        qt_key: Optional[int] = None,
    ) -> str:
        if virtual_key in self._MODIFIER_VK_MAP:
            return self._MODIFIER_VK_MAP[virtual_key]
        if scan_code in self._MODIFIER_SCAN_MAP:
            return self._MODIFIER_SCAN_MAP[scan_code]
        if qt_key is not None and qt_key in self._QT_FALLBACK_MODIFIERS:
            return self._QT_FALLBACK_MODIFIERS[qt_key]
        return ""

    def qt_key_to_hotkey_token(self, key: int, scan_code: int = 0) -> str:
        return qt_key_to_hotkey_token(key, scan_code)
