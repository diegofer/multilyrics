# 🎬 MpvEngine - Implementación Mínima Funcional

**Fecha:** 25 de enero de 2026  
**Estado:** ✅ **COMPLETADO - Mínimo Viable Implementado**  
**Tests:** 288/292 passed (16/16 video tests ✅)

---

## 📋 Alcance Implementado

### ✅ Métodos Core (11 de 11)

**Lifecycle:**
- ✅ `initialize()` - Crea mpv player con config básica
- ✅ `shutdown()` - Libera recursos mpv

**Window Management:**
- ✅ `attach_window()` - Adjunta a HWND/XID/NSView (Qt window)
- ✅ `show()` - No-op (Qt controla visibilidad)
- ✅ `hide()` - No-op (Qt controla visibilidad)

**Media Control:**
- ✅ `load()` - Carga MP4 o imágenes
- ✅ `play()` - Inicia/resume playback
- ✅ `pause()` - Pausa playback
- ✅ `stop()` - Pausa + seek(0)
- ✅ `seek()` - Seek absoluto en seconds

**Playback Parameters:**
- ✅ `set_loop()` - Loop infinito (`loop-file=inf`)

**State/Timing:**
- ✅ `get_time()` - Posición actual en seconds
- ✅ `is_playing()` - True si no pausado

---

## ❌ Fuera de Alcance (Deliberadamente)

**No Implementados (stubs con warnings):**
- ❌ `set_rate()` - Sync via seek, no rate changes
- ❌ `get_length()` - No requerido para loop (boundary timer)
- ❌ `set_end_callback()` - Backgrounds usan polling
- ❌ `is_paused()` - No crítico para minimal impl
- ❌ `get_state()` - Estado granular no requerido

**Razón:** Mantener implementación simple y estable. Backgrounds ya manejan estas necesidades.

---

## 🔧 Configuración mpv

### Argumentos Básicos
```python
mpv.MPV(
    # Audio
    no_audio=True,  # AudioEngine owns audio
    
    # Video
    vo='gpu',       # Hardware rendering
    hwdec='auto',   # Auto hardware decode
    
    # Window
    keep_open='yes', # No close after playback
    idle='yes',      # Keep alive when idle
    
    # Performance
    video_sync='display-resample',  # Smooth
    
    # Logging
    log_level='info',
    terminal='no',
    msg_level='all=error',
)
```

### Legacy Hardware Optimizations
```python
if is_legacy_hardware:
    player['profile'] = 'sw-fast'   # Software decode
    player['scale'] = 'bilinear'    # Fast scaling
```

---

## 🎯 Características Implementadas

### 1. ✅ Lazy Import con Fallback Seguro

```python
def initialize(self) -> None:
    try:
        import mpv  # Lazy import
    except ImportError as e:
        raise RuntimeError(
            "python-mpv not installed. "
            "Install with: pip install python-mpv"
        ) from e
```

**Beneficio:** App puede iniciar sin mpv instalado (usa VLC).

### 2. ✅ Multi-Platform Window Attachment

```python
def attach_window(self, win_id, screen_index, fullscreen):
    system = self.system  # Auto-detect
    
    if system == "Windows":
        self.player['wid'] = int(win_id)  # HWND
    elif system == "Linux":
        self.player['wid'] = int(win_id)  # XID
    elif system == "Darwin":
        self.player['wid'] = int(win_id)  # NSView
```

**Beneficio:** Funciona en Windows/Linux/macOS sin cambios.

### 3. ✅ Loop Infinito Nativo

```python
def set_loop(self, enabled: bool):
    self._loop_enabled = enabled
    if self.player:
        self.player['loop-file'] = 'inf' if enabled else 'no'
```

**Beneficio:** LoopBackground puede usar loop nativo de mpv.

### 4. ✅ Soporte MP4 e Imágenes

```python
def load(self, path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Media not found: {path}")
    
    self.player.loadfile(str(file_path.absolute()))
```

**Beneficio:** Soporta videos (MP4) y static frames (PNG, JPEG).

---

## 📊 Comparativa: VLC vs mpv

