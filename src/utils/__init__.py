"""
ユーティリティモジュール

ロギングなど、アプリケーション全体で共有される
汎用ユーティリティ機能を提供する。
"""

from .logger import setup_logger, get_logger

__all__ = [
    "setup_logger",  # ロガー設定関数
    "get_logger",    # ロガー取得関数
]
