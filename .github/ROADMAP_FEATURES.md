# 🗺️ MultiLyrics: Roadmap de Features Futuras

> **Documentación relacionada:**
> - [copilot-instructions.md](copilot-instructions.md) - Guía técnica con arquitectura implementada
> - [PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md) - Resumen ejecutivo del proyecto
> - [../docs/IMPLEMENTATION_ROADMAP.md](../docs/IMPLEMENTATION_ROADMAP.md) - Historial de optimizaciones completadas

Este documento contiene la arquitectura planificada para features no implementadas.

---

## 🎯 Features Planificadas

### 1. Multi-Monitor Display Management (Stage Display / Proyector)

**Estado:** ✅ Fallback automático implementado (2026-01-22)  
**Objetivo:** Gestión robusta de múltiples pantallas para proyección en vivo

#### Implementado:
- **Fallback Automático (Opción 1):** Si no hay pantalla secundaria, la ventana de video se muestra en modo ventana 16:9 (80% del ancho de pantalla) en la pantalla primaria. Permite preview del video cuando solo hay un monitor disponible.
- **Logging informativo:** Indica modo fallback con emoji 📐 y geometría calculada
- **Preserva funcionalidad dual-monitor:** Fullscreen en pantalla secundaria cuando está disponible

#### Pendiente (Opción 2 - Stage Display Avanzado):

**Objetivo:** Permitir selección manual de pantalla objetivo para múltiples proyectores o configuraciones complejas.

**Casos de Uso:**
- Iglesias con 3+ monitores (FOH, stage monitor, proyector)
- Configuraciones con laptop + 2 monitores externos
- Selección explícita cuando auto-detección falla

**Arquitectura Propuesta:**
```python
# En ui/widgets/settings_dialog.py
class SettingsDialog:
    def _create_video_settings(self):
        # Combo box con pantallas disponibles
        self.screen_combo = QComboBox()
        screens = QApplication.screens()
        for i, screen in enumerate(screens):
            label = f"Pantalla {i}: {screen.name()} ({screen.geometry().width()}x{screen.geometry().height()})"
            self.screen_combo.addItem(label, i)
        
        # Cargar selección guardada
        saved_index = config.get("video.screen_index", 1)
        self.screen_combo.setCurrentIndex(saved_index)
```

**ConfigManager:**
```json
{
  "video": {
    "screen_index": 1,  // Pantalla objetivo (0=primaria, 1=secundaria, etc.)
    "mode": "full",
    "fallback_to_window": true  // Si pantalla no existe, usar ventana
  }
}
```

**VideoLyrics Refactor:**
- Reemplazar `screen_index` hardcoded en constructor
- Leer `screen_index` desde ConfigManager al inicializar
- Agregar método `update_screen_index(new_index)` para cambios en vivo
- Validar índice al cambiar (si no existe, usar fallback)

**UI en Settings:**
- Dropdown: "Pantalla de Video: [Pantalla 1: DP-1 (1920x1080) ▼]"
- Checkbox: "Usar modo ventana si pantalla no disponible"
- Botón "Probar Pantalla" (muestra video 3 segundos en pantalla seleccionada)

**Prioridad:** Media (cuando se reciban reportes de usuarios con múltiples proyectores)

---

### 2. Split Mode Routing (L/R Channel Separation)

**Objetivo:** Permitir monitoreo profesional en vivo para iglesias y equipos de alabanza.

**Arquitectura:**
- **Canal Izquierdo (L):** Mezcla Mono de la instrumentación (stems sin click ni guía)
- **Canal Derecho (R):** Metrónomo (Click) + Guía de Voz (Cues)

**Propósito:**
- Músicos escuchan instrumentación en un oído
- Guía de voz + click en el otro oído
- Permite coordinación perfecta sin contaminar la mezcla principal

