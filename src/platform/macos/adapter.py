"""
macOS向けプラットフォーム実装。
"""

from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSystemTrayIcon
from pynput.keyboard import Key

from ...utils.logger import get_logger
from ..base import PlatformAdapter
from ..common import normalize_listener_key, qt_key_to_hotkey_token

logger = get_logger(__name__)


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

    # --- ウィンドウ可視性制御（macOS 固有） ---

    def configure_app_visibility(self, hide_from_dock: bool) -> None:
        """
        Dock / Cmd+Tab からアプリを隠す（Accessory モード）。

        メニューバー常駐型アプリとして動作させたい場合に True を渡す。
        PyInstaller ビルド版は Info.plist の `LSUIElement=true` で起動時から
        この状態になるが、`python run.py` で開発実行する場合は本メソッドで
        ランタイムにポリシーを変更する必要がある。
        """
        if not hide_from_dock:
            return
        try:
            # ローカルインポート: pyobjc は macOS でしか入らないため、
            # モジュールロード時に失敗しないよう呼び出し時に import する。
            from AppKit import NSApp, NSApplicationActivationPolicyAccessory  # type: ignore
        except Exception as e:
            logger.warning(f"AppKit を import できないため Dock 非表示を適用しません: {e}")
            return
        try:
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
            logger.debug("macOS Activation Policy を Accessory に設定しました")
        except Exception as e:
            logger.warning(f"Activation Policy 変更に失敗: {e}")

    def bring_to_front(self, window) -> None:
        """
        メニューバーから設定を開いた時に確実に前面化する。

        Accessory モードでは `raise_()` / `activateWindow()` だけでは
        他アプリの上に出ないことがあるため、AppKit 経由で
        `activateIgnoringOtherApps_(True)` を呼ぶ。
        """
        try:
            from AppKit import NSApp  # type: ignore
        except Exception as e:
            logger.debug(f"AppKit 不在のため bring_to_front をスキップ: {e}")
            return
        try:
            NSApp.activateIgnoringOtherApps_(True)
        except Exception as e:
            logger.warning(f"NSApp.activateIgnoringOtherApps_ 失敗: {e}")
