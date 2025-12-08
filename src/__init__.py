"""
WhisperWin - Windows用音声文字起こしアプリケーション

ローカルGPUまたはGroq APIを使用した高速音声認識と、
LLMによる後処理機能を備えた、プライバシー重視の音声入力ツール。
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
