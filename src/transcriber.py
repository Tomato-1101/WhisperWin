import whisper
import torch
import numpy as np

class Transcriber:
    def __init__(self, model_size="base", device="cuda", language="ja"):
        self.model_size = model_size
        self.device = device
        self.language = language
        self.model = None
        
        # Check if CUDA is actually available
        if self.device == "cuda" and not torch.cuda.is_available():
            print("CUDA not available, falling back to CPU.")
            self.device = "cpu"
            
        self.load_model()

    def load_model(self):
        print(f"Loading Whisper model '{self.model_size}' on {self.device}...")
        try:
            self.model = whisper.load_model(self.model_size, device=self.device)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    def transcribe(self, audio_data):
        """
        Transcribe audio data (numpy array).
        Returns the transcribed text.
        """
        if self.model is None:
            return "Error: Model not loaded."
            
        if len(audio_data) == 0:
            return ""

        # Normalize audio to float32 range [-1, 1] if not already
        # sounddevice returns float32, so usually fine.
        
        print("Transcribing...")
        try:
            result = self.model.transcribe(
                audio_data, 
                language=self.language if self.language else None,
                fp16=(self.device == "cuda")
            )
            text = result["text"].strip()
            return text
        except Exception as e:
            print(f"Transcription error: {e}")
            return f"Error: {e}"
