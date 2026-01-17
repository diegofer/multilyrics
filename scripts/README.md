# Scripts de Utilidad

Scripts auxiliares para configuración, testing y mantenimiento de MultiLyrics.

## 📁 Contenido

### `test_video_display.py`
**Propósito:** Script de prueba para verificar el sistema de video en segunda pantalla (Linux/X11).

**Uso:**
```bash
python3 scripts/test_video_display.py
```

**Plataformas:** Linux (X11), macOS, Windows

**Documentación completa:** [`docs/TESTING_VIDEO_LINUX.md`](../docs/TESTING_VIDEO_LINUX.md)

---

### `setup_pipewire_ubuntu.sh`
**Propósito:** Configura PipeWire en Ubuntu 22.04+ para mejorar latencia de audio (recomendado para hardware antiguo).

**Uso:**
```bash
chmod +x scripts/setup_pipewire_ubuntu.sh
./scripts/setup_pipewire_ubuntu.sh
# IMPORTANTE: Reiniciar sistema después de ejecutar
```

**Plataformas:** Ubuntu 22.04, 23.04, 23.10, 24.04+

**Beneficios:**
- Reduce latencia de audio (de ~15ms a ~5ms)
- Mejor sincronización audio-video
- Soporte moderno para ALSA/JACK

**Verificar instalación:**
```bash
pactl info | grep "Server Name"
# Salida esperada: PulseAudio (built on PipeWire)
```

**Documentación completa:** [`docs/SETUP_AUDIO_LINUX.md`](../docs/SETUP_AUDIO_LINUX.md)

---

## 🗂️ Organización por Sistema Operativo

Futuros scripts seguirán esta convención de nomenclatura:

- `setup_*_ubuntu.sh` - Ubuntu/Debian específico
- `setup_*_fedora.sh` - Fedora/RHEL específico
- `setup_*_arch.sh` - Arch Linux específico
- `setup_*_macos.sh` - macOS específico
- `setup_*_windows.ps1` - Windows PowerShell

**Ejemplos planeados:**
- `setup_audio_windows.ps1` - Configurar WASAPI exclusivo en Windows
- `setup_coreaudio_macos.sh` - Optimizar CoreAudio en macOS

---

## 📚 Documentación Relacionada

- **Desarrollo general:** [`docs/development.md`](../docs/development.md)
- **Arquitectura:** [`docs/architecture.md`](../docs/architecture.md)
- **Audio en Linux:** [`docs/SETUP_AUDIO_LINUX.md`](../docs/SETUP_AUDIO_LINUX.md) *(próximamente)*
- **Video en Linux:** [`docs/FIXES_VIDEO_LINUX.md`](../docs/FIXES_VIDEO_LINUX.md)

---

## 🤝 Contribuir

Al agregar nuevos scripts:
1. Nombrar según convención `<propósito>_<plataforma>.<ext>`
2. Documentar en este README
3. Crear guía detallada en `docs/` si es complejo
4. Validar en múltiples versiones de la plataforma objetivo
