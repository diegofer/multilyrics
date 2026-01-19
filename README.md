# MultiLyrics 🎵

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Professional multitrack audio/video player designed for worship teams and churches. Features synchronized lyrics, beat detection, chord recognition, and waveform visualization.

## 🚧 Status: Pre-Release (Active Development)

**This project is in active development.** Installers for Windows/Mac/Linux coming soon.

- 🧪 **For Testers:** Download latest builds from [Releases](../../releases)
- 🧑‍💻 **For Developers:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- 📖 **Documentation:** [.github/copilot-instructions.md](.github/copilot-instructions.md)

---

## ✨ Key Features

- 🎛️ **Multitrack Playback**: Independent stems (drums, bass, vocals, etc.) with per-track volume control
- 📊 **Waveform Timeline**: Three zoom modes (General, Playback, Edit) with interactive seeking
- 🎼 **Auto Analysis**: Beat detection and chord recognition (madmom)
- 📝 **Synchronized Lyrics**: LRC format with auto-download
- 🎥 **Video Support**: MP4 video lyrics synchronized with audio
- 🎚️ **Professional Mixer**: Solo/mute, logarithmic volume, master gain
- 🖥️ **Legacy Hardware**: Optimized for 2008+ CPUs with 4GB RAM
- 🎵 **Audio Formats**: WAV, OGG Vorbis

## 💻 System Requirements

**Minimum:**
- Windows 10+, macOS 10.13+, or Linux (Ubuntu 20.04+)
- CPU: 2008 or newer (Core 2 Duo equivalent)
- RAM: 4 GB (8 GB recommended)
- Storage: 500 MB free space

**Audio Formats:**
- Stems: WAV, OGG Vorbis
- Master: WAV (for timeline waveform)
- Video: MP4 (H.264/AAC)

## 📜 License

**GNU General Public License v3.0** - Free and open source.

You can use, modify, and distribute this software freely. See [LICENSE](LICENSE) for details.

Third-party attributions: [CREDITS.md](CREDITS.md)

---

## 🚀 Quick Start

### For Developers

```bash
git clone <repository-url>
cd multilyrics
python3 -m venv env
source env/bin/activate  # Windows: .\env\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python main.py
```

**Full setup guide:** [CONTRIBUTING.md](CONTRIBUTING.md)

### For Testers

Wait for installer releases (coming soon) or follow developer setup above.

### Audio Profiles

MultiLyrics **auto-detects your hardware** and configures audio automatically:

- **Legacy** (2008-2012): 4GB RAM, ~85ms latency
- **Balanced** (2013-2018): 8GB RAM, ~43ms latency ⭐ Most users
- **Modern** (2019+): 16GB RAM, ~21ms latency

**Troubleshooting:** See platform guides in [`docs/`](docs/)

---

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Developer setup and testing guide
- **[Copilot Instructions](.github/copilot-instructions.md)** - AI development guidelines
- **[Project Blueprint](.github/PROJECT_BLUEPRINT.md)** - Architecture overview
- **[Feature Roadmap](.github/ROADMAP_FEATURES.md)** - Planned features
- **[Implementation Log](docs/IMPLEMENTATION_ROADMAP.md)** - Completed optimizations

---

## 🛠️ Troubleshooting

**Audio glitches:**
```bash
export MULTILYRICS_AUDIO_PROFILE="legacy"  # Try legacy profile
```

**Missing dependencies:**
```bash
pip install -r requirements.txt --force-reinstall
```

**Platform-specific issues:** See [`docs/SETUP_AUDIO_*.md`](docs/)

**Report bugs:** [GitHub Issues](../../issues) - Include OS, Python version, and error logs

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Quick setup guide
- Testing checklist
- Code style guidelines
- Audio callback rules (CRITICAL)

This project is GPL v3.0 - all contributions must be compatible.

## 🙏 Acknowledgments

Built with:
- **madmom** - Beat tracking and chord recognition
- **PySide6/Qt** - Cross-platform GUI
- **sounddevice/soundfile** - Real-time audio
- **FFmpeg** - Audio/video processing

Full credits: [CREDITS.md](CREDITS.md)

---

**Made with ❤️ for the worship community**
