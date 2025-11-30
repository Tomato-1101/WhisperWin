"""Audio recording functionality using sounddevice."""

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
    Handles audio recording using sounddevice.
    
    Provides a simple interface for starting/stopping recordings
    and retrieving audio data as numpy arrays.
    """
    
    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        """
        Initialize AudioRecorder.
        
        Args:
            sample_rate: Sampling rate in Hz.
        """
        self.sample_rate = sample_rate
        self._queue: queue.Queue = queue.Queue()
        self._recording = False
        self._stream: Optional[sd.InputStream] = None

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags
    ) -> None:
        """
        Callback function for sounddevice stream.
        
        Puts incoming audio data into the queue for later retrieval.
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
        self._queue.put(indata.copy())

    def start(self) -> bool:
        """
        Start recording audio.
        
        Returns:
            True if recording started successfully, False otherwise.
        """
        if self._recording:
            logger.info("Already recording.")
            return False
        
        try:
            # Clear queue
            self._clear_queue()
            
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=AUDIO_CHANNELS,
                dtype=AUDIO_DTYPE,
                callback=self._audio_callback
            )
            self._stream.start()
            self._recording = True
            logger.info("Recording started...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._cleanup_stream()
            return False

    def stop(self) -> npt.NDArray[np.float32]:
        """
        Stop recording and return the audio data.
        
        Returns:
            Numpy array containing the recorded audio data.
        """
        if not self._recording:
            return np.array([], dtype=np.float32)

        self._recording = False
        self._cleanup_stream()
        logger.info("Recording stopped.")
        
        return self._collect_audio_data()

    def _clear_queue(self) -> None:
        """Clear the audio queue."""
        with self._queue.mutex:
            self._queue.queue.clear()

    def _cleanup_stream(self) -> None:
        """Clean up the audio stream."""
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
            finally:
                self._stream = None

    def _collect_audio_data(self) -> npt.NDArray[np.float32]:
        """
        Collect all audio data from the queue.
        
        Returns:
            Concatenated audio data as a flat array.
        """
        data_list: List[np.ndarray] = []
        
        while not self._queue.empty():
            data_list.append(self._queue.get())
            
        if not data_list:
            return np.array([], dtype=np.float32)
            
        try:
            audio_data = np.concatenate(data_list, axis=0)
            return audio_data.flatten()
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            return np.array([], dtype=np.float32)

    # Aliases for backward compatibility
    def start_recording(self) -> bool:
        """Alias for start() method."""
        return self.start()

    def stop_recording(self) -> npt.NDArray[np.float32]:
        """Alias for stop() method."""
        return self.stop()
