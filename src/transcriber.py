import os
# Disable HuggingFace progress bars to prevent [WinError 6] The handle is invalid on Windows
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import time
import threading
import gc
import torch
from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_size="large-v3", device="cuda", compute_type="float16", language="ja", 
                 release_memory_delay=300, cpu_threads=4, 
                 vad_filter=True, vad_min_silence_duration_ms=500,
                 condition_on_previous_text=False, no_speech_threshold=0.6,
                 log_prob_threshold=-1.0, no_speech_prob_cutoff=0.7, beam_size=5):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.release_memory_delay = release_memory_delay
        self.cpu_threads = cpu_threads
        
        # Advanced settings
        self.vad_filter = vad_filter
        self.vad_min_silence_duration_ms = vad_min_silence_duration_ms
        self.condition_on_previous_text = condition_on_previous_text
        self.no_speech_threshold = no_speech_threshold
        self.log_prob_threshold = log_prob_threshold
        self.no_speech_prob_cutoff = no_speech_prob_cutoff
        self.beam_size = beam_size
        
        self.model = None
        self.unload_timer = None
        self.lock = threading.Lock()

        # Check if CUDA is actually available
        if self.device == "cuda" and not torch.cuda.is_available():
            print("CUDA not available, falling back to CPU.")
            self.device = "cpu"
            self.compute_type = "int8" # Fallback for CPU usually

    def load_model(self):
        """Load the model if not already loaded."""
        with self.lock:
            # If a timer is running to unload, cancel it
            if self.unload_timer:
                self.unload_timer.cancel()
                self.unload_timer = None
            
            if self.model is not None:
                return

            print(f"Loading faster-whisper model '{self.model_size}' on {self.device} ({self.compute_type})...")
            try:
                self.model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type=self.compute_type,
                    cpu_threads=self.cpu_threads
                )
                print("Model loaded successfully.")
            except Exception as e:
                print(f"Error loading model: {e}")
                raise

    def unload_model(self):
        """Unload the model to release VRAM."""
        with self.lock:
            if self.model:
                print("Unloading model to release memory...")
                del self.model
                self.model = None
                gc.collect()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                print("Model unloaded.")

    def schedule_unload(self):
        """Schedule model unload after delay."""
        if self.release_memory_delay <= 0:
            return

        with self.lock:
            if self.unload_timer:
                self.unload_timer.cancel()
            
            self.unload_timer = threading.Timer(self.release_memory_delay, self.unload_model)
            self.unload_timer.start()
            # print(f"Memory release scheduled in {self.release_memory_delay} seconds.")

    def transcribe(self, audio_data):
        """
        Transcribe audio data (numpy array).
        Returns the transcribed text.
        """
        # Ensure model is loaded
        if self.model is None:
            self.load_model()
            
        if len(audio_data) == 0:
            return ""

        # print("Transcribing...") # Removed to avoid duplication with main.py
        try:
            segments, info = self.model.transcribe(
                audio_data, 
                language=self.language if self.language else None,
                beam_size=self.beam_size,
                # VAD filter to detect speech segments
                vad_filter=self.vad_filter,
                vad_parameters=dict(min_silence_duration_ms=self.vad_min_silence_duration_ms),
                # Anti-hallucination settings
                condition_on_previous_text=self.condition_on_previous_text,
                no_speech_threshold=self.no_speech_threshold,
                log_prob_threshold=self.log_prob_threshold,
            )
            
            # faster-whisper returns a generator, so we iterate to get text
            text_segments = []
            for segment in segments:
                # Additional filtering for high no_speech_prob
                if segment.no_speech_prob > self.no_speech_prob_cutoff:
                    continue
                text_segments.append(segment.text)
            
            text = " ".join(text_segments).strip()
            
            # Schedule unload after successful transcription
            self.schedule_unload()
            
            return text
        except Exception as e:
            print(f"Transcription error: {e}")
            # Schedule unload even on error to be safe
            self.schedule_unload()
            return f"Error: {e}"
