# 🎯 MultiLyrics Audio Optimization - Implementation Roadmap

**Última Actualización**: 2026-01-18  
**Estado General**: 4/11 tareas completadas (36%)

---

## 🔴 PRIORIDAD ALTA

### ✅ Tarea #1: Deshabilitar GC durante playback
- **Estado**: ✅ COMPLETADA (2026-01-17)
- **Archivos**: `core/engine.py`, `main.py`
- **Tiempo Real**: 45 min
- **Commit**: `d5851b5` - "feat: implement GC management and sample rate auto-detection"
- **Validación**: 
  - ✅ Sintaxis verificada
  - ✅ Tests manuales exitosos
  - ✅ GC se deshabilita en `play()` y se restaura en `stop()`/`pause()`
- **Resultados**: 
  - GC policy configurable: `'disable_during_playback'` (default) o `'normal'`
  - Logging informativo con emoji 🗑️
  - Integrado en todos los métodos de control de playback

---

### ✅ Tarea #2: Validación RAM pre-load
- **Estado**: ✅ COMPLETADA (2026-01-17)
- **Archivos**: `core/engine.py`
- **Tiempo Real**: 1.5h
- **Commit**: `882712d` - "feat: implement RAM validation and latency measurement"
- **Validación**:
  - ✅ Sintaxis verificada
  - ✅ Test suite ejecutado: `scripts/test_audio_optimizations.py`
  - ✅ RAM detection: 31.26 GB total, 23.38 GB disponible
  - ✅ Threshold del 70% funcionando correctamente
- **Resultados**:
  - Validación automática antes de pre-cargar tracks
  - Error claro con RAM requerida vs disponible
  - Fallback graceful si psutil no disponible
  - Logging con emoji 💾

---

### ✅ Tarea #3: Auto-detect sample rate
- **Estado**: ✅ COMPLETADA (2026-01-17)
- **Archivos**: `core/engine.py`, `main.py`
- **Tiempo Real**: 1h
- **Commit**: `d5851b5` - "feat: implement GC management and sample rate auto-detection"
- **Validación**:
  - ✅ Sintaxis verificada
  - ✅ Auto-detección funcionando: 48000 Hz detectado
  - ✅ Validación de todos los tracks
  - ✅ Mensajes de error con comando ffmpeg
- **Resultados**:
  - `samplerate: Optional[int] = None` en constructor
  - Auto-detección desde primer track
  - Soporte para 44.1 kHz y 48 kHz
  - Sin resampling en vivo (por estabilidad)
  - Logging con emoji 🎵

---

### ✅ Tarea #4: Medición interna de latencia
- **Estado**: ✅ COMPLETADA (2026-01-17)
- **Archivos**: `core/engine.py`, `ui/widgets/latency_monitor.py`
- **Tiempo Real**: 2h (incluye widget y tests)
- **Commit**: `882712d` - "feat: implement RAM validation and latency measurement"
- **Validación**:
  - ✅ Sintaxis verificada
  - ✅ Test suite exitoso: 51 callbacks, 0.17ms mean, 0 xruns
  - ✅ Budget: 42.67ms, Usage: 0.4%
  - ✅ Widget de debug creado
- **Resultados**:
  - Circular buffer (last 100 callbacks) con `collections.deque`
  - Detección automática de xruns (>80% budget)
  - Método `get_latency_stats()` con 7 métricas
  - Logging inteligente (cada 10° xrun)
  - Widget opcional para UI debug
  - Performance excelente en hardware moderno

---

### ✅ Tarea #5: Sistema de Perfiles
- **Estado**: ✅ COMPLETADA (2026-01-18)
- **Archivos**: `config/profiles/`, `core/audio_profiles.py`, `main.py`
- **Tiempo Real**: 3h
- **Commit**: `281efd8` - "feat: implement Audio Profile System with auto-detection"
- **Validación**:
  - ✅ Sintaxis verificada (core/audio_profiles.py, main.py)
  - ✅ Aplicación inicia correctamente
  - ✅ Auto-detección funcionando: ~2018 CPU, 31GB RAM, 6 cores
  - ✅ Perfil seleccionado: "Balanced Performance"
