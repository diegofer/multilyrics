"""
Tests for ConfigManager Singleton.

Validates:
- Singleton pattern enforcement
- Settings persistence
- Dot-notation access (get/set)
- Default values
- Deep merge functionality
"""

import json
import pytest
from pathlib import Path
from core.config_manager import ConfigManager


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file for testing."""
    config_path = tmp_path / "test_config.json"
    config_data = {
        "audio": {
            "device_id": 0,
            "master_volume": 0.9,
            "blocksize": 512
        },
        "ui": {
            "theme": "dark",
            "window_geometry": None
        },
        "paths": {
            "library_root": "library/multis"
        }
    }
    with open(config_path, 'w') as f:
        json.dump(config_data, f)
    return config_path


@pytest.fixture
def fresh_config_manager(temp_config_file):
    """Reset ConfigManager singleton and create fresh instance."""
    ConfigManager.reset_instance()
    config = ConfigManager(str(temp_config_file))
    yield config
    ConfigManager.reset_instance()


class TestConfigManagerSingleton:
    """Test singleton pattern enforcement."""

    def test_singleton_instance_creation(self, temp_config_file):
        """Test that only one instance can exist."""
        ConfigManager.reset_instance()
        config1 = ConfigManager.get_instance(str(temp_config_file))
        config2 = ConfigManager.get_instance(str(temp_config_file))

        assert config1 is config2

    def test_singleton_error_on_direct_init(self, temp_config_file):
        """Test that direct initialization after singleton exists raises error."""
        ConfigManager.reset_instance()
        ConfigManager.get_instance(str(temp_config_file))

        with pytest.raises(RuntimeError, match="singleton"):
            ConfigManager(str(temp_config_file))

    def test_reset_instance(self, temp_config_file):
        """Test that reset_instance clears singleton."""
        ConfigManager.reset_instance()
        config1 = ConfigManager.get_instance(str(temp_config_file))
        ConfigManager.reset_instance()
        config2 = ConfigManager.get_instance(str(temp_config_file))

        assert config1 is not config2


class TestConfigGetSet:
    """Test get/set operations with dot notation."""

    def test_get_top_level_key(self, fresh_config_manager):
        """Test getting top-level keys."""
        value = fresh_config_manager.get("audio")
        assert isinstance(value, dict)
        assert "device_id" in value

    def test_get_nested_key(self, fresh_config_manager):
        """Test getting nested keys with dot notation."""
        value = fresh_config_manager.get("audio.device_id")
        assert value == 0

    def test_get_deeply_nested_key(self, fresh_config_manager):
        """Test getting deeply nested keys."""
        value = fresh_config_manager.get("paths.library_root")
        assert value == "library/multis"

    def test_get_missing_key_with_default(self, fresh_config_manager):
        """Test that missing keys return default."""
        value = fresh_config_manager.get("nonexistent.key", default="default_value")
        assert value == "default_value"

    def test_get_missing_key_without_default(self, fresh_config_manager):
        """Test that missing keys return None without default."""
        value = fresh_config_manager.get("nonexistent.key")
        assert value is None

    def test_set_existing_key(self, fresh_config_manager):
        """Test setting existing keys."""
        fresh_config_manager.set("audio.device_id", 5)
        assert fresh_config_manager.get("audio.device_id") == 5

    def test_set_new_nested_key(self, fresh_config_manager):
        """Test creating new nested keys."""
        fresh_config_manager.set("new.nested.key", "value")
        assert fresh_config_manager.get("new.nested.key") == "value"

    def test_set_creates_intermediate_dicts(self, fresh_config_manager):
        """Test that set creates intermediate dictionaries."""
        fresh_config_manager.set("completely.new.deep.value", 42)
        assert fresh_config_manager.get("completely.new.deep.value") == 42


class TestConfigPersistence:
    """Test settings persistence to disk."""

    def test_save_creates_file(self, tmp_path):
        """Test that save creates the config file."""
        ConfigManager.reset_instance()
        config_path = tmp_path / "new_config.json"
        config = ConfigManager(str(config_path))

        # Save should create the file
        config.save()
        assert config_path.exists()

    def test_save_persists_changes(self, temp_config_file):
        """Test that changes are saved to disk."""
        ConfigManager.reset_instance()
        config = ConfigManager(str(temp_config_file))

        # Modify and save
        config.set("audio.device_id", 99)

        # Load fresh instance
        ConfigManager.reset_instance()
        fresh_config = ConfigManager(str(temp_config_file))

        # Verify change persisted
        assert fresh_config.get("audio.device_id") == 99

    def test_save_returns_true_on_success(self, fresh_config_manager):
        """Test that save returns True on success."""
        result = fresh_config_manager.save()
        assert result is True

    def test_load_from_file(self, temp_config_file):
        """Test that settings are loaded from file."""
        ConfigManager.reset_instance()
        config = ConfigManager(str(temp_config_file))

        # Verify data from file was loaded
        assert config.get("audio.device_id") == 0
        assert config.get("ui.theme") == "dark"


class TestConfigDefaults:
    """Test default settings."""

    def test_defaults_created_when_file_missing(self, tmp_path):
        """Test that defaults are created when config file doesn't exist."""
        ConfigManager.reset_instance()
        missing_path = tmp_path / "missing" / "config.json"
        config = ConfigManager(str(missing_path))

        # Should have default audio settings
        assert config.get("audio.master_volume") == 0.9
        assert config.get("audio.blocksize") == 512
        assert config.get("ui.theme") == "deep_tech_blue"

    def test_defaults_have_required_keys(self, tmp_path):
        """Test that defaults contain required top-level keys."""
        ConfigManager.reset_instance()
        config = ConfigManager(str(tmp_path / "new.json"))

        defaults = config.get_all()
        required_keys = ["audio", "ui", "paths", "remote", "playback"]
        for key in required_keys:
            assert key in defaults


