# Credits and Third-Party Licenses

Multi Lyrics uses the following open-source libraries and tools. We are grateful to their maintainers and contributors.

## Core Dependencies

### PySide6 (Qt for Python)
- **License**: LGPL v3
- **Website**: https://www.qt.io/qt-for-python
- **Usage**: GUI framework for the entire application interface
- **Copyright**: The Qt Company Ltd.

### madmom
- **License**: BSD 3-Clause
- **Repository**: https://github.com/CPJKU/madmom
- **Usage**: Audio signal processing for beat detection and chord recognition
- **Copyright**: Department of Computational Perception, Johannes Kepler University, Linz, Austria

### python-vlc
- **License**: LGPL v2.1+
- **Repository**: https://github.com/oaubert/python-vlc
- **Usage**: Video playback integration
- **Copyright**: Olivier Aubert and contributors

### sounddevice
- **License**: MIT
- **Repository**: https://github.com/spatialaudio/python-sounddevice
- **Usage**: Real-time audio playback with low latency
- **Copyright**: Matthias Geier

### soundfile
- **License**: BSD 3-Clause
- **Repository**: https://github.com/bastibe/python-soundfile
- **Usage**: Audio file I/O operations
- **Copyright**: Bastian Bechtold

### NumPy
- **License**: BSD 3-Clause
- **Repository**: https://github.com/numpy/numpy
- **Usage**: Numerical computing and array operations
- **Copyright**: NumPy Developers

### SciPy
- **License**: BSD 3-Clause
- **Repository**: https://github.com/scipy/scipy
- **Usage**: Scientific computing and signal processing
- **Copyright**: SciPy Developers

## External Tools

### FFmpeg
- **License**: LGPL v2.1+ / GPL v2+ (depending on configuration)
- **Website**: https://ffmpeg.org/
- **Usage**: Audio extraction from video files
- **Copyright**: FFmpeg team
- **Note**: FFmpeg is not distributed with Multi Lyrics. Users must install it separately.

### ffmpeg-python
- **License**: Apache License 2.0
- **Repository**: https://github.com/kkroening/ffmpeg-python
- **Usage**: Python wrapper for FFmpeg
- **Copyright**: Karl Kroening

## Lyrics Providers

### LRCLib API
- **Website**: https://lrclib.net/
- **Usage**: Synchronized lyrics search and download
- **Note**: Public API used under fair use terms

### NetEase Cloud Music API
- **Usage**: Alternative lyrics source
- **Note**: Used for educational purposes only

## Development Tools

### pytest
- **License**: MIT
- **Repository**: https://github.com/pytest-dev/pytest
- **Usage**: Testing framework

### pytest-qt
- **License**: MIT
- **Repository**: https://github.com/pytest-dev/pytest-qt
- **Usage**: Qt testing utilities

## Fonts

All fonts included in `assets/fonts/` are either:
- Licensed under SIL Open Font License (OFL)
- Public Domain
- Distributed with proper attribution in their respective directories

## Icons

### Iconoir
- **License**: MIT
- **Repository**: https://github.com/iconoir-icons/iconoir
- **Website**: https://iconoir.com/
- **Usage**: SVG icons throughout the application UI
- **Copyright**: Iconoir contributors
- **Note**: Icons are used under the MIT License which permits commercial and non-commercial use

## GPL Compliance

Multi Lyrics respects all GPL and LGPL requirements:
- Source code is available at the project repository
- All modifications to GPL/LGPL libraries are documented
- No proprietary forks of GPL/LGPL code are included
- Dynamic linking is used where permitted by LGPL

## Acknowledgments

Special thanks to:
- The Qt/PySide6 team for excellent Python bindings
- CPJKU for the powerful madmom audio analysis library
- All open-source contributors who make projects like this possible

---

**Last Updated**: January 2026

If you believe any attribution is missing or incorrect, please open an issue at the project repository.