- **Resultados**:
  - 10 perfiles JSON creados (linux/windows/macos × 3-4 perfiles)
  - AudioProfile dataclass con from_json() loader
  - AudioProfileManager con singleton pattern
  - Hardware auto-detection (CPU year, RAM, cores)
  - Decision tree para selección automática
  - Logging informativo con emojis 🖥️💻🎛️
  - Integration transparente en main.py

---

## 🟡 PRIORIDAD MEDIA

### ✅ Tarea #6: Script de validación de multi
- **Estado**: ✅ COMPLETADA (2026-01-18)
- **Archivos**: `scripts/validate_multi.py`
- **Tiempo Real**: 1h
- **Objetivo**: Validar sample rate de todos los tracks offline
- **Dependencias**: Tarea #3 completada ✅
- **Commit**: `e1b31bb`

#### Validación:
- ✅ Sintaxis: `python -m py_compile scripts/validate_multi.py`
- ✅ Validación single multi: OK (La Bondad de Dios - 4 tracks @ 44100 Hz)
- ✅ Validación --all: OK (2/2 multis passed)
- ✅ Detección de mismatch: OK (44100 vs 48000 Hz detectado correctamente)
- ✅ Generación de comandos ffmpeg: OK
- ✅ Logging informativo con emojis: OK

#### Resultados:
- Script completo con 3 modos: single multi, --all, help
- Detecta sample rate mismatches y genera comandos de corrección
- Warnings para duration/channel mismatches (no críticos)
- Estadísticas detalladas por track y resumen general
- Exit code 0 (success) o 1 (failed) para integración en CI/CD

---

### ✅ Tarea #7: Widget de latency monitor
- **Estado**: ✅ COMPLETADA (2026-01-18)
- **Archivos**: `ui/widgets/settings_dialog.py`, `main.py`, `ui/widgets/latency_monitor.py` (ya existía)
- **Tiempo Real**: 30min
- **Objetivo**: Integrar LatencyMonitor en Settings con checkbox show/hide
- **Dependencias**: Tarea #4 completada ✅
- **Commit**: (pendiente)

#### Validación:
- ✅ Sintaxis: `python -m py_compile settings_dialog.py main.py`
- ✅ Aplicación inicia correctamente
- ✅ LatencyMonitor agregado a UI (inicialmente oculto)
- ✅ Settings carga configuración desde config/settings.json
- ✅ Checkbox funcional: muestra/oculta monitor en tiempo real
- ✅ Persistencia: configuración guardada entre sesiones

#### Resultados:
- SettingsDialog creado con Audio Settings group
- Checkbox "Show Latency Monitor" con tooltip
- Método estático get_setting() para lectura global de config
- MainWindow.set_latency_monitor_visible() para control de visibilidad
- Configuración persistente en config/settings.json
- Botón settings ya existía en controls_widget, solo conectado

---

### ⏸️ Tarea #8: Benchmark script
- **Estado**: ❌ NO INICIADA
- **Archivos**: `scripts/benchmark_audio_profile.py`
- **Tiempo Estimado**: 2h
- **Objetivo**: Recomendar perfil óptimo automáticamente
- **Dependencias**: Tarea #5 completada (en progreso)

---

### ⏸️ Tarea #9: Documentar perfiles
- **Estado**: ❌ NO INICIADA
- **Archivos**: `docs/SETUP_AUDIO_LINUX.md`, `docs/SETUP_AUDIO_WINDOWS.md`, `docs/SETUP_AUDIO_MACOS.md`
- **Tiempo Estimado**: 1h
- **Objetivo**: Documentar cada perfil y su caso de uso
- **Dependencias**: Tarea #5 completada (en progreso)

---

## 🟢 PRIORIDAD BAJA

### ⏸️ Tarea #10: Rampa exponencial gain
- **Estado**: ❌ NO INICIADA
- **Archivos**: `core/engine.py`
- **Tiempo Estimado**: 30 min
- **Nota**: Baja prioridad - rampa lineal actual es suficiente
- **Objetivo**: Evitar clicks en cambios bruscos de volumen

---

### ⏸️ Tarea #11: Tests unitarios mixer
- **Estado**: ❌ NO INICIADA
- **Archivos**: `tests/test_engine_mixer.py`
- **Tiempo Estimado**: 2h
- **Objetivo**: Cobertura completa de lógica de mixer
- **Tests existentes**: `test_multitrack_master_gain.py` ✅

