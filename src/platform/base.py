"""
プラットフォーム抽象レイヤー。

OS差分（入力挿入・キー正規化・トレイ挙動・フォント）を
共通インターフェースとして定義する。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Sequence

from pynput.keyboard import Key


class PlatformAdapter(ABC):
    """OS別機能を提供する抽象インターフェース。"""

    name: str = "unknown"
    font_css_stack: str = "'Arial'"

    @property
    @abstractmethod
    def paste_modifier(self) -> Key:
        """貼り付けショートカットで使用する修飾キーを返す。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def tray_open_reasons(self) -> Sequence[Any]:
        """設定UIを開くトレイアクティベーション理由一覧を返す。"""
        raise NotImplementedError

    def is_tray_open_reason(self, reason: Any) -> bool:
        """トレイのアクティベーション理由が設定表示対象か判定する。"""
        return reason in self.tray_open_reasons

    @abstractmethod
    def normalize_listener_key(self, key: Any) -> Optional[str]:
        """pynputキーイベントを正規化文字列へ変換する。"""
        raise NotImplementedError

    @abstractmethod
    def modifier_hotkey_from_native(
        self,
        virtual_key: int,
        scan_code: int = 0,
        qt_key: Optional[int] = None,
    ) -> str:
        """Qtネイティブキー情報から修飾キー表現を返す。"""
        raise NotImplementedError

    @abstractmethod
    def qt_key_to_hotkey_token(self, key: int, scan_code: int = 0) -> str:
        """Qtキーコードをpynput形式トークンに変換する。"""
        raise NotImplementedError