**Implementación sugerida:**
```python
# En core/engine.py
def _mix_block_split_mode(self, start: int, frames: int):
    """Mix with L/R channel separation for stage monitoring."""
    instrumental_mix = self._mix_tracks(exclude=['click', 'cues'])
    click_cues_mix = self._mix_tracks(only=['click', 'cues'])
    
    # Output: L=instrumental (mono), R=click+cues (mono)
    output[:, 0] = instrumental_mix
    output[:, 1] = click_cues_mix
    return output
```

**UI:**
- Checkbox en Settings: "Enable Split Mode"
- Visual indicator en mixer: "L: Instrumental | R: Click+Cues"

---

### 3. Sistema de Cues (Guía de Voz Automática)

**Objetivo:** Disparar automáticamente guías de voz pregrabadas antes de cambios de sección.

**Regla:** Disparar samples `.wav` exactamente **4 beats antes** del inicio de una sección.

**Arquitectura:**
```python
# En core/cues.py
class CuesManager:
    def __init__(self, beats: np.ndarray, sections: List[Section]):
        """
        Args:
            beats: Matriz [[timestamp, beat_pos], ...]
            sections: Lista de secciones con start_time
        """
        self.cues_schedule = self._calculate_cue_times(beats, sections)
    
    def _calculate_cue_times(self, beats, sections):
        """Calculate cue trigger times (4 beats before section start)."""
        cue_times = []
        for section in sections:
            # Find 4th beat before section start
            beat_idx = self._find_beat_index(section.start_time, beats)
            cue_time = beats[beat_idx - 4][0]  # 4 beats before
            cue_times.append({
                'time': cue_time,
                'audio': f'cues/{section.name}.wav',
                'section': section.name
            })
        return cue_times
```

**Samples requeridos:**
- `assets/cues/verse.wav` - "Verso"
- `assets/cues/chorus.wav` - "Coro"
- `assets/cues/bridge.wav` - "Puente"
- `assets/cues/intro.wav` - "Intro"
- `assets/cues/outro.wav` - "Outro"

**UI:**
- Lista de cues en Settings con preview
- Enable/disable por sección
- Ajuste de volumen de cues independiente

---

### 4. Pitch Shifting (Transposición Offline)

**Objetivo:** Cambiar tonalidad de todas las pistas antes de reproducción.

**Tecnología:** `pyrubberband` (wrapper de Rubber Band Library)

**Arquitectura:**
```python
# En core/pitch_shifter.py
import pyrubberband as pyrb

class PitchShifter:
    @staticmethod
    def shift_audio(audio: np.ndarray, semitones: int, sr: int) -> np.ndarray:
        """
        Shift audio by semitones using Rubber Band.
        
        Args:
            audio: Audio array (n_samples, n_channels)
            semitones: Pitch shift in semitones (-12 to +12)
            sr: Sample rate
            
        Returns:
            Shifted audio with same length
        """
        if semitones == 0:
            return audio
        
        # Rubber Band preserves length
        shifted = pyrb.pitch_shift(audio, sr, semitones)
        return shifted.astype(np.float32)
```

**Flujo de trabajo:**
1. Usuario selecciona canción
2. UI muestra selector de semitonos (-12 a +12)
3. Al cambiar semitono, mostrar diálogo: "Procesando transposición..."
4. Procesar TODOS los stems offline (puede tomar 10-30 segundos)
5. Guardar versión transpuesta en caché: `library/multis/{song}/cache/shifted_{semitones}/`
6. Cargar versión transpuesta en lugar de original

**UI:**
- Spin box en toolbar: "Semitones: [ -2 ▼ ]"
- Rango: -12 (octava abajo) a +12 (octava arriba)
- Display: "Tono original: C | Actual: Bb" (usando key de meta.json)

**Optimizaciones:**
- Caché persistente: No reprocesar si ya existe
- Worker thread: No bloquear UI durante procesamiento
- Progress bar: Mostrar "Procesando: Drums (1/6)..."

---

### 5. Control Remoto (FastAPI + WebSockets)

**Objetivo:** Controlar MultiLyrics desde dispositivos móviles en la misma red.

**Arquitectura:**

