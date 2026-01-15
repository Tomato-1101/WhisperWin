"""
コアビジネスロジックモジュール

音声録音、文字起こし、テキスト入力など、
アプリケーションの中核機能を提供するモジュール群。
"""

from .audio_recorder import AudioRecorder
from .groq_transcriber import GroqTranscriber
from .input_handler import InputHandler
from .openai_transcriber import OpenAITranscriber
from .transcriber import Transcriber

__all__ = [
    "AudioRecorder",       # 音声録音
    "Transcriber",         # ローカルWhisper文字起こし
    "GroqTranscriber",     # Groq API文字起こし
    "OpenAITranscriber",   # OpenAI API文字起こし
    "InputHandler",        # テキスト入力
]
