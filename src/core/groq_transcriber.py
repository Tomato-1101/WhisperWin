"""
Groq API文字起こしモジュール

Groq CloudのWhisper APIを使用して高速な文字起こしを行う。
ローカルGPU不要で、リアルタイムの最大300倍の速度を実現。
"""

import io
import os
from typing import Optional

import numpy as np
import numpy.typing as npt

from .audio_utils import numpy_to_wav_bytes
from ..config.constants import SAMPLE_RATE
from ..utils.logger import get_logger
from .vad import VadFilter

logger = get_logger(__name__)

# Groq SDKの遅延インポート（未インストール時のエラー回避）
_groq_available: bool = False
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    Groq = None  # type: ignore
    logger.warning("Groq SDKがインストールされていません。pip install groq で追加できます")


class GroqTranscriber:
    """
    Groq API経由のクラウド文字起こしクラス。
    
    Groq CloudのWhisper APIを使用し、ローカルGPUなしで
    超高速な文字起こしを実現する。
    
    特徴:
    - 超高速文字起こし（リアルタイムの最大300倍）
    - ローカルGPU不要
    - whisper-large-v3-turbo等のモデルをサポート
    
    Note:
        GROQ_API_KEY環境変数の設定が必要。
    """

    # Groqでサポートされているモデル
    AVAILABLE_MODELS = [
        "whisper-large-v3-turbo",    # 推奨：最速
        "whisper-large-v3",           # 高精度
        "distil-whisper-large-v3-en"  # 英語最適化
    ]

    def __init__(
        self,
        model: str = "whisper-large-v3-turbo",
        language: str = "ja",
        temperature: float = 0.0,
        sample_rate: int = SAMPLE_RATE,
        vad_filter: bool = True,
        vad_min_silence_duration_ms: int = 500
    ) -> None:
        """
        GroqTranscriberを初期化する。
        
        Args:
            model: Groq Whisperモデル名
            language: 言語コード（'ja', 'en'等）
            temperature: サンプリング温度（0.0=決定論的）
            sample_rate: サンプリングレート（Hz）
            vad_filter: VADプリフィルタリングを有効にするか
            vad_min_silence_duration_ms: VADの最小無音時間
        """
        self.model = model
        self.language = language
        self.temperature = temperature
        self.sample_rate = sample_rate
        self._client: Optional[Groq] = None  # Groqクライアント（遅延初期化）
        
        # VAD設定
        self.vad_enabled = vad_filter
        self._vad_filter: Optional[VadFilter] = None
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        if vad_filter:
            self._vad_filter = VadFilter(
                min_silence_duration_ms=vad_min_silence_duration_ms,
                use_cuda=True  # VADにはCUDAを使用
            )

        # モデル名の検証
        if model not in self.AVAILABLE_MODELS:
            logger.warning(
                f"モデル '{model}' は利用できない可能性があります。 "
                f"推奨モデル: {', '.join(self.AVAILABLE_MODELS)}"
            )

    def is_available(self) -> bool:
        """
        Groq APIが利用可能かを確認する。
        
        Returns:
            SDKがインストール済みでAPIキーが設定されている場合True
        """
        if not _groq_available:
            return False

        api_key = os.environ.get("GROQ_API_KEY")
        return bool(api_key)

    def _get_client(self) -> Groq:
        """
        Groqクライアントを取得または作成する。
        
        Returns:
            初期化済みのGroqクライアント
        
        Raises:
            RuntimeError: APIキーが設定されていない場合
        """
        if self._client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "GROQ_API_KEY環境変数が設定されていません。 "
                    "export GROQ_API_KEY='gsk_...' で設定してください"
                )
            self._client = Groq(api_key=api_key)
        return self._client

    def transcribe(self, audio_data: npt.NDArray[np.float32]) -> str:
        """
        Groq APIを使用して音声を文字起こしする。
        
        Args:
            audio_data: 音声データ（float32、モノラルのNumPy配列）
        
        Returns:
            文字起こし結果、またはエラーメッセージ（"Error:"で始まる）
        """
        # タイミング情報をリセット
        self.last_vad_time = 0
        self.last_api_time = 0
        
        if len(audio_data) == 0:
            return ""

        import time
        
        # VADフィルター：発話がない場合はAPI呼び出しをスキップ
        if self.vad_enabled and self._vad_filter:
            vad_start = time.perf_counter()
            has_speech = self._vad_filter.has_speech(audio_data, self.sample_rate)
            self.last_vad_time = (time.perf_counter() - vad_start) * 1000
            logger.info(f"VADチェック: has_speech={has_speech}, vad_time={self.last_vad_time:.0f}ms")
            if not has_speech:
                logger.debug("VAD: 発話が検出されなかったため、Groq API呼び出しをスキップします。")
                return ""

        if not self.is_available():
            if not _groq_available:
                return "Error: Groq SDKがインストールされていません。pip install groq で追加してください"
            return "Error: GROQ_API_KEY環境変数が設定されていません"

        try:
            # NumPy配列をWAVバイト列に変換
            wav_bytes = numpy_to_wav_bytes(audio_data, self.sample_rate)
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"

            # Groq API呼び出し（API時間を計測）
            api_start = time.perf_counter()
            client = self._get_client()
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=self.language if self.language else None,
                temperature=self.temperature,
                response_format="text"
            )
            self.last_api_time = (time.perf_counter() - api_start) * 1000

            # テキスト抽出（レスポンス形式に応じて処理）
            if isinstance(transcription, str):
                text = transcription.strip()
            elif hasattr(transcription, 'text'):
                text = transcription.text.strip()
            else:
                # 予期しない型への対応
                text = str(transcription).strip()
            logger.debug(f"Groq文字起こし: {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"Groq文字起こしエラー: {e}")
            return f"Error: {e}"

    def load_model(self) -> None:
        """
        Groqクライアントを事前初期化する（オプション）。
        
        Groq APIはサーバーレスのため、実際のモデルロードは不要。
        """
        if self.is_available():
            try:
                self._get_client()
                logger.debug("Groqクライアントを初期化しました")
            except Exception as e:
                logger.warning(f"Groqクライアントの初期化に失敗: {e}")

    def unload_model(self) -> None:
        """
        クライアント参照をクリアする。
        
        Groq APIはサーバーレスのため、キャッシュされたクライアントをクリアするのみ。
        """
        self._client = None
        logger.debug("Groqクライアント参照をクリアしました")

    def preload_vad(self) -> None:
        """
        VADモデルを事前にロードする。
        
        アプリ起動時に呼び出すことで、最初の音声入力時の
        VADモデルロード遅延を回避できる。
        """
        if self.vad_enabled and self._vad_filter:
            self._vad_filter.preload_model()

