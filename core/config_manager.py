"""
ConfigManager Singleton - Centralized application settings management.

Provides thread-safe access to application configuration with automatic
persistence to JSON file. Supports dot-notation for nested keys.

Example:
    config = ConfigManager.get_instance()
    device_id = config.get("audio.device_id", default=None)
    config.set("audio.master_volume", 0.8)
"""

import json
from pathlib import Path
from typing import Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Singleton for managing application settings."""

    _instance: Optional['ConfigManager'] = None

    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize ConfigManager (singleton).

        Args:
            config_path: Path to settings JSON file

        Raises:
            RuntimeError: If instance already exists
        """
        if ConfigManager._instance is not None:
            raise RuntimeError(
                "ConfigManager is a singleton. Use ConfigManager.get_instance() instead."
            )

        self.config_path = Path(config_path)
        self.settings = self._load_settings()
        logger.info(f"📋 ConfigManager initialized: {self.config_path}")

    @classmethod
    def get_instance(cls, config_path: str = "config/settings.json") -> 'ConfigManager':
        """
        Get or create the singleton instance.

        Args:
            config_path: Path to settings JSON file (only used on first call)

        Returns:
            ConfigManager singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing only)."""
        cls._instance = None

    def _load_settings(self) -> dict:
        """
        Load settings from JSON file or return defaults.

        Returns:
            Settings dictionary
        """
        if not self.config_path.exists():
            logger.warning(f"⚠️  Settings file not found: {self.config_path}")
            logger.info("📋 Creating default settings...")
            return self._get_defaults()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            logger.debug(f"✅ Loaded settings from {self.config_path}")
            return settings
        except Exception as e:
            logger.error(f"❌ Failed to load settings: {e}")
            logger.info("📋 Using default settings...")
            return self._get_defaults()

    def _get_defaults(self) -> dict:
        """
        Get default settings structure.

        Returns:
            Dictionary with default configuration
        """
        return {
            "audio": {
                "device_id": None,
                "blocksize": 512,
                "sample_rate": None,  # Auto-detect
                "master_volume": 0.9,
                "enable_latency_monitor": True,
                "show_latency_monitor": True,
                "audio_profile": "balanced"
            },
            "ui": {
                "theme": "deep_tech_blue",
                "window_geometry": None,
                "window_state": None,
                "last_song": None
            },
            "paths": {
                "library_root": "library/multis",
                "loops_root": "library/loops",
                "assets_root": "assets",
                "logs_root": "logs"
            },
            "remote": {
                "enabled": False,
                "port": 8080,
                "host": "0.0.0.0"
            },
            "playback": {
                "loop_enabled": False,
                "auto_stop_enabled": True,
                "gc_policy": "disable_during_playback"  # or "normal"
            },
            "video": {
                "engine": "auto",  # "mpv" | "vlc" | "auto" - Auto: MPV-first, fallback to VLC
                "mode": None,  # "full" | "loop" | "static" | "none" (None = use recommended)
                "loop_video_path": "assets/loops/default.mp4",
                "recommended_mode": None,  # Set at first run based on hardware detection
                "show_engine_badge": True  # Show engine name badge in video window
            }
        }

    @staticmethod
    def detect_recommended_video_mode() -> str:
        """
        Detect recommended video mode based on hardware capabilities.

        Returns:
            Recommended mode: "full" | "loop" | "static" | "none"

        Detection criteria:
            - CPU < 2013 or RAM < 6GB → "static" (avoid video decoding)
            - Otherwise → "full" (full video with sync)
        """
        try:
            from core.audio_profiles import get_profile_manager

            profile_manager = get_profile_manager()
            hw_specs = profile_manager._detect_hardware_specs()

            cpu_year = hw_specs.get('cpu_year', 2018)
            ram_gb = hw_specs.get('ram_gb', 8)

            # Legacy hardware detection
            if cpu_year < 2013 or ram_gb < 6:
                logger.info(
                    f"🎬 Recommended video mode: 'static' "
                    f"(CPU ~{cpu_year}, {ram_gb}GB RAM - legacy hardware)"
                )
                return "static"
            else:
                logger.info(
                    f"🎬 Recommended video mode: 'full' "
                    f"(CPU ~{cpu_year}, {ram_gb}GB RAM - modern hardware)"
                )
                return "full"

        except Exception as e:
            logger.warning(f"⚠️  Failed to detect hardware for video mode: {e}")
            logger.info("🎬 Defaulting to 'full' video mode")
            return "full"

    def save(self) -> bool:
        """
        Persist settings to disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 Settings saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save settings: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get setting by dot-notation path.

        Args:
            key_path: Path to setting (e.g., "audio.device_id", "ui.theme")
            default: Default value if key not found

        Returns:
            Setting value or default

        Example:
            >>> config = ConfigManager.get_instance()
            >>> device_id = config.get("audio.device_id", default=None)
            >>> theme = config.get("ui.theme")
        """
        keys = key_path.split('.')
        value = self.settings

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.debug(f"⚠️  Setting '{key_path}' not found, using default")
                return default

        return value

    def set(self, key_path: str, value: Any) -> bool:
        """
        Set setting by dot-notation path and persist.

        Args:
            key_path: Path to setting (e.g., "audio.master_volume")
            value: New value to set

        Returns:
            True if successful, False otherwise

        Example:
            >>> config = ConfigManager.get_instance()
            >>> config.set("audio.master_volume", 0.8)
            >>> config.set("ui.theme", "dark_mode")
        """
        try:
            keys = key_path.split('.')
            target = self.settings

            # Navigate/create nested dictionaries
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                elif not isinstance(target[key], dict):
                    logger.error(
                        f"❌ Cannot set '{key_path}': '{key}' is not a dictionary"
                    )
                    return False
                target = target[key]

            # Set the final value
            target[keys[-1]] = value
            logger.debug(f"⚙️  Set {key_path} = {value}")

            # Persist to disk
            return self.save()

        except Exception as e:
            logger.error(f"❌ Failed to set '{key_path}': {e}")
            return False

    def get_all(self) -> dict:
        """
        Get all settings (deep copy for safety).

        Returns:
            Complete settings dictionary
        """
        import copy
        return copy.deepcopy(self.settings)

    def reset_to_defaults(self) -> bool:
        """
        Reset all settings to defaults and persist.

        Returns:
            True if successful
        """
        self.settings = self._get_defaults()
        logger.info("🔄 Settings reset to defaults")
        return self.save()

    def merge_settings(self, new_settings: dict) -> bool:
        """
        Deep merge new settings into current settings.

        Args:
            new_settings: Dictionary with settings to merge

        Returns:
            True if successful

        Example:
            >>> config.merge_settings({"audio": {"master_volume": 0.8}})
        """
        try:
            def deep_merge(base: dict, updates: dict):
                for key, value in updates.items():
                    if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value

            deep_merge(self.settings, new_settings)
            logger.debug(f"🔀 Merged settings")
            return self.save()

        except Exception as e:
            logger.error(f"❌ Failed to merge settings: {e}")
            return False

    def __repr__(self) -> str:
        """String representation."""
        return f"<ConfigManager path={self.config_path}>"