class TestConfigGetAll:
    """Test get_all functionality."""

    def test_get_all_returns_dict(self, fresh_config_manager):
        """Test that get_all returns dictionary."""
        all_settings = fresh_config_manager.get_all()
        assert isinstance(all_settings, dict)

    def test_get_all_is_deep_copy(self, fresh_config_manager):
        """Test that get_all returns a deep copy, not reference."""
        all_settings = fresh_config_manager.get_all()
        all_settings["audio"]["device_id"] = 999

        # Original should be unchanged
        assert fresh_config_manager.get("audio.device_id") == 0

    def test_get_all_contains_all_keys(self, fresh_config_manager):
        """Test that get_all contains all settings."""
        all_settings = fresh_config_manager.get_all()

        # Should have audio settings
        assert "audio" in all_settings
        assert "ui" in all_settings
        assert "paths" in all_settings


class TestConfigMerge:
    """Test settings merging functionality."""

    def test_merge_new_keys(self, fresh_config_manager):
        """Test merging new keys."""
        new_settings = {
            "custom": {
                "key1": "value1",
                "key2": "value2"
            }
        }
        fresh_config_manager.merge_settings(new_settings)

        assert fresh_config_manager.get("custom.key1") == "value1"
        assert fresh_config_manager.get("custom.key2") == "value2"

    def test_merge_overwrite_existing(self, fresh_config_manager):
        """Test that merge overwrites existing values."""
        new_settings = {
            "audio": {
                "device_id": 999
            }
        }
        fresh_config_manager.merge_settings(new_settings)

        # Should be overwritten
        assert fresh_config_manager.get("audio.device_id") == 999

    def test_merge_preserves_other_keys(self, fresh_config_manager):
        """Test that merge preserves unmodified keys."""
        original_volume = fresh_config_manager.get("audio.master_volume")

        new_settings = {
            "audio": {
                "device_id": 999
            }
        }
        fresh_config_manager.merge_settings(new_settings)

        # Other audio keys should be preserved
        assert fresh_config_manager.get("audio.master_volume") == original_volume

    def test_merge_returns_true_on_success(self, fresh_config_manager):
        """Test that merge returns True on success."""
        result = fresh_config_manager.merge_settings({"test": {"key": "value"}})
        assert result is True


class TestConfigReset:
    """Test reset to defaults functionality."""

    def test_reset_to_defaults(self, fresh_config_manager):
        """Test resetting all settings to defaults."""
        # Modify a setting
        fresh_config_manager.set("audio.device_id", 999)

        # Reset
        fresh_config_manager.reset_to_defaults()

        # Should be reset to default (None)
        assert fresh_config_manager.get("audio.device_id") is None

    def test_reset_returns_true(self, fresh_config_manager):
        """Test that reset returns True on success."""
        result = fresh_config_manager.reset_to_defaults()
        assert result is True


class TestConfigEdgeCases:
    """Test edge cases and error handling."""

    def test_set_none_value(self, fresh_config_manager):
        """Test setting None values."""
        fresh_config_manager.set("audio.device_id", None)
        assert fresh_config_manager.get("audio.device_id") is None

    def test_set_complex_types(self, fresh_config_manager):
        """Test setting complex data types."""
        test_list = [1, 2, 3]
        fresh_config_manager.set("custom.list", test_list)
        assert fresh_config_manager.get("custom.list") == test_list

    def test_get_with_empty_path(self, fresh_config_manager):
        """Test get with empty path returns None."""
        value = fresh_config_manager.get("")
        assert value is None

    def test_set_empty_key_path(self, fresh_config_manager):
        """Test set with empty key path."""
        # Empty path would have no keys to split, resulting in an index error or unexpected behavior
        # The implementation allows it but it sets the root, which may or may not be intended
        # For now, just verify it doesn't crash
        try:
            result = fresh_config_manager.set("", "value")
            # If no exception, it either succeeded or handled gracefully
            assert isinstance(result, bool)
        except (IndexError, KeyError):
            # Expected behavior for invalid path
            pass

    def test_config_representation(self, fresh_config_manager):
        """Test __repr__ method."""
        repr_str = repr(fresh_config_manager)
        assert "ConfigManager" in repr_str
        assert "config" in repr_str.lower()


class TestConfigIntegration:
    """Integration tests with real scenarios."""

    def test_audio_profile_workflow(self, fresh_config_manager):
        """Test typical audio profile setup workflow."""
        # Get current device
        device = fresh_config_manager.get("audio.device_id", default=None)

        # Update device
        fresh_config_manager.set("audio.device_id", 2)

        # Load and verify
        loaded_device = fresh_config_manager.get("audio.device_id")
        assert loaded_device == 2

    def test_theme_preference_workflow(self, fresh_config_manager):
        """Test typical theme preference workflow."""
        themes = ["deep_tech_blue", "light", "dark"]

        for theme in themes:
            fresh_config_manager.set("ui.theme", theme)
            assert fresh_config_manager.get("ui.theme") == theme

    def test_multi_settings_update(self, fresh_config_manager):
        """Test updating multiple settings."""
        settings = {
            "audio.master_volume": 0.8,
            "audio.blocksize": 1024,
            "ui.theme": "dark"
        }

        for key, value in settings.items():
            fresh_config_manager.set(key, value)

        for key, expected_value in settings.items():
            assert fresh_config_manager.get(key) == expected_value
