"""
音声フォーマット変換ユーティリティ

NumPy配列形式の音声データをWAV/MP3形式に変換する機能を提供する。
Groq/OpenAI APIなどへの送信時に使用される。
MP3形式はWAVより約10倍小さく、転送時間を大幅に短縮できる。
"""

import io
import struct
import subprocess
import tempfile
import os
from typing import Literal

import numpy as np
import numpy.typing as npt

# ffmpegの利用可能性チェック
_ffmpeg_available: bool = False
try:
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        timeout=5
    )
    _ffmpeg_available = result.returncode == 0
except (subprocess.SubprocessError, FileNotFoundError, OSError):
    _ffmpeg_available = False


def numpy_to_mp3_bytes(
    audio_data: npt.NDArray[np.float32],
    sample_rate: int = 16000,
    bitrate: str = "64k"
) -> bytes:
    """
    NumPyのfloat32音声配列をMP3形式のバイト列に変換する。
    
    MP3は音声で約10倍のファイルサイズ削減を実現。
    OpenAI API推奨: 音声では32-64kbpsで十分な品質。
    
    Args:
        audio_data: float32形式の音声データ（-1.0〜1.0の範囲）
        sample_rate: サンプリングレート（Hz）
        bitrate: MP3ビットレート（デフォルト64k、音声には十分）
    
    Returns:
        MP3形式のバイト列
    
    Raises:
        RuntimeError: ffmpegが利用できない場合
    """
    if not _ffmpeg_available:
        raise RuntimeError(
            "ffmpegがインストールされていないか、PATHに存在しません。"
            "WAV形式を使用するか、ffmpegをインストールしてください。"
        )
    
    # float32 [-1.0, 1.0] から int16 [-32768, 32767] に変換
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    # 一時ファイルを使用してffmpegで変換
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
        wav_path = wav_file.name
        # WAVヘッダーを書き込み
        wav_bytes = numpy_to_wav_bytes(audio_data, sample_rate)
        wav_file.write(wav_bytes)
    
    mp3_path = wav_path.replace(".wav", ".mp3")
    
    try:
        # ffmpegでMP3に変換
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", wav_path,
                "-ar", str(sample_rate),
                "-ac", "1",
                "-b:a", bitrate,
                "-f", "mp3",
                mp3_path
            ],
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg変換エラー: {result.stderr.decode()}")
        
        with open(mp3_path, "rb") as f:
            return f.read()
    
    finally:
        # 一時ファイルをクリーンアップ
        if os.path.exists(wav_path):
            os.remove(wav_path)
        if os.path.exists(mp3_path):
            os.remove(mp3_path)


def numpy_to_wav_bytes(
    audio_data: npt.NDArray[np.float32],
    sample_rate: int = 16000,
    channels: int = 1,
    bits_per_sample: int = 16
) -> bytes:
    """
    NumPyのfloat32音声配列をWAV形式のバイト列に変換する。
    
    Args:
        audio_data: float32形式の音声データ（-1.0〜1.0の範囲）
        sample_rate: サンプリングレート（Hz）
        channels: チャンネル数（1=モノラル、2=ステレオ）
        bits_per_sample: ビット深度（16または32）
    
    Returns:
        WAVファイル形式のバイト列
    """
    # float32 [-1.0, 1.0] から int16 [-32768, 32767] に変換
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # WAVヘッダーを構築
    buffer = io.BytesIO()

    # データサイズを計算
    data_size = len(audio_int16) * channels * (bits_per_sample // 8)

    # RIFFヘッダー（ファイル識別子）
    buffer.write(b'RIFF')
    buffer.write(struct.pack('<I', 36 + data_size))  # ファイルサイズ - 8
    buffer.write(b'WAVE')

    # fmtチャンク（フォーマット情報）
    buffer.write(b'fmt ')
    buffer.write(struct.pack('<I', 16))              # fmtチャンクサイズ
    buffer.write(struct.pack('<H', 1))               # PCMフォーマット
    buffer.write(struct.pack('<H', channels))        # チャンネル数
    buffer.write(struct.pack('<I', sample_rate))     # サンプリングレート
    buffer.write(struct.pack('<I', sample_rate * channels * (bits_per_sample // 8)))  # バイトレート
    buffer.write(struct.pack('<H', channels * (bits_per_sample // 8)))  # ブロックサイズ
    buffer.write(struct.pack('<H', bits_per_sample)) # ビット深度

    # dataチャンク（音声データ本体）
    buffer.write(b'data')
    buffer.write(struct.pack('<I', data_size))
    buffer.write(audio_int16.tobytes())

    return buffer.getvalue()


def numpy_to_audio_bytes(
    audio_data: npt.NDArray[np.float32],
    sample_rate: int = 16000,
    format: Literal["mp3", "wav"] = "mp3"
) -> tuple[bytes, str]:
    """
    NumPy音声データを指定形式に変換する。
    
    Args:
        audio_data: float32形式の音声データ
        sample_rate: サンプリングレート（Hz）
        format: 出力形式 ("mp3" または "wav")
    
    Returns:
        (音声バイト列, ファイル拡張子) のタプル
    """
    if format == "mp3" and _ffmpeg_available:
        return numpy_to_mp3_bytes(audio_data, sample_rate), "mp3"
    else:
        # MP3が利用できない場合はWAVにフォールバック
        return numpy_to_wav_bytes(audio_data, sample_rate), "wav"


