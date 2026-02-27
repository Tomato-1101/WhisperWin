"""
テキスト入力ハンドラーモジュール

クリップボードとキーボードシミュレーションを使用して、
文字起こし結果をアクティブなウィンドウに入力する機能を提供する。
日本語などのマルチバイト文字にも対応。
"""

import time
from typing import Optional

import pyperclip
from pynput.keyboard import Controller

from ..utils.logger import get_logger
from ..platform import PlatformAdapter, get_platform_adapter

logger = get_logger(__name__)

# クリップボード貼り付け前の待機時間（秒）
PASTE_DELAY: float = 0.1


class InputHandler:
    """
    テキスト入力シミュレーションを管理するクラス。
    
    クリップボード経由でCtrl+Vを使用することで、
    日本語や中国語などのマルチバイト文字を確実に入力できる。
    """
    
    def __init__(self, platform_adapter: Optional[PlatformAdapter] = None) -> None:
        """キーボードコントローラーを初期化する。"""
        self._keyboard = Controller()
        self._platform = platform_adapter or get_platform_adapter()

    def insert_text(self, text: str) -> bool:
        """
        アクティブウィンドウにテキストを挿入する。
        
        クリップボード経由でCtrl+Vを使用することで、
        マルチバイト文字を確実に入力できる。
        
        Args:
            text: 挿入するテキスト
            
        Returns:
            成功した場合True、失敗した場合False
        """
        if not text:
            return False

        try:
            # クリップボードにコピー
            pyperclip.copy(text)
            
            # クリップボードの準備が整うまで少し待機
            time.sleep(PASTE_DELAY)
            
            # OS別アダプタが定義する貼り付けショートカットを使用
            paste_modifier = self._platform.paste_modifier
            with self._keyboard.pressed(paste_modifier):
                self._keyboard.press('v')
                self._keyboard.release('v')
            
            logger.debug(f"テキスト挿入: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"テキスト挿入エラー: {e}")
            return False

    def type_text(self, text: str) -> bool:
        """
        テキストを1文字ずつ入力する。
        
        注意: この方法はinsert_text()より遅く、
        非ASCII文字では信頼性が低いため、
        通常はinsert_text()の使用を推奨。
        
        Args:
            text: 入力するテキスト
            
        Returns:
            成功した場合True、失敗した場合False
        """
        if not text:
            return False
            
        try:
            self._keyboard.type(text)
            return True
        except Exception as e:
            logger.error(f"テキスト入力エラー: {e}")
            return False
