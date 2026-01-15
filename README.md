# Multi Lyrics 🎵

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

**Multi Lyrics** is a professional multitrack audio/video player designed specifically for worship teams and churches. It provides synchronized lyrics display, advanced audio analysis (beat detection, chord recognition), and waveform visualization - all in a free, open-source package.

## ✨ Features

- 🎛️ **Multitrack Playback**: Play individual stems (drums, bass, vocals, etc.) with independent volume control
- 📊 **Waveform Visualization**: Interactive timeline with three zoom modes (General, Playback, Edit)
- 🎼 **Audio Analysis**: Automatic beat detection and chord recognition using madmom
- 📝 **Synchronized Lyrics**: LRC format support with auto-download from online sources
- 🎥 **Video Lyrics**: Optional video playback synchronized with audio
- 🎚️ **Professional Mixer**: Per-track mute/solo, logarithmic volume curves, master gain with headroom
- 🔄 **Live Worship Optimized**: Tracks start at 90% (-6 dB) for easy bass/drums boost during service

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

## 🚀 Installation

### Ubuntu (20.04+)

## Requisitos del sistema

- Sistema: Ubuntu 20.04 o superior
- Python: 3.11 recomendado
- Paquetes del sistema necesarios:

Instala dependencias del sistema necesarias (FFmpeg, PortAudio, libsndfile, compiladores):

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg libsndfile1 libportaudio2 build-essential
```

Si usas alguna librería que compile extensiones (por ejemplo `sounddevice`, `soundfile`), puede ser necesario el paquete de desarrollo de PortAudio:

```bash
sudo apt install -y portaudio19-dev
```

## Uso del virtualenv incluido (opcional)

El repositorio puede venir con un entorno virtual dentro de la carpeta `env/`. Para usarlo:

```bash
# Desde la raíz del proyecto
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Crear un nuevo virtualenv (recomendado)

Si prefieres crear uno nuevo:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar la aplicación

Con el virtualenv activado, ejecuta:

```bash
python main.py
```

## Solución de problemas comunes

- Error relacionado con PortAudio o `sounddevice`: instala `portaudio19-dev` (ver arriba) y vuelve a instalar las dependencias del entorno.
- Error relacionado con `libsndfile`: confirma `libsndfile1` instalado.
- Si faltan paquetes en `requirements.txt`, instálalos con `pip install <paquete>` y considera actualizar `requirements.txt` con `pip freeze > requirements.txt` dentro del entorno.

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
