# 📜 MultiLyrics: Blueprint - Resumen Ejecutivo

> **Documentación relacionada:**
> - [copilot-instructions.md](copilot-instructions.md) - Guía técnica completa para AI agents
> - [ROADMAP_FEATURES.md](ROADMAP_FEATURES.md) - Features futuras no implementadas
> - [../docs/IMPLEMENTATION_ROADMAP.md](../docs/IMPLEMENTATION_ROADMAP.md) - Historial de tareas completadas (100% ✅)

---

## 🎯 Visión del Proyecto

**MultiLyrics** es un reproductor multitrack de audio/video con letras sincronizadas, diseñado para iglesias y equipos de alabanza con recursos limitados.

**Misión:** Democratizar el uso profesional de multitracks mediante una herramienta gratuita, ligera y multiplataforma.

**Valores:**
- 🆓 **Gratuito:** Código abierto bajo GNU GPLv3
- 🪶 **Ligero:** Compatible con hardware legacy (2008–2009)
- 🌍 **Multiplataforma:** Windows 10/11, Linux, macOS 10.13+
- 📚 **Ético:** Atribución académica en `CREDITS.md`

---

## 🏗️ Arquitectura Core (Implementada)

### Stack Tecnológico
- **UI:** PySide6 (Qt6)
- **Audio:** sounddevice + NumPy (float32)
- **Video:** python-vlc
- **Análisis:** madmom (beats, chords)
- **Extracción:** ffmpeg-python

### Patrón de Datos
- **Single Source of Truth:** `TimelineModel` es la fuente canónica del tiempo de reproducción
- **Observer Pattern:** Componentes no-Qt usan callbacks, componentes Qt usan signals
- **Pre-Load Strategy:** WAV completos en RAM para evitar disk I/O durante playback

### Reglas Críticas de Audio Callback
**❌ PROHIBIDO:** Locks, I/O, prints, Qt signals, allocación de memoria  
**✅ PERMITIDO:** Operaciones sobre arrays NumPy pre-cargados, aritmética básica

---

## 🚀 Features Planificadas

Ver [ROADMAP_FEATURES.md](ROADMAP_FEATURES.md) para especificaciones detalladas:

1. **Split Mode Routing** - L/R channel separation para monitoreo en vivo
2. **Sistema de Cues** - Guías de voz automáticas 4 beats antes de secciones
3. **Pitch Shifting** - Transposición offline con pyrubberband
4. **Control Remoto** - FastAPI + WebSockets para control desde móviles
5. **ConfigManager** - Singleton para gestión de configuración persistente
6. **Verificador de Dependencias** - Validación de ffmpeg y libportaudio al inicio

---

## 📐 Estructura de Proyecto

```
multilyrics/
├── core/              # Motor de audio, workers, coordinación
├── models/            # TimelineModel, LyricsModel, MetaJson
├── ui/                # PySide6 widgets, main_window, styles
├── utils/             # Logger, error_handler, lyrics_loader
├── library/multis/    # Librería de canciones descomprimidas
│   └── {song_name}/
│       ├── meta.json
│       ├── master.wav
│       ├── lyrics.lrc
│       ├── beats.json
│       ├── chords.json
│       ├── video.mp4 (opcional)
│       └── tracks/   # Stems individuales
├── tests/            # Test suite (44 tests, 100% pass)
└── docs/             # Documentación adicional
```

---

## 🎨 Identidad Visual

**Tema "Deep Tech Blue":**
- Fondo: `#0B0E14`
- Superficies: `#161B22`
- Acento Cian: `#00E5FF` (neón)
- Acento Púrpura: `#7C4DFF` (neón)

**Efectos:** Sombras neón con `QGraphicsDropShadowEffect`, iconos SVG dinámicos

---

## ✅ Estado de Implementación

### Completado (100%)
- ✅ Audio Engine (mixer con gain smoothing, solo/mute, master gain)
- ✅ Timeline Visualization (waveform, beats, chords, lyrics, playhead)
- ✅ Audio Profiles (3 perfiles: Legacy, Balanced, Ultra-Low-Latency)
- ✅ GC Management (disable durante playback en hardware legacy)
- ✅ Beat/Chord Detection (madmom workers)
- ✅ Audio Extraction (ffmpeg)
- ✅ Lyrics Sync (LRC parser, búsqueda automática)
- ✅ Unit Tests (44/44 passed)
- ✅ Multi Validation (formato, naming, metadata)

### En Progreso
- 🔄 DTO Refactor (migración a @dataclass inmutables)
- 🔄 Video Dual Display (proyector secundario)

### Planificado
Ver [ROADMAP_FEATURES.md](ROADMAP_FEATURES.md) para detalles completos

---

## 📚 Documentación Relacionada

- **[copilot-instructions.md](copilot-instructions.md)** - Guía completa para AI agents con patrones de código
- **[ROADMAP_FEATURES.md](ROADMAP_FEATURES.md)** - Especificaciones de features no implementadas
- **[IMPLEMENTATION_ROADMAP.md](../docs/IMPLEMENTATION_ROADMAP.md)** - Historial de tareas completadas
- **[architecture.md](../docs/architecture.md)** - Deep-dive técnico de la arquitectura
- **[CREDITS.md](../CREDITS.md)** - Atribuciones académicas y licencias de terceros

---

**Última actualización:** 18 de enero de 2026
