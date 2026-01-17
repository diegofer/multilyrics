# 🖥️ Perfiles de Hardware y Optimizaciones

## Resumen

Este documento describe las optimizaciones implementadas para diferentes generaciones de hardware, especialmente para CPUs antiguas (2008-2012) y sistemas Linux con ALSA.

---

## 📊 Perfiles de Hardware

### 🟢 Hardware Moderno (2015+)
**Ejemplos:** Intel i5-6xxx+, AMD Ryzen series, Apple M1/M2

**Configuración:**
- Buffer audio: `512-1024 samples` (~10-21ms latency)
- Downsample waveform: `1024 samples/bucket`
- Throttling UI: `60 FPS` (0.016s)
- Video: **Habilitado por defecto** (1080p)

**Archivo:** `core/engine.py`, `ui/widgets/timeline_view.py`

---

### 🟡 Hardware Medio (2012-2015)
**Ejemplos:** Intel i5-3xxx/4xxx, AMD FX series

**Configuración:**
- Buffer audio: `1024-2048 samples` (~21-43ms latency)
- Downsample waveform: `2048 samples/bucket`
- Throttling UI: `45 FPS` (0.022s)
- Video: **Habilitado por defecto** (720p recomendado)

**Implementación:** Ajustar manualmente en código o futuro sistema de perfiles

---

### 🔴 Hardware Legacy (2008-2012)
**Ejemplos:** Intel Sandy Bridge (i5-2410M), Core 2 Duo, AMD pre-2013

**Configuración ACTUAL (Implementada):**
- Buffer audio: `2048 samples` (~43ms @ 48kHz)
- Latency ALSA: `high` (mayor buffer interno)
- Downsample waveform: `4096 samples/bucket` (agresivo)
- Throttling UI: `30 FPS` (0.033s)
- Video: **Deshabilitado por defecto** (usuario puede activar manualmente)

**Archivos modificados:**
```
core/engine.py (líneas 48-66, 228-241)
ui/widgets/timeline_view.py (líneas 50-62, 961-983, 1006-1016)
video/video.py (líneas 38-159)
ui/widgets/controls_widget.py (líneas 15, 114-131, 184-201)
main.py (líneas 127-131, 156-161, 313-325)
```

---

## 🔧 Optimizaciones Implementadas

### 1️⃣ **Audio Engine (`core/engine.py`)**

#### Aumento de Buffer Size
```python
# Línea 48
def __init__(self, samplerate: int = 44100, blocksize: int = 2048, dtype: str = 'float32'):
```

**Antes:** `blocksize=1024` (21ms @ 48kHz)
**Ahora:** `blocksize=2048` (43ms @ 48kHz)

**Beneficio:** 
- ✅ Reduce underruns en CPUs antiguas
- ✅ Da más tiempo al callback para completar procesamiento
- ⚠️ Aumenta latencia (aceptable para playback, no para instrumentos en vivo)

#### Latency Mode
```python
# Líneas 228-241
self._stream = sd.OutputStream(
    samplerate=self.samplerate,
    blocksize=self.blocksize,
    channels=self._n_output_channels,
    dtype=self.dtype,
    callback=self._callback,
    finished_callback=self._on_stream_finished,
    latency='high',  # ← CRÍTICO para hardware antiguo
    prime_output_buffers_using_stream_callback=True  # ← Pre-llenar buffers
)
```

**Antes:** Sin `latency` parameter (usa default 'low')
**Ahora:** `latency='high'` solicita mayor buffer interno a ALSA

**Beneficio:**
- ✅ ALSA crea buffers más grandes internamente
- ✅ Protege contra jitter del sistema operativo
- ✅ Reduce mensajes "underrun occurred" en dmesg

---

### 2️⃣ **Timeline Rendering (`ui/widgets/timeline_view.py`)**

#### Throttling de `paintEvent`
```python
# Líneas 961-983
def paintEvent(self, event):
    import time
    if not hasattr(self, '_last_paint_time'):
        self._last_paint_time = 0.0
    
    current_time = time.time()
    elapsed = current_time - self._last_paint_time
    
    if elapsed < 0.033:  # 30 FPS max (1/30 = 0.033s)
        event.ignore()
        return
    
    self._last_paint_time = current_time
```

**Antes:** Sin throttling (60+ FPS, depende de Qt event loop)
**Ahora:** Máximo 30 FPS (33ms entre frames)

