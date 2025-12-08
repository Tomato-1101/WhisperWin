"""
音声録音モジュール

sounddeviceライブラリを使用してマイクから音声を録音する機能を提供する。
録音データはNumPy配列として返され、Whisperによる文字起こしに使用される。
"""

import queue
from typing import Any, List, Optional

import numpy as np
import numpy.typing as npt
import sounddevice as sd

from ..config.constants import SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_DTYPE
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """
    音声録音を管理するクラス。
    
    sounddeviceを使用して非同期で音声を録音し、
    NumPy配列として取得できる。
    
    Attributes:
        sample_rate: サンプリングレート（Hz）
        is_recording: 録音中かどうか
    """
    
    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        """
        AudioRecorderを初期化する。
        
        Args:
            sample_rate: サンプリングレート（デフォルト: 16000Hz）
        """
        self.sample_rate = sample_rate
        self._queue: queue.Queue = queue.Queue()  # 録音データを一時保存するキュー
        self._recording = False  # 録音状態フラグ
        self._stream: Optional[sd.InputStream] = None  # 音声入力ストリーム

    @property
    def is_recording(self) -> bool:
        """録音中かどうかを返す。"""
        return self._recording

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags
    ) -> None:
        """
        sounddeviceからのコールバック関数。
        
        音声データを受け取るたびに呼び出され、キューに追加する。
        
        Args:
            indata: 受信した音声データ
            frames: フレーム数
            time_info: タイミング情報
            status: ステータスフラグ（エラー時に設定される）
        """
        if status:
            logger.warning(f"音声コールバック ステータス: {status}")
        # データをコピーしてキューに追加（元データは再利用されるため）
        self._queue.put(indata.copy())

    def start(self) -> bool:
        """
        録音を開始する。
        
        Returns:
            成功した場合True、既に録音中の場合False
        """
        if self._recording:
            logger.info("既に録音中です。")
            return False
        
        try:
            # キューをクリア
            self._clear_queue()
            
            # 音声入力ストリームを作成・開始
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=AUDIO_CHANNELS,
                dtype=AUDIO_DTYPE,
                callback=self._audio_callback
            )
            self._stream.start()
            self._recording = True
            logger.info("録音開始...")
            return True
            
        except Exception as e:
            logger.error(f"録音開始に失敗: {e}")
            self._cleanup_stream()
            return False

    def stop(self) -> npt.NDArray[np.float32]:
        """
        録音を停止し、音声データを返す。
        
        Returns:
            録音した音声データ（float32のNumPy配列）
        """
        if not self._recording:
            return np.array([], dtype=np.float32)

        self._recording = False
        self._cleanup_stream()
        logger.info("録音停止。")
        
        return self._collect_audio_data()

    def _clear_queue(self) -> None:
        """キューをクリアする。"""
        with self._queue.mutex:
            self._queue.queue.clear()

    def _cleanup_stream(self) -> None:
        """音声ストリームをクリーンアップする。"""
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"ストリーム停止エラー: {e}")
            finally:
                self._stream = None

    def _collect_audio_data(self) -> npt.NDArray[np.float32]:
        """
        キューから全ての音声データを収集する。
        
        Returns:
            結合された音声データ（1次元配列）
        """
        data_list: List[np.ndarray] = []
        
        # キューから全データを取得
        while not self._queue.empty():
            data_list.append(self._queue.get())
            
        if not data_list:
            return np.array([], dtype=np.float32)
            
        try:
            # 全データを結合して1次元配列に変換
            audio_data = np.concatenate(data_list, axis=0)
            return audio_data.flatten()
        except Exception as e:
            logger.error(f"音声データ処理エラー: {e}")
            return np.array([], dtype=np.float32)

    # 後方互換性のためのエイリアス
    def start_recording(self) -> bool:
        """start()のエイリアス。"""
        return self.start()

    def stop_recording(self) -> npt.NDArray[np.float32]:
        """stop()のエイリアス。"""
        return self.stop()
