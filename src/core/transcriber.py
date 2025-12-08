"""
ローカルWhisper文字起こしモジュール

faster-whisperを使用してGPU上で音声を文字起こしする。
VRAMの自動管理（遅延解放）機能付き。
"""

import os

# HuggingFace環境設定（インポート前に設定）
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"  # プログレスバー無効化
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # シンボリックリンク警告無効化
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"  # シンボリックリンク無効化

import gc
import threading
from typing import Optional

import numpy as np
import numpy.typing as npt
import torch
from faster_whisper import WhisperModel

from ..config.types import ModelSize, ComputeType
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Transcriber:
    """
    ローカルGPUでの音声文字起こしクラス。
    
    faster-whisperを使用してCUDA対応GPUで高速文字起こしを行う。
    VRAMの自動解放機能により、一定時間後にモデルをアンロードする。
    
    Attributes:
        model_size: Whisperモデルサイズ
        compute_type: 計算精度（float16, int8など）
        language: 言語コード
        release_memory_delay: VRAMを解放するまでの待機時間（秒）
    """
    
    def __init__(
        self,
        model_size: str = ModelSize.LARGE_V3.value,
        compute_type: str = ComputeType.FLOAT16.value,
        language: str = "ja",
        release_memory_delay: int = 300,
        vad_filter: bool = True,
        vad_min_silence_duration_ms: int = 500,
        condition_on_previous_text: bool = False,
        no_speech_threshold: float = 0.6,
        log_prob_threshold: float = -1.0,
        no_speech_prob_cutoff: float = 0.7,
        beam_size: int = 5,
        model_cache_dir: str = ""
    ) -> None:
        """
        Transcriberを初期化する。
        
        Args:
            model_size: Whisperモデルサイズ（tiny/base/small/medium/large等）
            compute_type: 計算精度タイプ
            language: 言語コード（ja, en等）
            release_memory_delay: VRAM解放までの待機秒数
            vad_filter: VAD（音声活性検出）を有効にするか
            vad_min_silence_duration_ms: VADの最小無音時間（ミリ秒）
            condition_on_previous_text: 前のテキストを条件付けに使用するか
            no_speech_threshold: 無発話判定閾値
            log_prob_threshold: ログ確率閾値
            no_speech_prob_cutoff: 無発話確率カットオフ
            beam_size: ビームサーチサイズ
            model_cache_dir: モデルキャッシュディレクトリ
            
        Raises:
            RuntimeError: CUDAが利用できない場合
        """
        # CUDA利用可否を確認
        if not torch.cuda.is_available():
            error_msg = "CUDAが利用できません。このアプリケーションにはCUDA対応GPUが必要です。"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # モデル設定
        self.model_size = model_size
        self.compute_type = compute_type
        self.language = language
        self.model_cache_dir = model_cache_dir or None
        
        # メモリ管理設定
        self.release_memory_delay = release_memory_delay
        
        # 文字起こし設定
        self.vad_filter = vad_filter
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        self.condition_on_previous_text = condition_on_previous_text
        self.no_speech_threshold = no_speech_threshold
        self.log_prob_threshold = log_prob_threshold
        self.no_speech_prob_cutoff = no_speech_prob_cutoff
        self.beam_size = beam_size
        
        # 内部状態
        self._model: Optional[WhisperModel] = None  # Whisperモデル
        self._unload_timer: Optional[threading.Timer] = None  # アンロードタイマー
        self._lock = threading.Lock()  # スレッドセーフ用ロック

    @property
    def model(self) -> Optional[WhisperModel]:
        """現在のモデルインスタンスを取得する。"""
        return self._model

    def load_model(self) -> None:
        """モデルをロードする（未ロードの場合）。"""
        with self._lock:
            self._cancel_unload_timer()
            
            if self._model is not None:
                return

            logger.info(
                f"faster-whisperモデル '{self.model_size}' を "
                f"cuda ({self.compute_type}) でロード中..."
            )
            
            try:
                model_kwargs = {
                    "device": "cuda",
                    "compute_type": self.compute_type,
                }
                
                if self.model_cache_dir:
                    model_kwargs["download_root"] = self.model_cache_dir
                    logger.info(f"モデルキャッシュディレクトリ: {self.model_cache_dir}")
                
                self._model = WhisperModel(self.model_size, **model_kwargs)
                logger.info("モデルのロードが完了しました。")
                
            except Exception as e:
                logger.error(f"モデルロードエラー: {e}")
                raise

    def unload_model(self) -> None:
        """モデルをアンロードしてVRAMを解放する。"""
        with self._lock:
            if self._model:
                logger.info("メモリ解放のためモデルをアンロード中...")
                del self._model
                self._model = None
                gc.collect()
                torch.cuda.empty_cache()
                logger.info("モデルをアンロードしました。")

    def transcribe(self, audio_data: npt.NDArray[np.float32]) -> str:
        """
        音声データを文字起こしする。
        
        Args:
            audio_data: 音声データ（float32のNumPy配列）
            
        Returns:
            文字起こし結果テキスト
        """
        if self._model is None:
            self.load_model()
            
        if len(audio_data) == 0:
            return ""

        try:
            # 文字起こし実行
            segments, info = self._model.transcribe(
                audio_data,
                language=self.language or None,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                vad_parameters={"min_silence_duration_ms": self.vad_min_silence_duration_ms},
                condition_on_previous_text=self.condition_on_previous_text,
                no_speech_threshold=self.no_speech_threshold,
                log_prob_threshold=self.log_prob_threshold,
            )
            
            # 無発話確率でフィルタリングしてテキスト収集
            text_segments = [
                segment.text
                for segment in segments
                if segment.no_speech_prob <= self.no_speech_prob_cutoff
            ]
            
            text = " ".join(text_segments).strip()
            self._schedule_unload()
            return text
            
        except Exception as e:
            logger.error(f"文字起こしエラー: {e}")
            self._schedule_unload()
            return f"Error: {e}"

    def _schedule_unload(self) -> None:
        """遅延後にモデルアンロードをスケジュールする。"""
        if self.release_memory_delay <= 0:
            return

        with self._lock:
            self._cancel_unload_timer()
            self._unload_timer = threading.Timer(
                self.release_memory_delay,
                self.unload_model
            )
            self._unload_timer.start()
            logger.debug(f"{self.release_memory_delay}秒後にメモリ解放を予約しました。")

    def _cancel_unload_timer(self) -> None:
        """保留中のアンロードタイマーをキャンセルする。"""
        if self._unload_timer:
            self._unload_timer.cancel()
            self._unload_timer = None
