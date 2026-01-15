"""
型定義モジュール

アプリケーション設定で使用される列挙型とデータクラスを定義する。
型安全な設定管理のための基盤を提供する。
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class HotkeyMode(str, Enum):
    """
    ホットキー動作モード。
    
    Attributes:
        TOGGLE: トグルモード - 1回押して開始、もう1回押して停止
        HOLD: ホールドモード - 押している間録音、離すと停止
    """
    TOGGLE = "toggle"
    HOLD = "hold"


class ModelSize(str, Enum):
    """
    Whisperモデルサイズ。
    
    大きいモデルほど精度が高いが、メモリ使用量も増加する。
    """
    TINY = "tiny"                     # 最小・最速
    BASE = "base"                     # 基本
    SMALL = "small"                   # 小
    MEDIUM = "medium"                 # 中
    LARGE = "large"                   # 大
    LARGE_V2 = "large-v2"             # 大v2
    LARGE_V3 = "large-v3"             # 大v3（最高精度）
    DISTIL_LARGE_V2 = "distil-large-v2"      # 蒸留版（高速）
    DISTIL_MEDIUM_EN = "distil-medium.en"    # 蒸留版（英語特化）


class ComputeType(str, Enum):
    """
    モデル推論の計算精度タイプ。
    
    低精度ほど高速・省メモリだが、精度が若干低下する可能性がある。
    """
    FLOAT16 = "float16"           # 16bit浮動小数点（推奨）
    INT8_FLOAT16 = "int8_float16"  # INT8量子化（より省メモリ）
    INT8 = "int8"                  # INT8（最も省メモリ）


class AppState(str, Enum):
    """
    アプリケーション状態。
    
    UIの表示やシステムトレイアイコンの色に使用される。
    """
    IDLE = "idle"                  # 待機中
    RECORDING = "recording"        # 録音中
    TRANSCRIBING = "transcribing"  # 文字起こし中


class TranscriptionBackend(str, Enum):
    """
    文字起こしバックエンドタイプ。

    Attributes:
        LOCAL: ローカルGPU（faster-whisper）
        GROQ: Groq Cloud API
        OPENAI: OpenAI GPT-4o Transcribe API
    """
    LOCAL = "local"
    GROQ = "groq"
    OPENAI = "openai"


@dataclass
class TranscriberConfig:
    """
    文字起こしモジュールの設定。
    
    ローカルWhisperモデルの各種パラメータを保持する。
    """
    model_size: str = ModelSize.BASE.value
    compute_type: str = ComputeType.FLOAT16.value
    language: str = "ja"
    release_memory_delay: int = 300
    vad_filter: bool = True
    vad_min_silence_duration_ms: int = 500
    condition_on_previous_text: bool = False
    no_speech_threshold: float = 0.6
    log_prob_threshold: float = -1.0
    no_speech_prob_cutoff: float = 0.7
    beam_size: int = 5
    model_cache_dir: str = ""


@dataclass
class HotkeyConfig:
    """ホットキー設定。"""
    hotkey: str = "<f2>"
    hotkey_mode: str = HotkeyMode.TOGGLE.value


@dataclass
class HotkeySlotConfig:
    """
    個別ホットキースロットの設定。

    各ホットキーに対して、キーバインド、動作モード、
    使用するバックエンドとAPIモデル設定を保持する。

    Attributes:
        hotkey: ホットキー文字列（例: "<shift_r>", "<ctrl>+<space>"）
        hotkey_mode: 動作モード（hold/toggle）
        backend: 使用するバックエンド（local/groq/openai）
        api_model: APIバックエンド使用時のモデル名
        api_prompt: APIバックエンド使用時のプロンプト
    """
    hotkey: str = "<f2>"
    hotkey_mode: str = HotkeyMode.TOGGLE.value
    backend: str = TranscriptionBackend.LOCAL.value
    api_model: str = ""
    api_prompt: str = ""


@dataclass
class AppConfig:
    """
    アプリケーション全体の設定。
    
    すべての設定項目を一つにまとめたデータクラス。
    """
    # ホットキー設定
    hotkey: str = "<f2>"
    hotkey_mode: str = HotkeyMode.TOGGLE.value
    
    # モデル設定
    model_size: str = ModelSize.BASE.value
    compute_type: str = ComputeType.FLOAT16.value
    language: str = "ja"
    model_cache_dir: str = ""
    
    # 文字起こし設定
    release_memory_delay: int = 300
    vad_filter: bool = True
    vad_min_silence_duration_ms: int = 500
    condition_on_previous_text: bool = False
    no_speech_threshold: float = 0.6
    log_prob_threshold: float = -1.0
    no_speech_prob_cutoff: float = 0.7
    beam_size: int = 5
