"""
UIモジュール

設定ウィンドウとシステムトレイ／メニューバーアイコンを提供する。
状態表示はトレイアイコンの色で行うため、画面上部に浮く Dynamic Island
オーバーレイは持たない（廃止済み）。
"""

from .settings_window import SettingsWindow
from .system_tray import SystemTray

__all__ = [
    "SettingsWindow",        # 設定ウィンドウ
    "SystemTray",            # システムトレイアイコン
]
