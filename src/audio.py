import sounddevice as sd
import numpy as np
import queue

class AudioRecorder:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.q = queue.Queue()
        self.recording = False
        self.stream = None

    def callback(self, indata, frames, time, status):
        """Callback function for sounddevice stream."""
        if status:
            print(status)
        self.q.put(indata.copy())

    def start_recording(self):
        """Start recording audio."""
        if self.recording:
            return
        
        self.recording = True
        # Clear queue
        with self.q.mutex:
            self.q.queue.clear()
            
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=self.callback
        )
        self.stream.start()
        print("Recording started...")

    def stop_recording(self):
        """Stop recording and return the audio data."""
        if not self.recording:
            return np.array([])

        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        print("Recording stopped.")
        
        # Collect all data from queue
        data_list = []
        while not self.q.empty():
            data_list.append(self.q.get())
            
        if not data_list:
            return np.array([])
            
        # Concatenate and flatten
        audio_data = np.concatenate(data_list, axis=0)
        return audio_data.flatten()
