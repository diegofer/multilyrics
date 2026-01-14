import json
import re
from pathlib import Path
from typing import Dict, Any

class MetaJson:
    def __init__(self, meta_path: Path):
        # Aseguramos que sea un objeto Path
        self.meta_path = Path(meta_path)
        if not self.meta_path.exists():
            self._create_initial_meta()

    def _create_initial_meta(self):
        initial_data = {
            "title": "",  # Legacy - kept for compatibility
            "artist": "",  # Legacy - kept for compatibility
            "track_name": "",  # Original metadata for lyrics search (immutable)
            "artist_name": "",  # Original metadata for lyrics search (immutable)
            "track_name_display": "",  # Clean display name (user-editable)
            "artist_name_display": "",  # Clean display name (user-editable)
            "year": "",
            "key": "",
            "tempo": 0.0,
            "duration": 0.0,  # Legacy format
            "duration_seconds": 0.0,  # Normalized duration for API
            "compass": "?/?",
            "tracks": {},
            "chords": [],
            "beats": []            
        }
        self._write_meta(initial_data)

    def _write_meta(self, data: Dict[str, Any]):
        # 1. Generamos el JSON con indentación normal
        json_string = json.dumps(data, ensure_ascii=False, indent=4)
        self.meta_path.write_text(json_string, encoding='utf-8')

    def read_meta(self) -> Dict[str, Any]:
        return json.loads(self.meta_path.read_text(encoding='utf-8'))

    def update_key(self, key: str, value: Any):
        meta_data = self.read_meta()
        meta_data[key] = value
        self._write_meta(meta_data)

    def update_meta(self, new_data: Dict[str, Any]):
        meta_data = self.read_meta()
        meta_data.update(new_data)
        self._write_meta(meta_data)