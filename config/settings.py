"""
User preferences and application settings manager for LocalStudy.
Saves settings locally to JSON with safe defaults.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from config.constants import (
    DEFAULT_BASE_DIR,
    DEFAULT_PROJECTS_DIR,
    DEFAULT_MODELS_DIR,
    PDF_LAYOUT_2UP
)


class SettingsManager:
    """Manages application settings stored in a local JSON configuration file."""

    DEFAULT_SETTINGS: Dict[str, Any] = {
        "projects_dir": str(DEFAULT_PROJECTS_DIR),
        "models_dir": str(DEFAULT_MODELS_DIR),
        "default_interval_seconds": 30,
        "default_pdf_layout": PDF_LAYOUT_2UP,
        "default_whisper_model": "base",
        "default_language": "en",
        "cpu_threads": 4,
        "theme": "dark",
        "show_timestamp_overlay": False,
        "show_title_overlay": False,
        "overlay_font_size": 22,
        "pdf_show_timestamp": True,
        "pdf_time_only": True,
        "pdf_cover_name_only": True,
        "screenshot_quality": 85,
        "auto_cleanup_wav": True,
        "hardware_acceleration": "auto"
    }

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            self.config_dir = DEFAULT_BASE_DIR
            self.config_path = self.config_dir / "settings.json"
        else:
            self.config_path = Path(config_path)
            self.config_dir = self.config_path.parent

        self._settings = dict(self.DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        """Loads settings from file or creates default configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._settings.update(loaded)
            except Exception as e:
                print(f"Warning: Failed to parse settings from {self.config_path}: {e}")
        else:
            self.save()

    def save(self) -> None:
        """Persists current settings to the JSON configuration file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to save settings to {self.config_path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save()

    def get_all(self) -> Dict[str, Any]:
        return dict(self._settings)


# Global singleton instance
settings = SettingsManager()
