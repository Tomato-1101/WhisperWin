"""
音声録音モジュール

sounddeviceライブラリを使用してマイクから音声を録音する機能を提供する。
録音データはNumPy配列として返され、Whisperによる文字起こしに使用される。
"""

import queue
from typing import Any, Dict, List, Optional, Union

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
    リアルタイムの音声レベル通知機能を提供。
    
    Attributes:
        sample_rate: サンプリングレート（Hz）
        is_recording: 録音中かどうか
    """
    
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        input_device: Optional[Union[int, str]] = "default"
    ) -> None:
        """
        AudioRecorderを初期化する。
        
        Args:
            sample_rate: サンプリングレート（デフォルト: 16000Hz）
            input_device: 入力デバイス（"default" / デバイスID / デバイス名）
        """
        self.sample_rate = sample_rate
        self._queue: queue.Queue = queue.Queue()  # 録音データを一時保存するキュー
        self._recording = False  # 録音状態フラグ
        self._stream: Optional[sd.InputStream] = None  # 音声入力ストリーム
        self._level_callback: Optional[callable] = None  # 音声レベルコールバック
        self._level_threshold = 0.02  # 音声検出のしきい値
        self._input_device: Optional[Union[int, str]] = None
        self.set_input_device(input_device)

    @staticmethod
    def normalize_device_setting(device: Any) -> Optional[Union[int, str]]:
        """
        設定値をsounddeviceで扱える入力デバイス形式に正規化する。

        Returns:
            None: システムデフォルトを使用
            int/str: sounddeviceのdevice引数として使用
        """
        if device is None:
            return None

        if isinstance(device, str):
            value = device.strip()
            if not value or value.lower() == "default":
                return None
            if value.isdigit():
                return int(value)
            return value

        if isinstance(device, (int, np.integer)):
            return int(device)

        return None

    @staticmethod
    def list_input_devices() -> List[Dict[str, Any]]:
        """
        利用可能な入力デバイス一覧を取得する。
        """
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
        except Exception as e:
            logger.warning(f"入力デバイス一覧の取得に失敗: {e}")
            return []

        results: List[Dict[str, Any]] = []
        for index, device in enumerate(devices):
            max_input_channels = int(device.get("max_input_channels", 0))
            if max_input_channels <= 0:
                continue

            name = str(device.get("name", f"Input {index}")).strip() or f"Input {index}"
            hostapi_name = ""
            hostapi_index = device.get("hostapi")
            if isinstance(hostapi_index, int) and 0 <= hostapi_index < len(hostapis):
                hostapi_name = str(hostapis[hostapi_index].get("name", "")).strip()

            label = f"{name} ({hostapi_name})" if hostapi_name else name
            results.append({
                "id": index,
                "name": name,
                "label": label,
                "max_input_channels": max_input_channels,
            })

        return results

    def set_input_device(self, device: Any) -> None:
        """
        使用する入力デバイス設定を更新する。
        """
        normalized = self.normalize_device_setting(device)
        self._input_device = normalized

        device_label = "default" if normalized is None else str(normalized)
        logger.info(f"入力デバイス設定: {device_label}")

        if self._recording:
            logger.info("録音中のため、入力デバイス変更は次回録音開始時に適用されます。")

    @property
    def input_device(self) -> Optional[Union[int, str]]:
        """現在の入力デバイス設定を返す。"""
        return self._input_device

    def set_level_callback(self, callback: callable) -> None:
        """
        音声レベルコールバックを設定する。
        
        Args:
            callback: 音声レベル（0.0-1.0）と音声検出フラグを受け取るコールバック
                     callback(level: float, has_voice: bool)
        """
        self._level_callback = callback

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
        音声レベルを計算してコールバックに通知する。
        
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
        
        # 音声レベルを計算してコールバックに通知
        if self._level_callback:
            # RMSで音声レベルを計算
            level = float(np.sqrt(np.mean(indata ** 2)))
            # 正規化（0.0-1.0）- 最大値を0.3程度と仮定
            normalized_level = min(1.0, level / 0.3)
            # しきい値を超えたら音声ありと判定
            has_voice = level > self._level_threshold
            self._level_callback(normalized_level, has_voice)

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

            stream_kwargs = {
                "samplerate": self.sample_rate,
                "channels": AUDIO_CHANNELS,
                "dtype": AUDIO_DTYPE,
                "callback": self._audio_callback,
            }
            if self._input_device is not None:
                stream_kwargs["device"] = self._input_device

            # 音声入力ストリームを作成・開始
            try:
                self._stream = sd.InputStream(**stream_kwargs)
            except Exception as e:
                if self._input_device is None:
                    raise

                logger.warning(
                    f"指定入力デバイス({self._input_device})で録音開始に失敗。"
                    f"デフォルトデバイスへフォールバックします: {e}"
                )
                stream_kwargs.pop("device", None)
                self._stream = sd.InputStream(**stream_kwargs)

            self._stream.start()
            self._recording = True
            device_label = "default" if self._input_device is None else str(self._input_device)
            logger.info(f"録音開始... (input_device={device_label})")
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
