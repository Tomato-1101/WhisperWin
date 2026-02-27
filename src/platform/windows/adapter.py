"""
Windows向けプラットフォーム実装。
"""

from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSystemTrayIcon
from pynput.keyboard import Key

from ..base import PlatformAdapter
from ..common import normalize_listener_key, qt_key_to_hotkey_token


class WindowsPlatformAdapter(PlatformAdapter):
    """Windows差分実装。"""

    name = "windows"
    font_css_stack = "'Segoe UI', 'Yu Gothic UI', 'Meiryo', 'Arial'"

    _MODIFIER_VK_MAP = {
        0xA2: "<ctrl_l>",
        0xA0: "<shift_l>",
        0xA4: "<alt_l>",
        0x5B: "<cmd_l>",
        0xA3: "<ctrl_r>",
        0xA1: "<shift_r>",
        0xA5: "<alt_r>",
        0x5C: "<cmd_r>",
    }

    _MODIFIER_SCAN_MAP = {
        29: "<ctrl_l>",
        42: "<shift_l>",
        56: "<alt_l>",
        285: "<ctrl_r>",
        54: "<shift_r>",
        312: "<alt_r>",
        57400: "<alt_r>",
        57372: "<ctrl_r>",
        57373: "<ctrl_r>",
    }

    _QT_FALLBACK_MODIFIERS = {
        Qt.Key.Key_Control: "<ctrl>",
        Qt.Key.Key_Shift: "<shift>",
        Qt.Key.Key_Alt: "<alt>",
        Qt.Key.Key_Meta: "<cmd>",
    }

    @property
    def paste_modifier(self) -> Key:
        return Key.ctrl

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
