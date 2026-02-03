# MPV Migration - Estado de Implementación

**Fecha:** 2026-02-03  
**Última sesión:** Lazy initialization + sync tuning  
**Branch:** main  
**Commits pendientes:** 5 archivos modificados

---

## 🎯 Plan Original (6 Steps)

### ✅ Step 1: Commit VLC Baseline
**Estado:** ⏳ PENDIENTE - No se creó tag aún

**Tareas:**
- [ ] Crear commit con estado actual de VLC engine
- [ ] Documentar elastic sync zones:
  - DEAD_ZONE=50ms (era 40ms, ajustado)
  - ELASTIC_THRESHOLD=200ms (era 150ms, ajustado)
  - HARD_THRESHOLD=400ms (era 300ms, ajustado)
- [ ] Tag como `vlc-legacy-baseline`
- [ ] Referencias: `video_lyrics_background.py:159`, `sync.py` 3-zone strategy

**Nota:** Los umbrales fueron ajustados durante optimización de sync MPV.

---

### ✅ Step 2: Implement Critical MPV Methods
**Estado:** ✅ COMPLETADO (parcial)

**Implementado:**
- ✅ `set_rate()` - línea 283 de mpv_engine.py
- ✅ `get_length()` - línea 341 de mpv_engine.py  
- ✅ `set_end_callback()` - línea 364 de mpv_engine.py con event callback

**Pendiente:**
- [ ] Validar rango 0.95-1.05 funciona sin glitches
- [ ] Test exhaustivo de rate adjustments en elastic sync

**Notas:**
- MPV engine inicializado correctamente
- Audio deshabilitado con `audio='no'`
- End callback usa QTimer.singleShot(0) para dispatch seguro

---

### ⏳ Step 3: Add Performance Metrics
**Estado:** ⏳ NO INICIADO

**Tareas pendientes:**
- [ ] Agregar timing en `video_lyrics_background.py:159` 
- [ ] Guard con `logger.isEnabledFor(logging.DEBUG)`
- [ ] Store en `self._perf_samples = deque(maxlen=100)`
- [ ] Método `get_avg_latency()` retornando dict

---

### ⏳ Step 4: Add Engine Selection Config
**Estado:** ⏳ NO INICIADO

**Tareas pendientes:**
- [ ] Agregar `"video": {"engine": "mpv"}` en config_manager.py
- [ ] Refactor `_initialize_engine()` en video.py:84-106
- [ ] Soporte para opciones: "mpv"|"vlc"|"auto"
- [ ] Logging de fallback MPV→VLC

**Nota:** Actualmente hardcoded como "auto" en video.py línea 123.

---

### ⏳ Step 5: Add Engine Badge
**Estado:** ✅ PARCIALMENTE IMPLEMENTADO

**Implementado:**
- ✅ QLabel badge en video.py (líneas 83-104)
- ✅ Muestra "MPV" o "VLC"
- ✅ Estilo con background rgba, padding, border-radius

**Pendiente:**
- [ ] Connect resizeEvent() para reposicionar badge en esquina
- [ ] Actualmente badge está visible pero posición fija

---

### ⏳ Step 6: Test Matrix with Metrics
**Estado:** ⏳ TESTING EN PROGRESO

**Tests realizados:**
- ✅ Full mode: MPV engine funciona
- ✅ Window show/hide: Lazy initialization exitosa
- ✅ Sync básico: Video se sincroniza con audio
- ⚠️ Sync stability: Saltos visibles reducidos pero no eliminados

**Pendiente:**
- [ ] Test Loop mode
- [ ] Test Static mode  
- [ ] Metrics logging cada 60s
- [ ] Document en docs/VIDEO_ENGINE_COMPARISON.md

---

## 🔧 Cambios Críticos Implementados (Fuera del Plan)

### 1. **Lazy Engine Initialization** (CRÍTICO)
**Problema:** Ventana aparecía automáticamente al cargar canción.

**Solución:**
- Engine ahora se crea SOLO cuando usuario hace clic en show_video_btn
- Previene llamada prematura a `winId()` que fuerza creación de ventana nativa
- Video path guardado en `_pending_video_path` para lazy loading

**Archivos modificados:**
- `video/video.py`: Engine initialization postponed (líneas 77-80)
- `video/video.py`: `show_window()` crea engine on-demand (líneas 207-215)
- `main.py`: Guard para `engine is not None` antes de load (líneas 877-889)

**Resultado:** ✅ Ventana NO aparece en carga, SOLO aparece en show_video_btn

---

### 2. **Sync Parameters Tuning** (CRÍTICO)
**Problema:** Saltos visibles molestos, desincronización aleatoria.

**Solución - Ajustes en `core/sync.py`:**

