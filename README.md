# Multi Lyrics 🎵

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

**Multi Lyrics** es un reproductor profesional de audio/video multitrack diseñado específicamente para equipos de alabanza e iglesias. Ofrece visualización de letras sincronizadas, análisis avanzado de audio (detección de beats, reconocimiento de acordes) y visualización de formas de onda - todo en un paquete gratuito y de código abierto.

## 🚀 Inicio Rápido (¡Empieza aquí!)

**¿Primera vez?** Te recomendamos seguir la guía completa de instalación para tu sistema:

→ 🪟 **Windows**: [`docs/INSTALL_WINDOWS.md`](docs/INSTALL_WINDOWS.md) - **Guía paso a paso con explicaciones detalladas**  
→ 🐧 **Linux/Ubuntu**: [`docs/SETUP_AUDIO_LINUX.md`](docs/SETUP_AUDIO_LINUX.md)  
→ 🍎 **macOS**: [`docs/SETUP_AUDIO_MACOS.md`](docs/SETUP_AUDIO_MACOS.md)

**¿Ya tienes Python instalado?** Ve directo a [Instalación Rápida](#-instalación-rápida)

---

## ✨ Features

- 🎛️ **Multitrack Playback**: Play individual stems (drums, bass, vocals, etc.) with independent volume control
- 📊 **Waveform Visualization**: Interactive timeline with three zoom modes (General, Playback, Edit)
- 🎼 **Audio Analysis**: Automatic beat detection and chord recognition using madmom
- 📝 **Synchronized Lyrics**: LRC format support with auto-download from online sources
- 🎥 **Video Lyrics**: Optional video playback synchronized with audio
- 🎚️ **Professional Mixer**: Per-track mute/solo, logarithmic volume curves, master gain with headroom
- 🔄 **Live Worship Optimized**: Tracks start at 90% (-6 dB) for easy bass/drums boost during service
- 🎵 **Flexible Audio Formats**: Full support for WAV and OGG Vorbis stems (10:1 compression without quality loss)

## 🎵 Supported Audio Formats

Multi Lyrics supports multiple audio formats for maximum flexibility:

### Stems (Individual Tracks)
- **WAV** (Recommended for master/timeline): Uncompressed, best for waveform rendering
- **OGG Vorbis**: Compressed format with ~10:1 ratio, ideal for saving disk space
  - Example: 50MB WAV stem → 5-8MB OGG (quality 5)
  - Fully supported for playback, solo/mute, and mixing
  - No quality loss perceptible in worship context

### Master Track
- **WAV only**: Required for timeline waveform visualization performance

### Video
- **MP4** with H.264/AAC: Synchronized video lyrics playback

**Mix and match formats freely** - your multi can have `bass.ogg`, `drums.wav`, `vox.ogg` all in the same session.

## 📜 License

Multi Lyrics is free software licensed under the **GNU General Public License v3.0**.

This means you are free to:
- ✅ Use the software for any purpose
- ✅ Study and modify the source code  
- ✅ Share copies with others
- ✅ Distribute your modifications

**Important:** Any modifications or derivative works must also be licensed under GPL v3.0 and include source code.

See [LICENSE](LICENSE) for the complete license text.

### Third-Party Licenses

This project uses several open-source libraries. See [CREDITS.md](CREDITS.md) for detailed attributions and their respective licenses.

---

## 🚀 Instalación Rápida

### ¿Primera vez instalando software de código abierto?

No te preocupes, hemos creado guías paso a paso con capturas de pantalla para cada sistema operativo:

- 🪟 **Windows 10/11**: [`docs/INSTALL_WINDOWS.md`](docs/INSTALL_WINDOWS.md) ⭐ **Guía completa para principiantes**
- 🐧 **Ubuntu/Linux**: [`docs/SETUP_AUDIO_LINUX.md`](docs/SETUP_AUDIO_LINUX.md)
- 🍎 **macOS**: [`docs/SETUP_AUDIO_MACOS.md`](docs/SETUP_AUDIO_MACOS.md)

### Para usuarios con experiencia

Si ya tienes Python y FFmpeg instalados:

```bash
# Clonar repositorio
git clone <repository-url>
cd multilyrics

# Crear entorno virtual
python3 -m venv env
source env/bin/activate  # En Windows: .\env\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python main.py
```

### Development Setup

For contributors and developers who want to run tests:

```bash
# After activating virtual environment
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_engine_mixer.py -v
```

### Configuración por Sistema Operativo

Multi Lyrics funciona en Windows, Linux y macOS. Cada sistema tiene su propia configuración óptima:

#### 🪟 Windows 10/11

- **Guía de instalación completa**: [`docs/INSTALL_WINDOWS.md`](docs/INSTALL_WINDOWS.md) ⭐ **Empieza aquí**
- **Audio Backend**: WASAPI (configurado automáticamente)
- **FFmpeg**: Se instala manualmente ([guía incluida](docs/INSTALL_WINDOWS.md#paso-2-instalar-ffmpeg))

**¿Primera vez?** La guía te explica TODO paso a paso, incluyendo cómo instalar Python.

#### 🐧 Linux (Ubuntu/Mint)

- **Guía completa**: [`docs/SETUP_AUDIO_LINUX.md`](docs/SETUP_AUDIO_LINUX.md)
- **Audio optimizado**: PipeWire para menor latencia (script automático incluido)
- **Dependencias del sistema**:
  ```bash
  sudo apt install python3 python3-venv ffmpeg libportaudio2
  ```

#### 🍎 macOS

- **Guía completa**: [`docs/SETUP_AUDIO_MACOS.md`](docs/SETUP_AUDIO_MACOS.md)
- **Audio Backend**: CoreAudio (configurado automáticamente)
- **FFmpeg**: Instalar con Homebrew: `brew install ffmpeg`

---

## 📚 Documentation

- **[Development Guide](docs/development.md)** - Setup, testing, and contribution workflow
- **[Architecture](docs/architecture.md)** - Technical design and patterns
- **[Audio Setup (Linux)](docs/SETUP_AUDIO_LINUX.md)** - PipeWire/PulseAudio configuration
- **[Video Fixes (Linux)](docs/FIXES_VIDEO_LINUX.md)** - Second-screen troubleshooting
- **[Copilot Instructions](.github/copilot-instructions.md)** - AI development guidelines

---

## 🛠️ Solución de Problemas

### Problemas Comunes y Soluciones Rápidas

**❌ "Python no se reconoce como comando" (Windows)**
- **Causa**: Python no se agregó al PATH durante la instalación
- **Solución**: Reinstala Python y marca la casilla "Add Python to PATH"
- 📖 Ver: [`docs/INSTALL_WINDOWS.md`](docs/INSTALL_WINDOWS.md#paso-1-instalar-python)

**❌ "ffmpeg no se reconoce como comando"**
- **Causa**: FFmpeg no está instalado o no está en el PATH
- **Windows**: [`docs/INSTALL_WINDOWS.md#paso-2-instalar-ffmpeg`](docs/INSTALL_WINDOWS.md#paso-2-instalar-ffmpeg)
- **Linux**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`

**❌ Audio con glitches o cortes**
- **Causa**: Tu hardware puede necesitar un perfil de audio diferente
- **Solución rápida**: Prueba forzar el perfil "legacy":
  ```bash
  export MULTILYRICS_AUDIO_PROFILE="legacy"  # Linux/macOS
  # o en PowerShell: $env:MULTILYRICS_AUDIO_PROFILE="legacy"
  python main.py
  ```
- 📖 Ver perfiles disponibles: [`docs/SETUP_AUDIO_*.md`](docs/)

**❌ No se ve ninguna ventana al ejecutar `python main.py`**
- **Causa**: Dependencias no instaladas correctamente
- **Solución**:
  ```bash
  pip install -r requirements.txt --force-reinstall
  ```

**❌ Linux: Ventana de video en pantalla incorrecta**
- 📖 Ver: [`docs/FIXES_VIDEO_LINUX.md`](docs/FIXES_VIDEO_LINUX.md)

### ¿Necesitas más ayuda?

1. **Revisa la guía de instalación de tu sistema operativo** (contiene soluciones detalladas)
2. **Consulta los logs**: La aplicación muestra mensajes de error útiles en la terminal
3. **Reporta un problema**: Abre un [issue en GitHub](../../issues) con:
   - Tu sistema operativo y versión
   - El mensaje de error completo (copia y pega desde la terminal)
   - Los pasos que seguiste antes del error

---

## ❓ Preguntas Frecuentes (FAQ)

### ¿Es realmente gratis?

**Sí, 100% gratis.** Multi Lyrics es software libre bajo licencia GPL v3.0. Puedes usarlo, modificarlo y compartirlo sin costo alguno. Ver [Licencia](#-license) para más detalles.

### ¿Qué tan difícil es instalar esto?

**Para principiantes**: Sigue nuestra [guía de Windows](docs/INSTALL_WINDOWS.md) que te explica TODO paso a paso (incluso cómo instalar Python). Toma unos 20-30 minutos.

**Para usuarios con experiencia**: Si ya tienes Python y FFmpeg, solo 5 minutos con los [comandos rápidos](#para-usuarios-con-experiencia).

### ¿Funciona en mi computadora antigua?

**Probablemente sí.** Multi Lyrics está optimizado para hardware de 2008+ con 4 GB de RAM. Detecta automáticamente tu hardware y ajusta la configuración. Ver [perfiles de audio](docs/SETUP_AUDIO_WINDOWS.md#-perfiles-de-audio-disponibles).

### ¿Necesito conocimientos técnicos?

**No para usarlo.** La instalación requiere seguir instrucciones paso a paso (están bien explicadas), pero una vez instalado, la aplicación es intuitiva con interfaz gráfica.

### ¿Puedo usar esto en mi iglesia?

**¡Claro! Para eso fue diseñado.** Es gratuito y legal usarlo en servicios, conciertos y eventos. Solo recuerda que la música que reproduzcas debe tener los permisos correspondientes (CCLI, etc.).

### ¿Qué formatos de audio soporta?

**WAV y OGG Vorbis** para stems individuales. MP4 con H.264/AAC para video. Ver [Formatos Soportados](#-supported-audio-formats) para más detalles.

### ¿Dónde consigo multitracks para usar?

Multi Lyrics reproduce multitracks que ya tengas. Puedes obtenerlos de:
- Servicios legales como Multitracks.com, LoopCommunity, PraiseCharts
- Producciones propias de tu banda/iglesia

**Importante**: Respeta los derechos de autor. Solo usa música que tengas permiso de reproducir.

---

## 🤝 Contributing

Contributions are welcome! Since this project is GPL v3.0:
- All contributions must be compatible with GPL v3.0
- Please include appropriate copyright headers in new files
- Maintain code quality and follow existing patterns (PEP 8, type hints)

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for architectural guidelines.

## 🙏 Acknowledgments

Multi Lyrics is built on the shoulders of giants:
- **madmom**: Beat tracking and chord recognition
- **PySide6/Qt**: Cross-platform GUI framework
- **sounddevice/soundfile**: Real-time audio playback
- **FFmpeg**: Audio/video processing

Full credits and citations in [CREDITS.md](CREDITS.md).

## 📧 Contact

For questions, bug reports, or feature requests, please open an issue on GitHub.

---

**Made with ❤️ for the worship community**
