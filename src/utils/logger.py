"""Centralized logging configuration for the application."""

import logging
import sys
from typing import Dict, Optional

# Default log format
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Singleton logger instances
_loggers: Dict[str, logging.Logger] = {}
_is_configured: bool = False


def setup_logger(
    log_file: Optional[str] = "app.log",
    level: int = logging.INFO,
    format_string: str = LOG_FORMAT
) -> None:
    """
    Configure the root logger with console and file handlers.
    
    Args:
        log_file: Path to the log file. None disables file logging.
        level: Logging level (default: INFO).
        format_string: Log message format.
    """
    global _is_configured
    
    if _is_configured:
        return
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers
    )
    
    _is_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance by name, with caching.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        Configured logger instance.
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]
