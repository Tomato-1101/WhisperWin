import pyperclip
from pynput.keyboard import Controller, Key
import time

class InputHandler:
    def __init__(self):
        self.keyboard = Controller()

    def insert_text(self, text):
        """
        Insert text into the active window.
        Uses clipboard copy + Ctrl+V paste for reliability with Japanese text.
        """
        if not text:
            return

        # Backup current clipboard (optional, but nice)
        # old_clipboard = pyperclip.paste()

        try:
            # Copy to clipboard
            pyperclip.copy(text)
            
            # Small delay to ensure clipboard is ready
            time.sleep(0.1)
            
            # Simulate Ctrl+V
            with self.keyboard.pressed(Key.ctrl):
                self.keyboard.press('v')
                self.keyboard.release('v')
                
            # Restore clipboard (optional - might interfere if paste is slow)
            # time.sleep(0.5)
            # pyperclip.copy(old_clipboard)
            
        except Exception as e:
            print(f"Error inserting text: {e}")
