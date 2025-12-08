"""Audio format conversion utilities."""

import io
import struct

import numpy as np
import numpy.typing as npt


def numpy_to_wav_bytes(
    audio_data: npt.NDArray[np.float32],
    sample_rate: int = 16000,
    channels: int = 1,
    bits_per_sample: int = 16
) -> bytes:
    """
    Convert numpy float32 audio array to WAV format bytes.

    Args:
        audio_data: Audio samples as float32 (-1.0 to 1.0).
        sample_rate: Sample rate in Hz.
        channels: Number of audio channels (1 for mono, 2 for stereo).
        bits_per_sample: Bit depth (16 or 32).

    Returns:
        WAV file as bytes.
    """
    # float32 [-1.0, 1.0] -> int16 [-32768, 32767]
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # Build WAV header
    buffer = io.BytesIO()

    # Calculate data size
    data_size = len(audio_int16) * channels * (bits_per_sample // 8)

    # RIFF header
    buffer.write(b'RIFF')
    buffer.write(struct.pack('<I', 36 + data_size))  # File size - 8
    buffer.write(b'WAVE')

    # fmt chunk
    buffer.write(b'fmt ')
    buffer.write(struct.pack('<I', 16))              # fmt chunk size
    buffer.write(struct.pack('<H', 1))               # PCM format
    buffer.write(struct.pack('<H', channels))        # Number of channels
    buffer.write(struct.pack('<I', sample_rate))     # Sample rate
    buffer.write(struct.pack('<I', sample_rate * channels * (bits_per_sample // 8)))  # Byte rate
    buffer.write(struct.pack('<H', channels * (bits_per_sample // 8)))  # Block size
    buffer.write(struct.pack('<H', bits_per_sample)) # Bit depth

    # data chunk
    buffer.write(b'data')
    buffer.write(struct.pack('<I', data_size))
    buffer.write(audio_int16.tobytes())

    return buffer.getvalue()