#### Backend (FastAPI embebido)
```python
# En core/remote_control.py
from fastapi import FastAPI, WebSocket
from threading import Thread
import uvicorn

class RemoteControlServer:
    def __init__(self, engine: MultiTrackPlayer):
        self.app = FastAPI()
        self.engine = engine
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.get("/api/status")
        async def get_status():
            return {
                "playing": self.engine.is_playing(),
                "position": self.engine.get_position_seconds(),
                "duration": self.engine.get_duration_seconds()
            }
        
        @self.app.post("/api/control/play")
        async def play():
            self.engine.play()
            return {"status": "ok"}
        
        @self.app.post("/api/control/pause")
        async def pause():
            self.engine.pause()
            return {"status": "ok"}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            # Stream position updates
            while True:
                data = {
                    "position": self.engine.get_position_seconds(),
                    "playing": self.engine.is_playing()
                }
                await websocket.send_json(data)
                await asyncio.sleep(0.1)
    
    def start(self, port: int = 8080):
        """Start server in background thread."""
        thread = Thread(
            target=uvicorn.run,
            args=(self.app,),
            kwargs={"host": "0.0.0.0", "port": port},
            daemon=True
        )
        thread.start()
```

#### Frontend (Vue.js ligero)
```html
<!-- assets/remote/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>MultiLyrics Remote</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <div id="app">
        <h1>MultiLyrics Remote Control</h1>
        <div class="position">{{ formatTime(position) }} / {{ formatTime(duration) }}</div>
        <div class="controls">
            <button @click="play">▶️ Play</button>
            <button @click="pause">⏸️ Pause</button>
            <button @click="stop">⏹️ Stop</button>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/vue@3"></script>
    <script>
        const app = Vue.createApp({
            data() {
                return { position: 0, duration: 0, playing: false };
            },
            methods: {
                async play() { await fetch('/api/control/play', {method: 'POST'}); },
                async pause() { await fetch('/api/control/pause', {method: 'POST'}); },
                formatTime(seconds) { /* ... */ }
            },
            mounted() {
                const ws = new WebSocket(`ws://${location.host}/ws`);
                ws.onmessage = (e) => {
                    const data = JSON.parse(e.data);
                    this.position = data.position;
                    this.playing = data.playing;
                };
            }
        });
        app.mount('#app');
    </script>
</body>
</html>
```

**UI (Emparejamiento):**
- Botón en toolbar: "📱 Remote Control"
- Diálogo muestra:
  - QR code con URL: `http://192.168.1.100:8080`
  - IP local detectada automáticamente
  - Instrucciones: "Escanea el QR desde tu móvil"

**Protocolo JSON:**
```json
// Control messages
{"action": "play"}
{"action": "pause"}
{"action": "seek", "position": 45.5}
{"action": "volume", "track": 0, "value": 0.8}

// Status updates (WebSocket)
{
  "position": 45.5,
  "duration": 180.0,
  "playing": true,
  "tracks": [
    {"name": "Drums", "muted": false, "volume": 0.9}
  ]
}
```

---

### 6. ConfigManager Singleton

**Objetivo:** Gestión centralizada de configuración persistente.

**Arquitectura:**
```python
# En core/config_manager.py
import json
from pathlib import Path
from typing import Any, Optional

class ConfigManager:
    """Singleton for managing application settings."""
    
    _instance: Optional['ConfigManager'] = None
    
    def __init__(self):
        if ConfigManager._instance is not None:
            raise RuntimeError("Use ConfigManager.get_instance()")
        self.config_path = Path("config/settings.json")
        self.settings = self._load_settings()
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance
    
    def _load_settings(self) -> dict:
        """Load settings from JSON file."""
        if not self.config_path.exists():
            return self._get_defaults()
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _get_defaults(self) -> dict:
        return {
            "audio": {
                "device_id": None,
                "blocksize": 2048,
                "master_volume": 0.9,
                "show_latency_monitor": False
            },
            "ui": {
                "theme": "deep_tech_blue",
                "window_geometry": None
            },
            "paths": {
                "library_root": "library/multis",
                "assets_root": "assets"
            },
            "remote": {
                "enabled": False,
                "port": 8080
            }
        }
    
    def save(self):
        """Persist settings to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get setting by dot-notation path.
        Example: config.get("audio.device_id")
        """
        keys = key_path.split('.')
        value = self.settings
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set setting by dot-notation path.
        Example: config.set("audio.device_id", 5)
        """
        keys = key_path.split('.')
        target = self.settings
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self.save()
```

