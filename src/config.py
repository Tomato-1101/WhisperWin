import yaml
import os

class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            # Look for settings.yaml in parent directory (project root)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "..", "settings.yaml")
        self.config_path = config_path
        self.last_mtime = None
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            # Return defaults if file doesn't exist
            return {
                "hotkey": "<f2>",
                "hotkey_mode": "toggle",
                "model_size": "base",
                "device": "cuda",
                "language": "ja"
            }
        
        try:
            # Update last modified time
            self.last_mtime = os.path.getmtime(self.config_path)
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def reload_if_changed(self):
        """Reload config if file has been modified."""
        if not os.path.exists(self.config_path):
            return False
            
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if self.last_mtime is None or current_mtime > self.last_mtime:
                print("\n[Config file changed, reloading...]")
                self.config = self.load_config()
                return True
        except Exception as e:
            print(f"Error checking config: {e}")
        return False

    def get(self, key, default=None):
        return self.config.get(key, default)
