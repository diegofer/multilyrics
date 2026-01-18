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

### ⏳ Tarea #5: Sistema de Perfiles
- **Estado**: 🚧 EN PROGRESO (2026-01-18)
- **Archivos**: `config/profiles/`, `core/audio_profiles.py`, `main.py`
- **Tiempo Estimado**: 4h
- **Plan**:
  1. Crear estructura de carpetas `config/profiles/{linux,windows,macos}/`
  2. Definir `AudioProfile` dataclass en `core/audio_profiles.py`
  3. Crear perfiles JSON:
     - `legacy.json`: Hardware 2008-2012 (blocksize=4096, gc_policy=disable)
     - `balanced.json`: Hardware 2013-2018 (blocksize=2048, gc_policy=disable)
     - `modern.json`: Hardware 2019+ (blocksize=1024, gc_policy=normal)
     - `low_latency.json`: Hardware 2020+ (blocksize=512, gc_policy=normal)
  4. Implementar auto-detección de hardware (CPU, RAM, año)
  5. Integrar en `main.py` con override manual
- **Validación Pendiente**:
  - [ ] Sintaxis verificada
  - [ ] Tests con cada perfil
  - [ ] Detección de CPU funcionando
  - [ ] Override manual en Settings

---

## 🟡 PRIORIDAD MEDIA

### ⏸️ Tarea #6: Script de validación de multi
- **Estado**: ❌ NO INICIADA
- **Archivos**: `scripts/validate_multi.py`
- **Tiempo Estimado**: 1h
- **Objetivo**: Validar sample rate de todos los tracks offline
- **Dependencias**: Tarea #3 completada ✅

---

### ⏸️ Tarea #7: Widget de latency monitor
- **Estado**: ⚠️ PARCIALMENTE COMPLETADA (widget creado, falta integración en Settings)
- **Archivos**: `ui/widgets/latency_monitor.py` ✅, UI settings pendiente
- **Tiempo Real**: 30 min (widget básico)
- **Pendiente**: Integración en Settings → Audio → Show Latency Monitor

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

**Tiempo Invertido**: ~5.5h  
**Tiempo Estimado Restante**: ~11.5h  
**Progreso**: 36% completado  

**Desglose por Prioridad**:
- 🔴 Alta: 4/5 completadas (80%)
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

---

## 🎯 Próximo Objetivo

**Tarea #5: Audio Profile System**
- Crear perfiles para diferentes configuraciones de hardware
- Auto-detección de CPU, RAM, OS
- Override manual en Settings
- Integración transparente en `main.py`

**Estimado**: 4h de trabajo
**Inicio**: 2026-01-18
**Meta**: Completar antes del 2026-01-19