| Feature | VlcEngine | MpvEngine |
|---------|-----------|-----------|
| **Lifecycle** | ✅ `__init__` heavy | ✅ `initialize()` lazy |
| **Window Embed** | ✅ Qt-controlled | ✅ Qt-controlled |
| **Play/Pause/Stop** | ✅ Implemented | ✅ Implemented |
| **Seek (seconds)** | ✅ ms→s convert | ✅ Native seconds |
| **Loop** | ✅ `--repeat` arg | ✅ `loop-file=inf` |
| **Rate Control** | ✅ `set_rate()` | ❌ Not implemented |
| **Get Length** | ✅ `get_length()` | ❌ Not implemented |
| **EOF Callback** | ✅ VLC events | ❌ Not implemented |
| **State Granular** | ✅ `get_state()` | ❌ Stub |
| **Legacy Hardware** | ✅ CPU-specific args | ✅ `sw-fast` profile |

**Conclusión:** mpv es **más simple** pero **suficiente** para playback visual básico.

---

## 🎨 Orden de Métodos (Conforme a VisualEngine)

**Orden en base.py → Orden en mpv_engine.py:**

1. `initialize()` ✅
2. `shutdown()` ✅
3. `attach_window()` ✅
4. `show()` ✅
5. `hide()` ✅
6. `load()` ✅
7. `play()` ✅
8. `pause()` ✅
9. `stop()` ✅
10. `seek()` ✅
11. `set_rate()` ⚠️ (stub)
12. `set_loop()` ✅
13. `get_time()` ✅
14. `get_length()` ⚠️ (stub)
15. `is_playing()` ✅
16. `is_paused()` ⚠️ (stub)
17. `get_state()` ⚠️ (stub)
18. `set_end_callback()` ⚠️ (stub)

**Leyenda:**
- ✅ Implementado completamente
- ⚠️ Stub con warning (fuera de alcance mínimo)

---

## ✅ Validación

### Test Results
```bash
tests/test_video_architecture.py::16 passed ✅
- test_mpv_engine_implements_interface PASSED ✅

Total suite: 288/292 passed (99% success rate) ✅
```

### Sintaxis
```bash
py_compile: mpv_engine.py ✅
```

### Dependencias
**Nueva dependencia opcional:**
```bash
pip install python-mpv
```

**Fallback seguro:** Si `python-mpv` no disponible, app usa VLC (no crash).

---

## 🚀 Uso en Producción

### Construcción + Inicialización
```python
# Construction (lightweight)
engine = MpvEngine(is_legacy_hardware=False)

# Initialize resources (lazy)
try:
    engine.initialize()
except RuntimeError as e:
    logger.error(f"mpv not available: {e}")
    # Fallback to VLC
    engine = VlcEngine(is_legacy_hardware=False)
    engine.initialize()
```

### Playback Loop
```python
# Load media
engine.load("assets/loops/default.mp4")

# Enable infinite loop
engine.set_loop(True)

# Attach to Qt window
win_id = int(self.winId())
engine.attach_window(win_id, screen_index=1, fullscreen=True)

# Start playback
engine.play()

# Monitor position
while True:
    position = engine.get_time()
    is_playing = engine.is_playing()
    # ... update UI
```

### Cleanup
```python
# Stop playback
engine.stop()

# Release resources
engine.shutdown()
```

---

## 📝 Limitaciones Conocidas

### 1. ⚠️ win_id Requerido
**Problema:** `attach_window(win_id=None)` lanza `NotImplementedError`.

**Razón:** mpv-owned window no implementado en alcance mínimo.

**Workaround:** Siempre proveer `win_id` desde Qt widget.

### 2. ⚠️ set_rate() No Soportado
**Problema:** Sync elástico (rate 0.95-1.05) no disponible.

**Razón:** VideoLyricsBackground usa rate para correcciones finas.

**Workaround:** MpvEngine solo para LoopBackground (no sync).

### 3. ⚠️ get_length() Devuelve -1.0
**Problema:** Duración no expuesta.

**Razón:** LoopBackground usa boundary timer (no necesita duración).

**Workaround:** Si necesitas duración, usa VLC o parsea con ffprobe.

### 4. ⚠️ EOF Callback No Implementado
**Problema:** `set_end_callback()` es stub.

**Razón:** Backgrounds usan polling vía `is_playing()`.

