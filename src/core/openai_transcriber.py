"""
OpenAI GPT-4o文字起こしモジュール

OpenAI Audio Transcriptions APIを使用して高精度な文字起こしを行う。
gpt-4o-transcribe / gpt-4o-mini-transcribe モデルをサポート。
"""

import io
import os
import time
from typing import Optional

import httpx

import numpy as np
import numpy.typing as npt

from .audio_utils import numpy_to_audio_bytes
from ..config.constants import SAMPLE_RATE
from ..utils.logger import get_logger
from .vad import VadFilter

logger = get_logger(__name__)

# OpenAI SDKの遅延インポート（未インストール時のエラー回避）
_openai_available: bool = False
try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    OpenAI = None  # type: ignore
    logger.warning("OpenAI SDKがインストールされていません。pip install openai で追加できます")


class OpenAITranscriber:
    """
    OpenAI API経由のクラウド文字起こしクラス。

    OpenAIのGPT-4oベースAudio Transcription APIを使用し、
    高精度な文字起こしを実現する。

    特徴:
    - GPT-4oベースの高精度文字起こし
    - ローカルGPU不要
    - gpt-4o-transcribe / gpt-4o-mini-transcribe をサポート

    Note:
        OPENAI_API_KEY環境変数の設定が必要。
    """

    # OpenAIでサポートされている文字起こしモデル
    AVAILABLE_MODELS = [
        "gpt-4o-transcribe",       # 高精度
        "gpt-4o-mini-transcribe",  # 推奨：コスト効率
    ]

    def __init__(
        self,
        model: str = "gpt-4o-mini-transcribe",
        language: str = "ja",
        prompt: str = "",
        temperature: float = 0.0,
        sample_rate: int = SAMPLE_RATE,
        vad_filter: bool = True,
        vad_min_silence_duration_ms: int = 500
    ) -> None:
        """
        OpenAITranscriberを初期化する。

        Args:
            model: OpenAI文字起こしモデル名
            language: 言語コード（'ja', 'en'等）
            prompt: 文字起こしのヒントテキスト
            temperature: サンプリング温度（0.0=決定論的）
            sample_rate: サンプリングレート（Hz）
            vad_filter: VADプリフィルタリングを有効にするか
            vad_min_silence_duration_ms: VADの最小無音時間
        """
        self.model = model
        self.language = language
        self.prompt = prompt
        self.temperature = temperature
        self.sample_rate = sample_rate
        self._client: Optional[OpenAI] = None  # OpenAIクライアント（遅延初期化）

        # VAD設定
        self.vad_enabled = vad_filter
        self._vad_filter: Optional[VadFilter] = None
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        if vad_filter:
            self._vad_filter = VadFilter(
                min_silence_duration_ms=vad_min_silence_duration_ms,
                use_cuda=True  # 利用可能なハードウェアアクセラレーションを使用
            )

        # タイミング情報
        self.last_vad_time = 0
        self.last_api_time = 0

        # モデル名の検証
        if model not in self.AVAILABLE_MODELS:
            logger.warning(
                f"モデル '{model}' は利用できない可能性があります。 "
                f"推奨モデル: {', '.join(self.AVAILABLE_MODELS)}"
            )

    def is_available(self) -> bool:
        """
        OpenAI APIが利用可能かを確認する。

        Returns:
            SDKがインストール済みでAPIキーが設定されている場合True
        """
        if not _openai_available:
            return False

        api_key = os.environ.get("OPENAI_API_KEY")
        return bool(api_key)

    def _get_client(self) -> OpenAI:
        """
        OpenAIクライアントを取得または作成する。

        Returns:
            初期化済みのOpenAIクライアント

        Raises:
            RuntimeError: APIキーが設定されていない場合
        """
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY環境変数が設定されていません。 "
                    "export OPENAI_API_KEY='sk-...' で設定してください"
                )
            # HTTPコネクションプーリングで高速化 + 20秒タイムアウト
            http_client = httpx.Client(
                timeout=httpx.Timeout(20.0, connect=5.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
            self._client = OpenAI(api_key=api_key, http_client=http_client)
        return self._client

    def transcribe(self, audio_data: npt.NDArray[np.float32]) -> str:
        """
        OpenAI APIを使用して音声を文字起こしする。

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

        # VADフィルター：発話がない場合はAPI呼び出しをスキップ
        if self.vad_enabled and self._vad_filter:
            vad_start = time.perf_counter()
            has_speech = self._vad_filter.has_speech(audio_data, self.sample_rate)
            self.last_vad_time = (time.perf_counter() - vad_start) * 1000
            logger.info(f"VADチェック: has_speech={has_speech}, vad_time={self.last_vad_time:.0f}ms")
            if not has_speech:
                logger.debug("VAD: 発話が検出されなかったため、OpenAI API呼び出しをスキップします。")
                return ""

        if not self.is_available():
            if not _openai_available:
                return "Error: OpenAI SDKがインストールされていません。pip install openai で追加してください"
            return "Error: OPENAI_API_KEY環境変数が設定されていません"

        try:
            # NumPy配列をMP3に変換（WAVより約10倍小さい）、ffmpegがなければWAVにフォールバック
            audio_bytes, audio_ext = numpy_to_audio_bytes(audio_data, self.sample_rate, format="mp3")
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"audio.{audio_ext}"

            # OpenAI API呼び出し（API時間を計測）
            api_start = time.perf_counter()
            client = self._get_client()
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=self.language if self.language else None,
                prompt=self.prompt if self.prompt else None,
                temperature=self.temperature,
                response_format="text"
            )
            self.last_api_time = (time.perf_counter() - api_start) * 1000

            # テキスト抽出（レスポンス形式に応じて処理）
            if isinstance(transcription, str):
                text = transcription
            elif hasattr(transcription, 'text'):
                text = transcription.text
            else:
                # 予期しない型への対応
                text = str(transcription)

            # 前後のスペース・改行を確実に除去
            text = text.strip()

            logger.debug(f"OpenAI文字起こし: {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"OpenAI文字起こしエラー: {e}")
            return f"Error: {e}"

    def load_model(self) -> None:
        """
        OpenAIクライアントを事前初期化する（オプション）。

        OpenAI APIはサーバーレスのため、実際のモデルロードは不要。
        """
        if self.is_available():
            try:
                self._get_client()
                logger.debug("OpenAIクライアントを初期化しました")
            except Exception as e:
                logger.warning(f"OpenAIクライアントの初期化に失敗: {e}")

    def unload_model(self) -> None:
        """
        クライアント参照をクリアする。

        OpenAI APIはサーバーレスのため、キャッシュされたクライアントをクリアするのみ。
        """
        self._client = None
        logger.debug("OpenAIクライアント参照をクリアしました")

    def preload_vad(self) -> None:
        """
        VADモデルを事前にロードする。

        アプリ起動時に呼び出すことで、最初の音声入力時の
        VADモデルロード遅延を回避できる。
        """
        if self.vad_enabled and self._vad_filter:
            self._vad_filter.preload_model()