---

## 📊 Estadísticas Generales

**Tiempo Invertido**: ~8.5h  
**Tiempo Estimado Restante**: ~8.5h  
**Progreso**: 45% completado  

**Desglose por Prioridad**:
- 🔴 Alta: 5/5 completadas (100%) ✅
- 🟡 Media: 0.5/4 completadas (12.5%)
- 🟢 Baja: 0/2 completadas (0%)

---

## ✅ Criterios de Validación (Checklist Obligatorio)

Después de cada tarea completada:

1. **Sintaxis**: ✅ `python -m py_compile <archivos_modificados>`
2. **Tests**: ✅ Ejecutar suite relevante si existe
3. **Logging**: ✅ Verificar que logs son informativos (con emojis)
4. **Documentación**: ✅ Actualizar CHANGELOG/README si aplica
5. **Commit**: ✅ Mensaje descriptivo con resultados
6. **Roadmap**: ✅ Actualizar este archivo con estado

---

## 📝 Notas de Implementación

### Tarea #1 (GC Management)
- **Aprendizaje**: GC puede causar pausas de 10-100ms en hardware legacy
- **Decisión**: Deshabilitar durante playback es seguro (sesiones cortas, sin allocation)
- **Alternativa**: Profile "modern" puede usar `gc_policy='normal'`

### Tarea #2 (RAM Validation)
- **Aprendizaje**: 70% threshold previene swap thrashing
- **Decisión**: Fallback graceful si psutil no disponible
- **Alternativa**: En futuro, paginación de tracks muy largos

### Tarea #3 (Sample Rate)
- **Aprendizaje**: Resampling en vivo es prohibitivo en CPUs antiguas
- **Decisión**: Auto-detect + validación estricta + error con fix command
- **Alternativa**: Offline resampling script para preparar multis

### Tarea #4 (Latency)
- **Aprendizaje**: `time.perf_counter()` tiene overhead mínimo (<0.01ms)
- **Decisión**: Circular buffer con deque (no allocation)
- **Resultado**: 0.4% usage en hardware moderno = excelente headroom

### Tarea #5 (Audio Profiles)
- **Aprendizaje**: CPU year detection via Python version + psutil es razonablemente preciso
- **Decisión**: Decision tree basado en CPU year, cores y RAM
- **Resultado**: Auto-selección correcta "Balanced" para hardware 2018
- **Alternativa**: Manual override disponible para casos especiales

### Tarea #6 (Multi Validation)
- **Aprendizaje**: soundfile.info() lee metadata sin cargar audio completo en RAM
- **Decisión**: Validación offline previene errores al cargar en la app
- **Resultado**: Detección correcta de mismatches + generación automática de fix commands
- **Beneficio**: Usuarios pueden validar multis descargados antes de usar

### Tarea #7 (Latency Monitor Integration)
- **Aprendizaje**: Settings dialog con persistencia JSON simple es suficiente
- **Decisión**: Checkbox en Settings para mostrar/ocultar widget de debug
- **Resultado**: Integración transparente, no invasiva, configuración persistente
- **Beneficio**: Usuarios avanzados pueden monitorear stats sin código

---

## 📊 Estadísticas Generales

**Tiempo Invertido**: ~10h  
**Progreso**: 64% completado (7/11 tareas)

**Desglose por Prioridad**:
- 🔴 Alta: 5/5 completadas (100%) ✅
- 🟡 Media: 2/4 completadas (50%)
- 🟢 Baja: 0/2 completadas (0%)

**Tareas Restantes**: 5h estimadas  
**Próxima Tarea**: Benchmark script (2h) o Profile documentation (1h)

---

## 🎯 Próximo Objetivo

**TODAS LAS TAREAS DE PRIORIDAD ALTA COMPLETADAS ✅**

**Tareas Pendientes (Prioridad Media):**
- Tarea #6: Script de validación de multi
- Tarea #7: Widget de latency monitor (parcial - falta integrar en Settings)
- Tarea #8: Benchmark script
- Tarea #9: Documentar perfiles

**Estimado Total Restante**: ~8.5h
**Próxima Sesión**: Comenzar con Tarea #6 o #7
