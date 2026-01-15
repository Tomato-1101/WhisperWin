"""
WhisperWin - Windows用音声文字起こしアプリケーション

ローカルGPUまたはGroq/OpenAI APIを使用した高速音声認識に対応した、
プライバシー重視の音声入力ツール。
"""

__version__ = "2.0.0"
__author__ = "WhisperWin Team"

from .app import SuperWhisperApp
from .main import main

__all__ = [
    "SuperWhisperApp",  # メインアプリケーションクラス
    "main",             # エントリーポイント関数
    "__version__",      # バージョン番号
]