**Beneficio:**
- ✅ Reduce ~50% carga de CPU en renderizado
- ✅ Libera ciclos para audio callback
- ⚠️ Playhead se ve menos "suave" (imperceptible en práctica)

#### Downsample Agresivo en Modo GENERAL
```python
# Líneas 50-62
GLOBAL_DOWNSAMPLE_FACTOR = 4096  # Configurado para i5-2410M (Sandy Bridge)
```

**Antes:** `1024 samples/bucket` (alta resolución visual)
**Ahora:** `4096 samples/bucket` (4x menos operaciones de dibujado)

**Beneficio:**
- ✅ Reduce drásticamente número de líneas dibujadas
- ✅ Vista GENERAL sigue siendo legible
- ✅ No afecta modos PLAYBACK/EDIT (zoom mayor)

---

### 3️⃣ **Detección de Hardware Legacy (`video/video.py`)**

#### Detección Automática de CPU Antigua
```python
# Líneas 84-140
def _detect_legacy_hardware(self) -> bool:
    # Detecta CPUs específicas conocidas por problemas:
    legacy_cpu_markers = [
        "i5-2410m",  # Sandy Bridge (2011) - tu caso
        "i3-2", "i5-2", "i7-2",  # Sandy Bridge series
        "core(tm)2 duo", "core(tm)2 quad",  # Core 2 series
        "pentium(r) dual",  # Pentium Dual Core
    ]
```

**Método:** Lee `/proc/cpuinfo` en Linux y busca marcadores de CPUs antiguas

**Conservador:** Solo marca como legacy si hay coincidencia exacta (evita falsos positivos)

#### Desactivación Automática de Video
```python
# Líneas 38-44
self._is_legacy_hardware = self._detect_legacy_hardware()
self._video_auto_disabled = self._is_legacy_hardware

if self._video_auto_disabled:
    logger.warning("⚠️ Hardware antiguo detectado - Video deshabilitado...")
```

**Beneficio:**
- ✅ Elimina carga de VLC decoding en CPU antigua
- ✅ Usuario puede activar manualmente si lo desea
- ✅ No afecta hardware moderno (video ON por defecto)

#### Optimizaciones VLC Condicionales
```python
# Líneas 50-57
if self._is_legacy_hardware:
    vlc_args.extend([
        '--avcodec-hurry-up',         # Skip frames si CPU lenta
        '--avcodec-skiploopfilter=4', # Saltear deblocking
        '--avcodec-threads=2',        # Limitar threads
        '--file-caching=1000',        # Buffer más grande
    ])
```

**Beneficio:** Si usuario activa video en hardware antiguo, VLC usa configuración optimizada

---

### 4️⃣ **Toggle UI para Video (`ui/widgets/controls_widget.py`, `main.py`)**

#### Nuevo Botón de Control
```python
# controls_widget.py, líneas 114-131
self.video_enable_toggle_btn = QPushButton()
self.video_enable_toggle_btn.setCheckable(True)
self.video_enable_toggle_btn.setChecked(True)  # ON por defecto
self.video_enable_toggle_btn.toggled.connect(self._on_video_enable_toggled)
```

#### Sincronización con Detección Automática
```python
# main.py, líneas 127-131
self.controls.set_video_enabled_state(self.video_player.is_video_enabled())
```

**Flujo:**
1. App inicia → Detecta hardware legacy → `_video_auto_disabled = True`
2. `is_video_enabled()` retorna `False`
3. UI toggle se muestra como **desactivado**
4. Usuario puede **clicar** para habilitar video manualmente

---

## 🎯 Resultados Esperados

### ✅ Con Optimizaciones (Hardware Legacy)
```
🔊 Audio stream initialized: 48000Hz, blocksize=2048, latency=high
🔍 CPU Legacy detectada: i5-2410m
⚠️ Hardware antiguo detectado - Video deshabilitado por defecto
```

**Durante Playback:**
- ❌ **Sin** mensajes "underrun occurred" en dmesg
- ✅ Reproducción fluida de 4 stems simultáneos
- ✅ Timeline se actualiza a 30 FPS (suave pero no excesivo)
- ✅ Video deshabilitado (sin carga de VLC)

### ❌ Sin Optimizaciones (Antes)
```
WARNING [core.engine] Stream status: output underflow
ALSA lib pcm.c:8568:(snd_pcm_recover) underrun occurred
```

