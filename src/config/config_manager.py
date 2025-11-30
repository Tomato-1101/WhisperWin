"""Configuration management with file watching and hot-reload support."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..utils.logger import get_logger
from .constants import DEFAULT_CONFIG, SETTINGS_FILE_NAME

logger = get_logger(__name__)


class ConfigManager:
    """
    Manages application configuration loading, saving, and monitoring.
    
    Supports hot-reload when the configuration file changes.
    """
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize ConfigManager.
        
        Args:
            config_path: Path to the configuration file. 
                        If None, looks for settings.yaml in project root.
        """
        self.config_path = self._resolve_config_path(config_path)
        self.last_mtime: Optional[float] = None
        self.config: Dict[str, Any] = self._load_config()

    def _resolve_config_path(self, config_path: Optional[str]) -> str:
        """Resolve the configuration file path."""
        if config_path:
            return config_path
            
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_dir = Path(sys.executable).parent
        else:
            # Running as script - look in project root (parent of src)
            base_dir = Path(__file__).parent.parent.parent
            
        return str(base_dir / SETTINGS_FILE_NAME)

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file, merging with defaults.
        
        Returns:
            Configuration dictionary with all keys guaranteed to exist.
        """
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found at {self.config_path}. Using defaults.")
            return DEFAULT_CONFIG.copy()
        
        try:
            self.last_mtime = os.path.getmtime(self.config_path)
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f) or {}
            
            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(loaded_config)
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()

    def reload_if_changed(self) -> bool:
        """
        Reload configuration if file has been modified.
        
        Returns:
            True if config was reloaded, False otherwise.
        """
        if not os.path.exists(self.config_path):
            return False
            
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if self.last_mtime is None or current_mtime > self.last_mtime:
                logger.info("Config file changed, reloading...")
                self.config = self._load_config()
                return True
        except Exception as e:
            logger.error(f"Error checking config: {e}")
            
        return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key.
            default: Default value if key not found.
            
        Returns:
            Configuration value.
        """
        return self.config.get(key, default)

    def save(self, new_config: Dict[str, Any]) -> bool:
        """
        Save configuration to file.
        
        Args:
            new_config: Dictionary containing new configuration values.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Update internal config
            self.config.update(new_config)
            
            # Write to file
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            # Update mtime to prevent reload loop
            self.last_mtime = os.path.getmtime(self.config_path)
            logger.info("Configuration saved successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    # Alias for backward compatibility
    def save_config(self, new_config: Dict[str, Any]) -> bool:
        """Alias for save() method."""
        return self.save(new_config)
