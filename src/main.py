"""Application entry point."""

import sys
import traceback

from dotenv import load_dotenv
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .app import SuperWhisperApp
from .utils.logger import get_logger, setup_logger

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logger(log_file="startup_log.txt")
logger = get_logger(__name__)


def main() -> int:
    """
    Main entry point for the application.
    
    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        # Configure High DPI support
        _configure_high_dpi()
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Keep running for system tray
        
        # Create main controller
        controller = SuperWhisperApp()
        
        # Run event loop
        return app.exec()
        
    except Exception as e:
        _handle_critical_error(e)
        return 1


def _configure_high_dpi() -> None:
    """Configure High DPI display support."""
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)


def _handle_critical_error(error: Exception) -> None:
    """
    Handle critical errors by logging and writing to error file.
    
    Args:
        error: The exception that occurred.
    """
    error_msg = f"Critical Error: {error}"
    logger.critical(error_msg, exc_info=True)
    
    # Write detailed error to file
    with open("error_log.txt", "w", encoding="utf-8") as f:
        traceback.print_exc(file=f)
    
    print(error_msg)


if __name__ == "__main__":
    sys.exit(main())
