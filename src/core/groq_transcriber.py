"""Cloud-based transcription using Groq API."""

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

# Lazy import Groq SDK (may not be installed)
_groq_available: bool = False
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    Groq = None  # type: ignore
    logger.warning("Groq SDK not installed. Install with: pip install groq")


class GroqTranscriber:
    """
    Cloud-based transcription using Groq API.

    Features:
    - Ultra-fast transcription (up to 300x real-time)
    - No local GPU required
    - Supports whisper-large-v3-turbo and other Whisper models

    Note:
        Requires GROQ_API_KEY environment variable to be set.
    """

    # Groq-supported Whisper models
    AVAILABLE_MODELS = [
        "whisper-large-v3-turbo",   # Recommended: fastest
        "whisper-large-v3",          # High accuracy
        "distil-whisper-large-v3-en" # English-optimized
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
        Initialize GroqTranscriber.

        Args:
            model: Groq Whisper model name.
            language: Language code (e.g., 'ja', 'en').
            temperature: Temperature for sampling (0.0 = deterministic).
            sample_rate: Audio sample rate in Hz.
            vad_filter: Whether to enable VAD pre-filtering.
            vad_min_silence_duration_ms: Minimum silence duration for VAD.
        """
        self.model = model
        self.language = language
        self.temperature = temperature
        self.sample_rate = sample_rate
        self._client: Optional[Groq] = None
        
        # VAD settings
        self.vad_enabled = vad_filter
        self._vad_filter: Optional[VadFilter] = None
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        if vad_filter:
            self._vad_filter = VadFilter(
                min_silence_duration_ms=vad_min_silence_duration_ms,
                use_cuda=True  # Use CUDA for VAD
            )

        # Validate model
        if model not in self.AVAILABLE_MODELS:
            logger.warning(
                f"Model '{model}' may not be available. "
                f"Recommended models: {', '.join(self.AVAILABLE_MODELS)}"
            )

    def is_available(self) -> bool:
        """
        Check if Groq API is available.

        Returns:
            True if Groq SDK is installed and API key is set, False otherwise.
        """
        if not _groq_available:
            return False

        api_key = os.environ.get("GROQ_API_KEY")
        return bool(api_key)

    def _get_client(self) -> Groq:
        """
        Get or create Groq client.

        Returns:
            Initialized Groq client.

        Raises:
            RuntimeError: If API key is not configured.
        """
        if self._client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "GROQ_API_KEY environment variable not set. "
                    "Set it with: export GROQ_API_KEY='gsk_...'"
                )
            self._client = Groq(api_key=api_key)
        return self._client

    def transcribe(self, audio_data: npt.NDArray[np.float32]) -> str:
        """
        Transcribe audio using Groq API.

        Args:
            audio_data: Audio samples as numpy array (float32, mono).

        Returns:
            Transcribed text, or error message starting with "Error:".
        """
        if len(audio_data) == 0:
            return ""

        # VAD Filter - skip API call if no speech detected
        if self.vad_enabled and self._vad_filter:
            if not self._vad_filter.has_speech(audio_data, self.sample_rate):
                logger.debug("VAD: No speech detected, skipping Groq API call.")
                return ""

        if not self.is_available():
            if not _groq_available:
                return "Error: Groq SDK not installed. Run: pip install groq"
            return "Error: GROQ_API_KEY environment variable not set"

        try:
            # Convert NumPy array to WAV bytes
            wav_bytes = numpy_to_wav_bytes(audio_data, self.sample_rate)

            # Create file-like object
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"  # Groq uses filename to detect format

            # Call Groq API
            client = self._get_client()
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=self.language if self.language else None,
                temperature=self.temperature,
                response_format="text"
            )

            # Extract text
            text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
            logger.debug(f"Groq transcription: {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"Groq transcription error: {e}")
            return f"Error: {e}"

    def load_model(self) -> None:
        """
        Pre-initialize the Groq client (optional).

        For Groq API, this is a no-op since there's no model loading.
        """
        if self.is_available():
            try:
                self._get_client()
                logger.debug("Groq client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")

    def unload_model(self) -> None:
        """
        Clear the client reference.

        For Groq API, this simply clears the cached client instance.
        """
        self._client = None
        logger.debug("Groq client reference cleared")