**Durante Playback:**
- ❌ Stuttering fuerte cada 10-15 segundos
- ❌ Timeline rendering compite con audio callback
- ❌ VLC decoding consume 40-60% CPU
- ❌ Total CPU usage: 170%+ (swapping)

---

## 📝 Notas de Implementación

### Comentarios de Código
Todas las optimizaciones están marcadas con bloques de comentarios claros:

```python
# ===========================================================================
# LEGACY HARDWARE OPTIMIZATION: [Descripción]
# ===========================================================================
# Explicación técnica...
# ===========================================================================
```

**Buscar en código:** `grep -r "LEGACY HARDWARE OPTIMIZATION"` para encontrar todas las optimizaciones

### Testing en Hardware Moderno
Para simular hardware legacy en equipo moderno (testing):

```bash
# Forzar detección de legacy (futuro feature)
export MULTILYRICS_FORCE_LEGACY=1
python main.py
```

### Ajuste Fino
Si aún hay stuttering leve:

1. **Aumentar blocksize:**
   ```python
   # core/engine.py, línea 48
   blocksize: int = 4096  # Era 2048
   ```

2. **Reducir FPS UI:**
   ```python
   # ui/widgets/timeline_view.py, línea 978
   if elapsed < 0.050:  # 20 FPS (era 0.033 = 30 FPS)
   ```

3. **Downsample más agresivo:**
   ```python
   # ui/widgets/timeline_view.py, línea 62
   GLOBAL_DOWNSAMPLE_FACTOR = 8192  # Era 4096
   ```

---

## 🚀 Roadmap Futuro

### Perfiles Automáticos
Crear sistema de detección y configuración automática:

```python
class HardwareProfile:
    MODERN = "modern"    # 2015+
    MEDIUM = "medium"    # 2012-2015
    LEGACY = "legacy"    # 2008-2012
    
def detect_profile() -> HardwareProfile:
    # Detectar generación de CPU y RAM
    # Retornar perfil apropiado
```

### Configuración Persistente
Guardar preferencias de usuario en `settings.json`:

```json
{
  "hardware_profile": "legacy",
  "video_enabled": false,
  "audio_blocksize": 2048,
  "ui_fps_limit": 30
}
```

### Benchmarking Automático
Sistema que detecte underruns y ajuste automáticamente:

```python
if underrun_count > 5:
    logger.warning("Ajustando blocksize automáticamente...")
    self.blocksize *= 2
    self._restart_stream()
```

---

## 🐛 Troubleshooting

### Problema: Aún hay stuttering después de optimizaciones

**Diagnóstico:**
```bash
# Monitorear underruns en tiempo real
journalctl -f | grep -i "underrun\|xrun"

# Verificar carga de CPU
top -p $(pidof python)
```

**Soluciones:**
1. Verificar que video esté realmente deshabilitado (check logs)
2. Aumentar blocksize a 4096 o 8192
3. Deshabilitar análisis de beats/chords en tiempo real (futuro)
4. Cerrar aplicaciones en background (Chrome, etc.)

### Problema: Video se siente lento o con lag

**Causa:** Optimizaciones VLC demasiado agresivas
**Solución:** Recodificar video a 720p con:
```bash
ffmpeg -i video.mp4 -vf scale=1280:720 -c:v libx264 -preset ultrafast -crf 28 -c:a copy video_720p.mp4
```

### Problema: Timeline se ve "blocky" en modo GENERAL

**Causa:** Downsample factor muy alto (4096)
**Solución:** Reducir a 2048 si CPU lo soporta:
```python
GLOBAL_DOWNSAMPLE_FACTOR = 2048
```

---

## 📚 Referencias

- **ALSA Underrun:** https://www.alsa-project.org/wiki/Underrun
- **sounddevice Latency:** https://python-sounddevice.readthedocs.io/en/latest/api/streams.html#sounddevice.Stream
- **VLC Command Line:** https://wiki.videolan.org/VLC_command-line_help/
- **Qt Performance:** https://doc.qt.io/qt-6/qtquick-performance.html

---

**Última actualización:** 2026-01-17
**Autor:** MultiLyrics Dev Team
**Hardware de referencia:** Toshiba Satellite L735 (i5-2410M, 8GB RAM, Ubuntu 22.04)
