"""Speech-to-text transcription using faster-whisper."""

import os

# Configure HuggingFace environment before imports
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

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
    Handles audio transcription using faster-whisper.
    
    GPU/CUDA only - requires a CUDA-capable GPU.
    Supports automatic model loading/unloading for memory management.
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
        Initialize Transcriber.
        
        Args:
            model_size: Whisper model size.
            compute_type: Computation precision type.
            language: Language code for transcription.
            release_memory_delay: Seconds before unloading model from VRAM.
            vad_filter: Enable Voice Activity Detection.
            vad_min_silence_duration_ms: Minimum silence duration for VAD.
            condition_on_previous_text: Condition on previous transcription.
            no_speech_threshold: Threshold for no-speech detection.
            log_prob_threshold: Log probability threshold.
            no_speech_prob_cutoff: Cutoff for no-speech probability.
            beam_size: Beam size for decoding.
            model_cache_dir: Directory for model cache.
            
        Raises:
            RuntimeError: If CUDA is not available.
        """
        # Verify CUDA availability
        if not torch.cuda.is_available():
            error_msg = "CUDA is not available. This application requires a CUDA-capable GPU."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Model settings
        self.model_size = model_size
        self.compute_type = compute_type
        self.language = language
        self.model_cache_dir = model_cache_dir or None
        
        # Memory management
        self.release_memory_delay = release_memory_delay
        
        # Transcription settings
        self.vad_filter = vad_filter
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        self.condition_on_previous_text = condition_on_previous_text
        self.no_speech_threshold = no_speech_threshold
        self.log_prob_threshold = log_prob_threshold
        self.no_speech_prob_cutoff = no_speech_prob_cutoff
        self.beam_size = beam_size
        
        # Internal state
        self._model: Optional[WhisperModel] = None
        self._unload_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    @property
    def model(self) -> Optional[WhisperModel]:
        """Get the current model instance."""
        return self._model

    def load_model(self) -> None:
        """Load the model if not already loaded."""
        with self._lock:
            self._cancel_unload_timer()
            
            if self._model is not None:
                return

            logger.info(
                f"Loading faster-whisper model '{self.model_size}' "
                f"on cuda ({self.compute_type})..."
            )
            
            try:
                model_kwargs = {
                    "device": "cuda",
                    "compute_type": self.compute_type,
                }
                
                if self.model_cache_dir:
                    model_kwargs["download_root"] = self.model_cache_dir
                    logger.info(f"Using model cache directory: {self.model_cache_dir}")
                
                self._model = WhisperModel(self.model_size, **model_kwargs)
                logger.info("Model loaded successfully.")
                
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                raise

    def unload_model(self) -> None:
        """Unload the model to release VRAM."""
        with self._lock:
            if self._model:
                logger.info("Unloading model to release memory...")
                del self._model
                self._model = None
                gc.collect()
                torch.cuda.empty_cache()
                logger.info("Model unloaded.")

    def transcribe(self, audio_data: npt.NDArray[np.float32]) -> str:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio samples as numpy array.
            
        Returns:
            Transcribed text.
        """
        if self._model is None:
            self.load_model()
            
        if len(audio_data) == 0:
            return ""

        try:
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
            
            # Collect text from segments, filtering by no_speech probability
            text_segments = [
                segment.text
                for segment in segments
                if segment.no_speech_prob <= self.no_speech_prob_cutoff
            ]
            
            text = " ".join(text_segments).strip()
            self._schedule_unload()
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self._schedule_unload()
            return f"Error: {e}"

    def _schedule_unload(self) -> None:
        """Schedule model unload after delay."""
        if self.release_memory_delay <= 0:
            return

        with self._lock:
            self._cancel_unload_timer()
            self._unload_timer = threading.Timer(
                self.release_memory_delay,
                self.unload_model
            )
            self._unload_timer.start()
            logger.debug(f"Memory release scheduled in {self.release_memory_delay} seconds.")

    def _cancel_unload_timer(self) -> None:
        """Cancel any pending unload timer."""
        if self._unload_timer:
            self._unload_timer.cancel()
            self._unload_timer = None
