"""
設定モジュール

アプリケーションの設定管理、定数、型定義を提供する。
ConfigManagerを通じて設定の読み込み・保存・ホットリロードが可能。
"""

from .config_manager import ConfigManager
from .constants import APP_NAME, DEFAULT_CONFIG, SAMPLE_RATE
from .types import AppConfig, ComputeType, HotkeyMode, ModelSize, TranscriptionBackend

__all__ = [
    "HotkeyMode",           # ホットキーモード列挙型
    "ModelSize",            # モデルサイズ列挙型
    "ComputeType",          # 計算精度列挙型
    "AppConfig",            # アプリ設定データクラス
    "TranscriptionBackend", # バックエンド列挙型
    "DEFAULT_CONFIG",       # デフォルト設定辞書
    "SAMPLE_RATE",          # サンプリングレート
    "APP_NAME",             # アプリケーション名
    "ConfigManager",        # 設定管理クラス
]
