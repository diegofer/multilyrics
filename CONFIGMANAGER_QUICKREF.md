# ConfigManager Quick Reference

## Installation & Import

```python
from core.config_manager import ConfigManager

# Get singleton (creates if needed)
config = ConfigManager.get_instance()
```

## Basic Operations

### Get Settings

```python
# Simple get with default
volume = config.get("audio.master_volume", default=0.9)

# Without default (returns None if missing)
device_id = config.get("audio.device_id")

# Top-level dict
audio_settings = config.get("audio")

# With None/missing keys
value = config.get("nonexistent.path", default="fallback")
```

### Set Settings

```python
# Set and auto-save
config.set("audio.master_volume", 0.8)

# Creates nested structure automatically
config.set("custom.deeply.nested.key", "value")

# Set any type
config.set("custom.list", [1, 2, 3])
config.set("custom.dict", {"key": "value"})
```

## Advanced Operations

### Get All Settings

```python
# Returns deep copy (safe to modify)
all_settings = config.get_all()
```

### Merge Settings

```python
# Deep merge (preserves unmodified keys)
new_config = {
    "audio": {
        "device_id": 2,
        "blocksize": 2048
    }
}
config.merge_settings(new_config)
```

### Reset to Defaults

```python
# Reset all settings
config.reset_to_defaults()
```

### Explicit Save

```python
# Usually not needed (set() auto-saves)
success = config.save()
```

---

## Common Patterns

### Load Audio Profile on Startup

```python
# main.py
from core.config_manager import ConfigManager

config = ConfigManager.get_instance()
profile_name = config.get("audio.audio_profile", default="balanced")
```

### Update Settings from UI

```python
# SettingsDialog
def on_volume_changed(self, value):
    self.config.set("audio.master_volume", value)
    # Auto-saved, no manual save() needed
```

### Access Settings Everywhere

```python
# Any component
from core.config_manager import ConfigManager

config = ConfigManager.get_instance()
theme = config.get("ui.theme", default="deep_tech_blue")
```

### Default Settings Structure

```json
{
  "audio": {
    "device_id": null,
    "blocksize": 512,
    "sample_rate": null,
    "master_volume": 0.9,
    "enable_latency_monitor": true,
    "show_latency_monitor": true,
    "audio_profile": "balanced"
  },
  "ui": {
    "theme": "deep_tech_blue",
    "window_geometry": null,
    "window_state": null,
    "last_song": null
  },
  "paths": {
    "library_root": "library/multis",
    "loops_root": "library/loops",
    "assets_root": "assets",
    "logs_root": "logs"
  },
  "remote": {
    "enabled": false,
    "port": 8080,
    "host": "0.0.0.0"
  },
  "playback": {
    "loop_enabled": false,
    "auto_stop_enabled": true,
    "gc_policy": "disable_during_playback"
  }
}
```

---

## Singleton Management

```python
# Get singleton
config = ConfigManager.get_instance()

# Reset (only for testing)
ConfigManager.reset_instance()

# Create new instance (for testing with different config)
config = ConfigManager("path/to/test/config.json")
```

---

## Error Handling

ConfigManager handles errors gracefully:

| Scenario | Behavior |
|----------|----------|
| Missing config file | Loads defaults, creates file on first save |
| Corrupted JSON | Loads defaults, logs warning |
| Save failure | Logs error, keeps changes in memory |
| Invalid path | Returns default value or None |

No exceptions thrown - always continues running.

---

## Testing

```bash
# Run ConfigManager tests
python -m pytest tests/test_config_manager.py -v

# Run specific test
python -m pytest tests/test_config_manager.py::TestConfigGetSet -v

# Run full suite (272 tests)
python -m pytest tests/ -q
```

---

## Performance

| Operation | Time |
|-----------|------|
| get() | <1ms |
| set() | <5ms |
| merge_settings() | <10ms |
| reset_to_defaults() | <5ms |

---

## Files

| File | Purpose |
|------|---------|
| `core/config_manager.py` | Main singleton implementation |
| `tests/test_config_manager.py` | 34 unit tests |
| `docs/CONFIG_MANAGER_GUIDE.md` | Complete documentation |
| `config/settings.json` | Persisted settings file |

---

## See Also

- [CONFIG_MANAGER_GUIDE.md](../docs/CONFIG_MANAGER_GUIDE.md) - Full documentation
- [ROADMAP_FEATURES.md](../.github/ROADMAP_FEATURES.md) - Future features
- [core/config_manager.py](../core/config_manager.py) - Source code

