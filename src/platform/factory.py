"""
プラットフォーム実装ファクトリ。
"""

import sys
from functools import lru_cache
from typing import Optional

from .base import PlatformAdapter
from .macos import MacOSPlatformAdapter
from .windows import WindowsPlatformAdapter


class GenericPlatformAdapter(WindowsPlatformAdapter):
    """
    非対応OS向けフォールバック。

    キー挿入はCtrl系を使用し、Windows互換の設定で動作する。
    """

    name = "generic"
    font_css_stack = "'Arial'"


@lru_cache(maxsize=1)
def get_platform_adapter(platform_name: Optional[str] = None) -> PlatformAdapter:
    """
    実行OSに応じたプラットフォーム実装を返す。
    """
    current = (platform_name or sys.platform).lower()
    if current == "darwin":
        return MacOSPlatformAdapter()
    if current.startswith("win"):
        return WindowsPlatformAdapter()
    return GenericPlatformAdapter()