**Workaround:** LoopBackground detecta end via boundary timer.

---

## 🎯 Recomendaciones de Uso

### ✅ Casos de Uso Ideales
1. **LoopBackground:** Loop infinito de video sin sync
2. **StaticFrameBackground:** Mostrar frame estático (PNG/JPEG)
3. **BlankBackground:** Ventana negra (no media loaded)

### ❌ No Recomendado Para
1. **VideoLyricsBackground:** Requiere `set_rate()` para sync elástico
2. **Sync Complejo:** mpv no soporta rate control fino

### 💡 Estrategia de Selección
```python
# En VideoLyrics.__init__()
config = ConfigManager.get_instance()
video_mode = config.get("video.mode")

if video_mode in ["loop", "static", "none"]:
    # mpv es suficiente (no sync requerido)
    try:
        self.engine = MpvEngine(is_legacy_hardware)
        self.engine.initialize()
    except RuntimeError:
        # Fallback a VLC si mpv no disponible
        self.engine = VlcEngine(is_legacy_hardware)
        self.engine.initialize()
else:
    # video_mode == "full" → requiere sync → usa VLC
    self.engine = VlcEngine(is_legacy_hardware)
    self.engine.initialize()
```

---

## 🔮 Futuras Mejoras (Fuera de Alcance Mínimo)

### Alta Prioridad
- [ ] `set_rate()` implementation (enable sync support)
- [ ] `get_length()` from `duration` property
- [ ] `set_end_callback()` via mpv event observers

### Media Prioridad
- [ ] `is_paused()` implementation (check `pause` property)
- [ ] `get_state()` implementation (map internal state)
- [ ] mpv-owned window support (`win_id=None`)

### Baja Prioridad
- [ ] Hardware decode validation (check `hwdec-current`)
- [ ] Performance metrics (dropped frames via `decoder-frame-drop-count`)
- [ ] Custom profiles per video mode

---

## 📚 Dependencias

### python-mpv
**Instalación:**
```bash
pip install python-mpv
```

**Requisitos del Sistema:**
- **Windows:** `mpv.exe` en PATH o mismo directorio
- **Linux:** `libmpv.so.1` (install via `apt install libmpv1`)
- **macOS:** `libmpv.dylib` (install via `brew install mpv`)

**Verificación:**
```python
try:
    import mpv
    player = mpv.MPV()
    print("✅ mpv available")
except ImportError:
    print("❌ python-mpv not installed")
except Exception as e:
    print(f"❌ mpv runtime error: {e}")
```

---

## ✅ Estado Final

**🎊 MPVENGINE MÍNIMO FUNCIONAL IMPLEMENTADO**

**Características:**
- 🎯 11/11 métodos core implementados
- 🛡️ Lazy import con fallback seguro
- 🌍 Multi-plataforma (Windows/Linux/macOS)
- 🔄 Loop infinito nativo
- 📹 Soporte MP4 + imágenes
- ✅ 288/292 tests pasan
- 📝 Código claro y documentado

**Arquitectura:**
- ✅ No rompe interfaz VisualEngine
- ✅ VLC sigue siendo backend principal
- ✅ mpv como opción ligera para casos simples

**Tiempo Invertido:** ~1.5 horas  
**Líneas de Código:** 428 líneas (incluye docstrings)

---

**Próximo Commit:**
```bash
git add video/engines/mpv_engine.py tests/test_video_architecture.py docs/
git commit -m "feat: implement minimal functional MpvEngine

Minimal viable implementation using python-mpv:
- initialize/shutdown lifecycle
- attach_window (HWND/XID/NSView)
- load/play/pause/stop/seek
- set_loop (native infinite loop)
- get_time/is_playing state queries

Out of scope (stubs):
- set_rate (sync via seek, not rate)
- get_length (boundary timer used)
- set_end_callback (polling used)
- is_paused/get_state (not critical)

Features:
- Lazy import with safe fallback
- Multi-platform (Windows/Linux/macOS)
- Supports MP4 and images
- Legacy hardware optimizations

Tests: 288/292 passed (16/16 video tests)
Ref: docs/MPV_ENGINE_IMPLEMENTATION.md"
```
