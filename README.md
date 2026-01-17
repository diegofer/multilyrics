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

## 🚀 Quick Start

### Prerequisites

- **Python:** 3.11+ (recommended)
- **FFmpeg:** System-wide installation required
- **Operating System:** Windows 10/11, Ubuntu 20.04+, macOS 10.13+

### Basic Installation

```bash
# Clone repository
git clone <repository-url>
cd multilyrics

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Platform-Specific Setup

Different platforms require additional configuration for optimal performance:

#### 🐧 Linux

**Audio optimization (Ubuntu 22.04+):**
```bash
# Install PipeWire for better latency
chmod +x scripts/setup_pipewire_ubuntu.sh
./scripts/setup_pipewire_ubuntu.sh
# Restart system after installation
```

**System dependencies:**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
    ffmpeg libsndfile1 libportaudio2 portaudio19-dev build-essential
```

📖 **Full guide:** [`docs/SETUP_AUDIO_LINUX.md`](docs/SETUP_AUDIO_LINUX.md)

#### 🪟 Windows

- **Audio Backend:** WASAPI (auto-detected, no configuration needed)
- **FFmpeg:** Download from [ffmpeg.org](https://ffmpeg.org/) and add to PATH

📖 **Full guide:** `docs/SETUP_AUDIO_WINDOWS.md` *(coming soon)*

#### 🍎 macOS

- **Audio Backend:** CoreAudio (auto-detected, no configuration needed)
- **FFmpeg:** Install via Homebrew: `brew install ffmpeg`

📖 **Full guide:** `docs/SETUP_AUDIO_MACOS.md` *(coming soon)*

---

## 📚 Documentation

- **[Development Guide](docs/development.md)** - Setup, testing, and contribution workflow
- **[Architecture](docs/architecture.md)** - Technical design and patterns
- **[Audio Setup (Linux)](docs/SETUP_AUDIO_LINUX.md)** - PipeWire/PulseAudio configuration
- **[Video Fixes (Linux)](docs/FIXES_VIDEO_LINUX.md)** - Second-screen troubleshooting
- **[Copilot Instructions](.github/copilot-instructions.md)** - AI development guidelines

---

## 🛠️ Troubleshooting

### Common Issues

**Linux: No audio output**
→ Check `pactl info | grep "Server Name"` - may need PipeWire setup

**Linux: Video window on wrong screen**
→ See [`docs/FIXES_VIDEO_LINUX.md`](docs/FIXES_VIDEO_LINUX.md)

**All platforms: Audio glitches on old hardware**
→ Increase buffer size in `core/constants.py` → `AUDIO_BLOCKSIZE = 2048`

**Missing dependencies**
→ Reinstall: `pip install -r requirements.txt --force-reinstall`

For detailed troubleshooting, see platform-specific guides in `docs/`.

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
