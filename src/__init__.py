"""
SuperWhisper - Speech-to-text application using faster-whisper.

A local, privacy-focused speech-to-text application with GPU acceleration.
"""

__version__ = "1.0.0"
__author__ = "SuperWhisper Team"

from .app import SuperWhisperApp
from .main import main

__all__ = ["SuperWhisperApp", "main", "__version__"]
