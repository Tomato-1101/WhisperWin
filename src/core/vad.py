"""
音声活性検出（VAD）モジュール

Silero VADを使用して音声に発話が含まれるかを検出する。
CUDA対応でGPU高速化が可能。Groqモードでの無音判定に使用される。
"""

import torch
import numpy as np
import numpy.typing as npt

from ..utils.logger import get_logger

logger = get_logger(__name__)


class VadFilter:
    """
    音声活性検出（VAD）フィルター。
    
    Silero VADを使用して、音声データに発話が含まれるかを判定する。
    発話が検出されない場合、API呼び出しをスキップして効率化できる。
    
    Attributes:
        min_silence_duration_ms: 無音と判定する最小継続時間（ミリ秒）
        use_cuda: CUDAを使用するかどうか
        device: 使用デバイス（'cuda' or 'cpu'）
    """
    
    def __init__(
        self,
        min_silence_duration_ms: int = 500,
        use_cuda: bool = True
    ) -> None:
        """
        VADフィルターを初期化する。
        
        Args:
            min_silence_duration_ms: 発話終了と判定する最小無音時間（ミリ秒）
            use_cuda: CUDA使用フラグ（利用可能な場合のみ有効）
        """
        self.min_silence_duration_ms = min_silence_duration_ms
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self._model = None  # 遅延ロード用
        
        # デバイス設定
        self.device = 'cuda' if self.use_cuda else 'cpu'
        logger.info(f"VADフィルター初期化 (デバイス: {self.device})")
        
    def _load_model(self):
        """Silero VADモデルを遅延ロードする。"""
        if self._model is None:
            try:
                from silero_vad import load_silero_vad
                
                # モデルをロード
                self._model = load_silero_vad()
                
                # CUDAデバイスに移動
                if self.use_cuda:
                    self._model = self._model.to(self.device)
                
                logger.info(f"Silero VADモデルをロード ({self.device})")
                
            except Exception as e:
                logger.error(f"Silero VADモデルのロードに失敗: {e}")
                raise
    
    def has_speech(self, audio_data: npt.NDArray[np.float32], sample_rate: int = 16000) -> bool:
        """
        音声データに発話が含まれるかを判定する。
        
        Args:
            audio_data: 音声データ（float32のNumPy配列）
            sample_rate: サンプリングレート（Hz）
            
        Returns:
            発話が検出された場合True、無音の場合False
        """
        if len(audio_data) == 0:
            return False
        
        # モデルをロード（未ロードの場合）
        self._load_model()
            
        try:
            from silero_vad import get_speech_timestamps
            
            # NumPy配列をTensorに変換
            audio_tensor = torch.from_numpy(audio_data)
            if self.use_cuda:
                audio_tensor = audio_tensor.to(self.device)
            
            # 発話区間を検出
            speech_timestamps = get_speech_timestamps(
                audio_tensor,
                self._model,
                sampling_rate=sample_rate,
                min_silence_duration_ms=self.min_silence_duration_ms,
                return_seconds=False
            )
            
            has_speech = len(speech_timestamps) > 0
            logger.debug(f"VAD結果: has_speech={has_speech}, セグメント数={len(speech_timestamps)}")
            return has_speech
            
        except Exception as e:
            logger.error(f"VADエラー: {e}")
            # エラー時は安全側に倒してTrueを返す（文字起こしを実行）
            return True

    def preload_model(self) -> None:
        """
        VADモデルを事前にロードする。
        
        アプリ起動時に呼び出すことで、最初の音声入力時の
        モデルロード遅延を回避できる。
        """
        logger.info("VADモデルをプリロード中...")
        self._load_model()
        logger.info("VADモデルのプリロードが完了しました")

