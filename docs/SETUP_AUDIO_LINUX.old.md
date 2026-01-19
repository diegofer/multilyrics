# Configuración de Audio en Linux

Guía completa para optimizar el audio en MultiLyrics bajo diferentes distribuciones de Linux.

## 📋 Tabla de Contenidos

- [Sistemas Soportados](#sistemas-soportados)
- [PipeWire vs PulseAudio](#pipewire-vs-pulseaudio)
- [Instalación en Ubuntu 22.04+](#instalación-en-ubuntu-2204)
- [Configuración Manual](#configuración-manual)
- [Verificación y Troubleshooting](#verificación-y-troubleshooting)
- [Hardware Antiguo](#hardware-antiguo)

---

## Sistemas Soportados

| Distribución | Versión | Audio Backend | Estado |
|-------------|---------|---------------|--------|
| Ubuntu | 22.04+ | PipeWire (recomendado) | ✅ Soportado |
| Ubuntu | 20.04 | PulseAudio | ✅ Soportado |
| Ubuntu | 18.04 | PulseAudio | ⚠️ No testeado |
| Linux Mint | 21+ | PipeWire disponible | ✅ Soportado |
| Linux Mint | 20 | PulseAudio | ✅ Soportado |
| Fedora | 34+ | PipeWire (por defecto) | ✅ Soportado |
| Arch Linux | Rolling | PipeWire disponible | ✅ Soportado |
| Debian | 12+ | PipeWire disponible | ⚠️ No testeado |

---

## PipeWire vs PulseAudio

### ¿Qué es PipeWire?

PipeWire es el sucesor moderno de PulseAudio, diseñado para baja latencia y mejor compatibilidad con aplicaciones profesionales de audio.

### Comparación

| Característica | PulseAudio | PipeWire |
|---------------|------------|----------|
| **Latencia típica** | 15-25ms | 5-10ms |
| **Sincronización AV** | Buena | Excelente |
| **CPU en hardware antiguo** | Media | Baja |
| **Soporte JACK** | Limitado | Nativo |
| **Estabilidad** | Muy estable | Estable (desde 2022) |

### Recomendación

- **Hardware moderno (2015+)**: PipeWire (mejor latencia)
- **Hardware antiguo (2008-2014)**: PipeWire (menor uso de CPU)
- **Ubuntu < 22.04**: PulseAudio (única opción disponible)

---

## Instalación en Ubuntu 22.04+

### Método Automático (Recomendado)

```bash
cd /path/to/multilyrics
chmod +x scripts/setup_pipewire_ubuntu.sh
./scripts/setup_pipewire_ubuntu.sh
```

**Después de ejecutar:**
1. Reinicia tu equipo: `sudo reboot`
2. Verifica instalación: `pactl info | grep "Server Name"`
3. Debería mostrar: `PulseAudio (built on PipeWire)`

### Método Manual

Si prefieres instalar manualmente:

```bash
# 1. Instalar paquetes
sudo apt update
sudo apt install -y \
    pipewire-audio-client-libraries \
    libspa-0.2-bluetooth \
    libspa-0.2-jack \
    wireplumber \
    pipewire-pulse

# 2. Deshabilitar PulseAudio
systemctl --user --now disable pulseaudio.service pulseaudio.socket
systemctl --user mask pulseaudio

# 3. Habilitar PipeWire
systemctl --user --now enable pipewire pipewire-pulse wireplumber

# 4. Reiniciar servicios
systemctl --user restart pipewire pipewire-pulse wireplumber

# 5. Reiniciar equipo
sudo reboot
```

---

## Configuración Manual

### Seleccionar Dispositivo de Audio

MultiLyrics usa `sounddevice` (PortAudio) que auto-detecta el dispositivo por defecto. Para listar dispositivos disponibles:

```python
import sounddevice as sd
print(sd.query_devices())
```

### Ajustar Buffer Size

Si experimentas glitches de audio en hardware antiguo:

1. Abre `core/constants.py`
2. Modifica `AUDIO_BLOCKSIZE`:
   ```python
   AUDIO_BLOCKSIZE = 2048  # Default: 512
   # Valores más altos = mayor latencia, menos glitches
   ```

### Latencia Alta (Hardware Antiguo)

En `core/engine.py` se fuerza latencia alta por defecto:

```python
self.stream = sd.OutputStream(
    samplerate=self.samplerate,
    blocksize=self.blocksize,
    channels=2,
    dtype='float32',
    callback=self._callback,
    latency='high'  # ← Reduce underruns en CPUs lentas
)
```

---

## Verificación y Troubleshooting

### Verificar Sistema de Audio Activo

```bash
# Ver qué servidor está corriendo
pactl info | grep "Server Name"

# Listar dispositivos de audio
pactl list sinks short

# Ver latencia actual
pactl list sinks | grep "Latency"
```

### Problemas Comunes

#### 1. Audio entrecortado (xruns)

**Causa:** Buffer size muy pequeño para tu CPU.

**Solución:**
```bash
# Editar configuración de PipeWire
mkdir -p ~/.config/pipewire
cp /usr/share/pipewire/pipewire.conf ~/.config/pipewire/

# Editar ~/.config/pipewire/pipewire.conf
# Buscar "default.clock.quantum" y cambiar a 2048
```

#### 2. No hay sonido después de instalar PipeWire

**Solución:**
```bash
# Reiniciar servicios
systemctl --user restart pipewire pipewire-pulse wireplumber

# Si sigue sin funcionar, reinstalar
systemctl --user unmask pulseaudio
sudo apt install --reinstall pipewire-pulse

# Reiniciar equipo
sudo reboot
```

#### 3. Latencia muy alta en PipeWire

**Verificar:**
```bash
pw-metadata -n settings
# Buscar "default.clock.quantum"
```

**Reducir latencia (solo si tienes CPU potente):**
```bash
pw-metadata -n settings 0 clock.force-quantum 256
```

#### 4. Desinstalar PipeWire y volver a PulseAudio

```bash
# Deshabilitar PipeWire
systemctl --user --now disable pipewire pipewire-pulse wireplumber

# Habilitar PulseAudio
systemctl --user unmask pulseaudio
systemctl --user --now enable pulseaudio.service pulseaudio.socket

# Reiniciar
sudo reboot
```

---

## Hardware Antiguo

### Especificaciones Objetivo

MultiLyrics está optimizado para funcionar en:

- **CPU:** Intel Core 2 Duo (2008) o superior
- **RAM:** 8GB
- **Almacenamiento:** SSD (recomendado) o HDD
- **Audio:** Cualquier tarjeta con ALSA

### Optimizaciones Automáticas

El código incluye detección de hardware antiguo (`video/video.py`):

```python
def _detect_legacy_hardware(self):
    # Detecta CPUs Sandy Bridge (2011) o más antiguas
    # Ajusta configuración automáticamente
```

### Ajustes Manuales para Hardware Antiguo

1. **Desactivar video si no es necesario:**
   - Usa el botón de toggle de video en la UI

2. **Aumentar buffer size:**
   - Edita `core/constants.py` → `AUDIO_BLOCKSIZE = 2048`

3. **Usar PipeWire con latencia alta:**
   - Configurar `default.clock.quantum = 2048` en `~/.config/pipewire/pipewire.conf`

4. **Deshabilitar efectos visuales:**
   - En Ubuntu: Settings → Appearance → Animations OFF

---

## Soporte Multiplataforma

### Linux (ALSA/PulseAudio/PipeWire)

MultiLyrics usa `sounddevice` que internamente usa PortAudio. En Linux, PortAudio detecta automáticamente:
- ALSA directamente (baja latencia)
- PulseAudio (compatibilidad)
- PipeWire (moderno)

### Windows (WASAPI)

Ver documentación específica: `docs/SETUP_AUDIO_WINDOWS.md` *(próximamente)*

### macOS (CoreAudio)

Ver documentación específica: `docs/SETUP_AUDIO_MACOS.md` *(próximamente)*

---

## Referencias

- [PipeWire Wiki](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/home)
- [PortAudio Documentation](http://www.portaudio.com/docs.html)
- [sounddevice Python](https://python-sounddevice.readthedocs.io/)
- [Ubuntu PipeWire Guide](https://ubuntuhandbook.org/index.php/2022/04/pipewire-replace-pulseaudio-ubuntu-2204/)
