"""プラットフォーム共通ユーティリティ。"""

from .keymap import normalize_listener_key, qt_key_to_hotkey_token

__all__ = ["normalize_listener_key", "qt_key_to_hotkey_token"]
