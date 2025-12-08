"""
ロギングモジュール

アプリケーション全体で使用されるロギング機能を提供する。
コンソールとファイルへの同時出力に対応。
"""

import logging
import sys
from typing import Dict, Optional

# デフォルトのログフォーマット
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# シングルトンロガーインスタンス
_loggers: Dict[str, logging.Logger] = {}
_is_configured: bool = False


def setup_logger(
    log_file: Optional[str] = "app.log",
    level: int = logging.INFO,
    format_string: str = LOG_FORMAT
) -> None:
    """
    ルートロガーをコンソールとファイルハンドラーで設定する。
    
    Args:
        log_file: ログファイルパス。Noneでファイル出力を無効化
        level: ログレベル（デフォルト: INFO）
        format_string: ログメッセージフォーマット
    """
    global _is_configured
    
    # 二重設定を防止
    if _is_configured:
        return
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers
    )
    
    _is_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    名前でロガーインスタンスを取得する（キャッシュ付き）。
    
    Args:
        name: ロガー名（通常は__name__）
        
    Returns:
        設定済みのロガーインスタンス
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]