| Parámetro | Antes | Después | Razón |
|-----------|-------|---------|-------|
| Correction Timer | 1000ms (1Hz) | 250ms (4Hz) | Correcciones más frecuentes |
| DEAD_ZONE | 40ms | 50ms | Más permisivo |
| ELASTIC_THRESHOLD | 150ms | 200ms | Zona suave más amplia |
| HARD_THRESHOLD | 300ms | 400ms | Evita seeks prematuros |
| Rate Min/Max | ±5% (0.95-1.05) | ±3% (0.97-1.03) | Ajustes más sutiles |
| Rate Adjustment | `drift_ms/1000` | `drift_ms/2000` | 50% más suave |
| Rate Change Threshold | 0.02 | 0.01 | Más responsivo |

**Resultado:** ⚠️ Saltos reducidos pero no eliminados completamente

---

### 3. **MPV Audio Fix**
**Problema:** Error "option does not exist" con `no_audio=True`.

**Solución:**
- Cambiado a `audio='no'` en mpv_engine.py línea 86
- Removido `log_level='info'` (opción inválida)

---

### 4. **VLC Pause-After-Load**
**Problema:** Video auto-play al cargar.

**Solución:**
- Agregado `play()` + `pause()` sequence en vlc_engine.py líneas 121-123
- MPV usa `pause = True` después de loadfile

---

## 📊 Estado Actual del Testing

### Test 1: Modo Full ✅ (Parcialmente exitoso)

**Flujo probado:**
1. ✅ Carga canción → ventana NO aparece
2. ✅ Show video btn → ventana aparece fullscreen en pantalla secundaria
3. ✅ Video pausado correctamente
4. ✅ Play → video reproduce
5. ⚠️ Sincronización: saltos visibles reducidos pero persisten
6. ⚠️ Después de 10-20s: desincronización aleatoria
7. ✅ Pause → respuesta inmediata
8. ⚠️ Seek (doble clic timeline) → salta correctamente pero fallos aleatorios

**Diagnóstico:**
- Sync más estable que antes pero no perfecto
- Posibles causas:
  - MPV puede requerir más tuning de buffering
  - Timer de 250ms aún puede ser lento para video
  - Elastic corrections pueden ser demasiado sutiles

---

## 🚧 Problemas Conocidos

1. **Sync Stability:**
   - Saltos ocasionales visibles
   - Desincronización aleatoria después de 10-20s
   - Seeks fallan aleatoriamente

2. **Performance Metrics Ausente:**
   - No hay logging de latencias
   - No se puede medir overhead de set_rate/seek
   - Difícil diagnosticar bottlenecks

3. **Config Hardcoded:**
   - Engine selection no configurable desde Settings
   - Usuario no puede forzar VLC si MPV falla

---

## 📝 Próximos Pasos Recomendados

### Inmediato (Sesión actual)
1. ✅ Mover logs a folder `logs/`
2. ✅ Documentar estado en este archivo
3. ⏳ Commit cambios actuales
4. ⏳ Push al repositorio remoto

### Próxima sesión (Continuar plan)
1. **Step 3:** Implementar performance metrics
   - Agregar timing guards en apply_correction()
   - Loggear latencias de set_rate() y seek()
   - Diagnosticar si hay bottleneck en MPV

2. **Step 4:** Config de engine selection
   - Permitir forzar VLC desde Settings
   - Agregar opción "auto" con fallback logging

3. **Step 6:** Completar test matrix
   - Test Loop mode (assets/loops/default.mp4)
   - Test Static mode (frame freeze)
   - Document comparativa MPV vs VLC

4. **Optimización adicional si persiste sync issue:**
   - Considerar aumentar correction timer a 100ms (10Hz)
   - Revisar MPV buffering options (cache, demuxer)
   - Test con diferentes codecs de video

---

## 🔗 Referencias de Código

**Archivos modificados (pendientes de commit):**
- `video/video.py` - Lazy engine initialization
- `main.py` - Guard para engine load
- `core/sync.py` - Sync parameters tuning
- `video/engines/mpv_engine.py` - Audio fix, end callback
- `video/engines/vlc_engine.py` - Pause after load

**Archivos clave no modificados:**
- `video/backgrounds/video_lyrics_background.py` - Apply corrections
- `video/background_manager.py` - Mode selection
- `core/config_manager.py` - Settings persistence

---

## 💡 Notas para Continuar desde Otro PC

1. **Después de pull:**
   ```bash
   git pull origin main
   source env/bin/activate  # Linux/macOS
   .\env\Scripts\Activate.ps1  # Windows
   ```

2. **Para testing:**
   - Cargar canción con video.mp4
   - Click show_video_btn (debe aparecer solo en pantalla 2)
   - Play y observar sync por 30-60 segundos
   - Hacer seeks (doble clic timeline)

3. **Para continuar Step 3 (metrics):**
   - Editar `video/backgrounds/video_lyrics_background.py:159`
   - Agregar timing con `time.perf_counter()`
   - Store en `collections.deque(maxlen=100)`

4. **Para crear VLC baseline tag:**
   ```bash
   git tag -a vlc-legacy-baseline -m "VLC engine baseline before full MPV migration"
   git push origin vlc-legacy-baseline
   ```

---

**Última actualización:** 2026-02-03
