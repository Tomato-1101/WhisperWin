import time
import sys
import threading
from pynput import keyboard
from config import ConfigManager
from audio import AudioRecorder
from transcriber import Transcriber
from input_handler import InputHandler

class SuperWhisperApp:
    def __init__(self):
        print("Initializing SuperWhisper-like App...")
        
        # Load Config
        self.config = ConfigManager()
        
        # Initialize Components
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber(
            model_size=self.config.get("model_size"),
            device=self.config.get("device"),
            language=self.config.get("language")
        )
        self.input_handler = InputHandler()
        
        # Display device info
        device = self.transcriber.device
        print(f"✓ Using device: {device.upper()}")
        
        self.is_recording = False
        self.hotkey = self.config.get("hotkey", "<f2>")
        self.hotkey_mode = self.config.get("hotkey_mode", "toggle")
        
        # For hold mode: track which keys are currently pressed
        self.pressed_keys = set()
        self.required_keys = self.parse_hotkey(self.hotkey)
        
        print(f"Ready! Press '{self.hotkey}' to {'toggle' if self.hotkey_mode == 'toggle' else 'hold for'} recording.")
        
        # Start config monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_config, daemon=True)
        self.monitor_thread.start()

    def parse_hotkey(self, hotkey_str):
        """Parse hotkey string into set of required keys."""
        # Remove angle brackets and split by +
        keys = hotkey_str.replace('<', '').replace('>', '').split('+')
        return set(keys)

    def monitor_config(self):
        """Monitor config file for changes."""
        while self.monitoring:
            time.sleep(1)  # Check every second
            if self.config.reload_if_changed():
                # Config changed, update relevant settings
                new_hotkey = self.config.get("hotkey", "<f2>")
                new_mode = self.config.get("hotkey_mode", "toggle")
                
                if new_hotkey != self.hotkey or new_mode != self.hotkey_mode:
                    self.hotkey = new_hotkey
                    self.hotkey_mode = new_mode
                    self.required_keys = self.parse_hotkey(self.hotkey)
                    print(f"\n✓ Hotkey updated: '{self.hotkey}' ({self.hotkey_mode} mode)")
                    print("Please restart the app to apply hotkey changes.")

    def on_activate(self):
        """Called when hotkey is pressed (toggle mode)."""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_and_transcribe()

    def start_recording(self):
        print("\n[Start Recording]")
        self.is_recording = True
        self.recorder.start_recording()

    def stop_and_transcribe(self):
        print("[Stop Recording]")
        self.is_recording = False
        audio_data = self.recorder.stop_recording()
        
        if len(audio_data) == 0:
            print("No audio recorded.")
            return

        print("Transcribing...")
        text = self.transcriber.transcribe(audio_data)
        
        if text:
            print(f"Result: {text}")
            print("Pasting...")
            self.input_handler.insert_text(text)
        else:
            print("No text detected.")

    def run(self):
        if self.hotkey_mode == 'hold':
            # Hold mode: track key presses to detect combination
            listener = keyboard.Listener(
                on_press=self.handle_key_press,
                on_release=self.handle_key_release
            )
            listener.start()
            listener.join()
        else:
            # Toggle mode: use GlobalHotKeys
            hotkey_map = {
                self.hotkey: self.on_activate
            }

            try:
                with keyboard.GlobalHotKeys(hotkey_map) as h:
                    h.join()
            except Exception as e:
                print(f"Error with hotkey listener: {e}")
                print("Please check your hotkey configuration in settings.yaml")

    def handle_key_press(self, key):
        """Handle key press for hold mode."""
        try:
            # Convert key to normalized string
            key_str = self.normalize_key(key)
            if key_str:
                self.pressed_keys.add(key_str)
                
                # Check if all required keys are now pressed
                if self.required_keys.issubset(self.pressed_keys) and not self.is_recording:
                    self.start_recording()
        except Exception as e:
            pass

    def handle_key_release(self, key):
        """Handle key release for hold mode."""
        try:
            key_str = self.normalize_key(key)
            if key_str and key_str in self.pressed_keys:
                self.pressed_keys.remove(key_str)
                
                # If we were recording and a required key was released, stop
                if self.is_recording and key_str in self.required_keys:
                    self.stop_and_transcribe()
        except Exception as e:
            pass

    def normalize_key(self, key):
        """Convert pynput key to normalized string (lowercase, no brackets)."""
        try:
            # Handle special keys (e.g., Key.ctrl, Key.space)
            if hasattr(key, 'name'):
                name = key.name.lower()
                # Map common variants
                if name == 'ctrl_l' or name == 'ctrl_r':
                    return 'ctrl'
                if name == 'alt_l' or name == 'alt_r':
                    return 'alt'
                if name == 'shift_l' or name == 'shift_r':
                    return 'shift'
                return name
            # Handle character keys
            elif hasattr(key, 'char') and key.char:
                return key.char.lower()
        except:
            pass
        return None

if __name__ == "__main__":
    app = SuperWhisperApp()
    app.run()
