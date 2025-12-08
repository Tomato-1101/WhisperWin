"""Voice Activity Detection (VAD) using silero-vad package with CUDA support."""

import torch
import numpy as np
import numpy.typing as npt

from ..utils.logger import get_logger

logger = get_logger(__name__)


class VadFilter:
    """
    Filters audio based on Voice Activity Detection.
    
    Uses silero-vad package for CUDA-accelerated inference.
    """
    
    def __init__(
        self,
        min_silence_duration_ms: int = 500,
        use_cuda: bool = True
    ) -> None:
        """
        Initialize VAD filter.
        
        Args:
            min_silence_duration_ms: Minimum silence duration to consider end of speech.
            use_cuda: Whether to use CUDA for VAD inference.
        """
        self.min_silence_duration_ms = min_silence_duration_ms
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self._model = None
        
        # Set device
        self.device = 'cuda' if self.use_cuda else 'cpu'
        logger.info(f"VAD Filter initialized (device: {self.device})")
        
    def _load_model(self):
        """Load the Silero VAD model lazily."""
        if self._model is None:
            try:
                from silero_vad import load_silero_vad
                
                # Load model - silero-vad package handles loading
                self._model = load_silero_vad()
                
                # Move to device if CUDA
                if self.use_cuda:
                    self._model = self._model.to(self.device)
                
                logger.info(f"Silero VAD model loaded on {self.device}")
                
            except Exception as e:
                logger.error(f"Failed to load Silero VAD model: {e}")
                raise
    
    def has_speech(self, audio_data: npt.NDArray[np.float32], sample_rate: int = 16000) -> bool:
        """
        Check if the audio contains speech.
        
        Args:
            audio_data: Audio samples as numpy array (float32).
            sample_rate: Sample rate of the audio.
            
        Returns:
            True if speech is detected, False otherwise.
        """
        if len(audio_data) == 0:
            return False
        
        # Ensure model is loaded
        self._load_model()
            
        try:
            from silero_vad import get_speech_timestamps
            
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_data)
            if self.use_cuda:
                audio_tensor = audio_tensor.to(self.device)
            
            # Get speech timestamps
            speech_timestamps = get_speech_timestamps(
                audio_tensor,
                self._model,
                sampling_rate=sample_rate,
                min_silence_duration_ms=self.min_silence_duration_ms,
                return_seconds=False
            )
            
            has_speech = len(speech_timestamps) > 0
            logger.debug(f"VAD result: has_speech={has_speech}, segments={len(speech_timestamps)}")
            return has_speech
            
        except Exception as e:
            logger.error(f"VAD error: {e}")
            # If VAD fails, default to True (allow transcription) to be safe
            return True
