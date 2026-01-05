"""
アプリケーション定数・デフォルト設定モジュール

アプリケーション全体で使用される定数値と、
settings.yamlが存在しない場合のデフォルト設定を定義する。
"""

from typing import Any, Dict

from .types import ComputeType, HotkeyMode, ModelSize

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
DEFAULT_MEMORY_RELEASE_DELAY_SEC: int = 300  # VRAM解放までの待機時間（秒）

# ============================================
# デフォルト設定
# ============================================
# settings.yamlが存在しない場合や、キーが欠けている場合に使用される
DEFAULT_CONFIG: Dict[str, Any] = {
    # ホットキー設定
    "hotkey": "<f2>",
    "hotkey_mode": HotkeyMode.TOGGLE.value,

    # 文字起こしバックエンド
    "transcription_backend": "local",  # "local" または "groq"

    # モデル設定（ローカルバックエンド用）
    "model_size": ModelSize.BASE.value,
    "compute_type": ComputeType.FLOAT16.value,
    "language": "ja",
    "model_cache_dir": "",

    # Groq API設定
    "groq_model": "whisper-large-v3-turbo",  # APIキーは環境変数GROQ_API_KEYから取得

    # 文字起こし設定
    "release_memory_delay": DEFAULT_MEMORY_RELEASE_DELAY_SEC,
    "vad_filter": True,
    "vad_min_silence_duration_ms": 500,
    "condition_on_previous_text": False,
    "no_speech_threshold": 0.6,
    "log_prob_threshold": -1.0,
    "no_speech_prob_cutoff": 0.7,
    "beam_size": 5,

    # 開発者モード - 出力を引用符で囲み、タイミングをファイルに記録
    "dev_mode": False,

    # LLM後処理設定（system_promptはprompt.xmlから読み込む）
    "llm_postprocess": {
        "enabled": False,
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "timeout": 5.0,
        "fallback_on_error": True,
    },
}

# ============================================
# ファイル名
# ============================================
SETTINGS_FILE_NAME: str = "settings.yaml"