**Uso:**
```python
# En main.py
config = ConfigManager.get_instance()
device_id = config.get("audio.device_id")
engine = MultiTrackPlayer(device_id=device_id)

# En settings dialog
config.set("audio.master_volume", 0.8)
```

---

### 7. Verificación de Dependencias del Sistema (installer.py)

**Objetivo:** Validar dependencias del sistema al inicio y guiar al usuario.

**Arquitectura:**
```python
# En installer.py
import platform
import subprocess
import sys
from pathlib import Path

class SystemValidator:
    """Validate system dependencies before app start."""
    
    @staticmethod
    def check_ffmpeg() -> bool:
        """Check if ffmpeg is available in PATH."""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def check_libportaudio_linux() -> bool:
        """Check if libportaudio2 is installed (Linux only)."""
        if platform.system() != 'Linux':
            return True
        
        # Check if library exists
        lib_paths = [
            '/usr/lib/x86_64-linux-gnu/libportaudio.so.2',
            '/usr/lib/libportaudio.so.2'
        ]
        return any(Path(p).exists() for p in lib_paths)
    
    @staticmethod
    def validate_all() -> dict:
        """Run all validations and return report."""
        report = {
            'ffmpeg': SystemValidator.check_ffmpeg(),
            'libportaudio': SystemValidator.check_libportaudio_linux()
        }
        return report
    
    @staticmethod
    def show_installation_guide(missing: list):
        """Show GUI dialog with installation instructions."""
        system = platform.system()
        
        instructions = []
        if 'ffmpeg' in missing:
            if system == 'Linux':
                instructions.append("sudo apt install ffmpeg")
            elif system == 'Windows':
                instructions.append("Download from https://ffmpeg.org/")
            elif system == 'Darwin':
                instructions.append("brew install ffmpeg")
        
        if 'libportaudio' in missing:
            instructions.append("sudo apt install libportaudio2")
        
        # Show Qt dialog with instructions
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Missing Dependencies")
        msg.setText("Some system dependencies are missing:")
        msg.setDetailedText("\n".join(instructions))
        msg.exec()

# En main.py
if __name__ == '__main__':
    validator = SystemValidator()
    report = validator.validate_all()
    
    missing = [k for k, v in report.items() if not v]
    if missing:
        validator.show_installation_guide(missing)
        sys.exit(1)
    
    # Continue with normal startup
    app = QApplication(sys.argv)
    # ...
```

---

## 📅 Prioridad Sugerida

1. **Alta:** ConfigManager (base para todo)
2. **Alta:** Verificación de dependencias (UX inicial)
3. **Media:** Multi-Monitor Display Management - Opción 2 (selección manual de pantalla)
4. **Media:** Split Mode Routing (feature killer para iglesias)
5. **Media:** Sistema de Cues (complementa split mode)
6. **Baja:** Control Remoto (nice-to-have)
7. **Baja:** Pitch Shifting (procesamiento costoso, casos de uso limitados)

---

## ✅ Features Ya Implementadas

Ver [IMPLEMENTATION_ROADMAP.md](../docs/IMPLEMENTATION_ROADMAP.md) para el estado de features implementadas:
- ✅ Audio Profile System
- ✅ GC Management
- ✅ Latency Monitoring
- ✅ Sample Rate Auto-Detection
- ✅ Benchmark Script
- ✅ Multi Validation
- ✅ Unit Tests (44/44 passed)
- ✅ Video Fallback Automático (modo ventana 16:9 en single-monitor)

---

**Última actualización:** 22 de enero de 2026
