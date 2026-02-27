"""
アプリケーション定数・デフォルト設定モジュール

アプリケーション全体で使用される定数値と、
settings.yamlが存在しない場合のデフォルト設定を定義する。
"""

from typing import Any, Dict

from .types import HotkeyMode

# ============================================
# アプリケーションメタデータ
# ============================================
APP_NAME: str = "WhisperWin"
APP_VERSION: str = "1.0.0"

# ============================================
# 音声設定
# ============================================
SAMPLE_RATE: int = 16000      # サンプリングレート（Hz）
AUDIO_CHANNELS: int = 1       # チャンネル数（モノラル）
AUDIO_DTYPE: str = "float32"  # 音声データ型

# ============================================
# UI設定
# ============================================
OVERLAY_BASE_WIDTH: int = 60        # オーバーレイ基本幅（コンパクト）
OVERLAY_BASE_HEIGHT: int = 28       # オーバーレイ基本高さ
OVERLAY_EXPANDED_WIDTH: int = 160   # オーバーレイ拡張時の幅
OVERLAY_EXPANDED_HEIGHT: int = 36   # オーバーレイ拡張時の高さ
OVERLAY_TOP_MARGIN: int = 16        # 画面上端からのマージン
ANIMATION_DURATION_MS: int = 250    # アニメーション時間（高速化）

# ============================================
# タイミング設定
# ============================================
CONFIG_CHECK_INTERVAL_SEC: int = 1          # 設定ファイル監視間隔（秒）
# ============================================
# デフォルト設定
# ============================================
# settings.yamlが存在しない場合や、キーが欠けている場合に使用される
DEFAULT_CONFIG: Dict[str, Any] = {
    # グローバル設定（両ホットキー共通）
    "language": "ja",
    "vad_filter": True,
    "vad_min_silence_duration_ms": 500,

    # ホットキー1 設定
    "hotkey1": {
        "hotkey": "<f2>",
        "hotkey_mode": HotkeyMode.TOGGLE.value,
        "backend": "openai",
        "api_model": "",
        "api_prompt": "",
    },

    # ホットキー2 設定
    "hotkey2": {
        "hotkey": "<f3>",
        "hotkey_mode": HotkeyMode.TOGGLE.value,
        "backend": "groq",
        "api_model": "",
        "api_prompt": "",
    },

    # APIモデルデフォルト値（バックエンド別）
    "default_api_models": {
        "groq": "whisper-large-v3-turbo",
        "openai": "gpt-4o-mini-transcribe",
    },

    # 開発者モード - 出力を引用符で囲み、タイミングをファイルに記録
    "dev_mode": False,

    # 起動時プリロード - 起動時にVADを事前ロードして最初の文字起こしを高速化
    "preload_on_startup": True,
}

# ============================================
# ファイル名
# ============================================
SETTINGS_FILE_NAME: str = "settings.yaml"
