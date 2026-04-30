"""OS別実装レイヤー。"""

from .base import PlatformAdapter
from .factory import get_platform_adapter

__all__ = ["PlatformAdapter", "get_platform_adapter"]
