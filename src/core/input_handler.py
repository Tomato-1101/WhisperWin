"""Text input handling via clipboard and keyboard simulation."""

import time

import pyperclip
from pynput.keyboard import Controller, Key

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Clipboard paste delay (seconds)
PASTE_DELAY: float = 0.1


class InputHandler:
    """
    Handles text input simulation.
    
    Uses clipboard copy + Ctrl+V paste for reliable text insertion,
    especially for non-ASCII characters like Japanese text.
    """
    
    def __init__(self) -> None:
        """Initialize InputHandler with keyboard controller."""
        self._keyboard = Controller()

    def insert_text(self, text: str) -> bool:
        """
        Insert text into the active window.
        
        Uses clipboard copy + Ctrl+V paste for reliability with
        multibyte characters (Japanese, Chinese, etc.).
        
        Args:
            text: Text to insert.
            
        Returns:
            True if successful, False otherwise.
        """
        if not text:
            return False

        try:
            # Copy to clipboard
            pyperclip.copy(text)
            
            # Small delay to ensure clipboard is ready
            time.sleep(PASTE_DELAY)
            
            # Simulate Ctrl+V
            with self._keyboard.pressed(Key.ctrl):
                self._keyboard.press('v')
                self._keyboard.release('v')
            
            logger.debug(f"Inserted text: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting text: {e}")
            return False

    def type_text(self, text: str) -> bool:
        """
        Type text character by character.
        
        Note: This method is slower and less reliable with non-ASCII text.
        Prefer insert_text() for most use cases.
        
        Args:
            text: Text to type.
            
        Returns:
            True if successful, False otherwise.
        """
        if not text:
            return False
            
        try:
            self._keyboard.type(text)
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
