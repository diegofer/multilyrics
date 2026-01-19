# Contributing to MultiLyrics

Thank you for your interest in contributing! MultiLyrics is in active pre-release development.

---

## 🧑‍💻 For Developers

### Quick Setup

**Prerequisites:**
- Python 3.11+
- FFmpeg (system-wide installation)

**Installation:**
```bash
# Clone repository
git clone <repository-url>
cd multilyrics

# Create virtual environment
python3 -m venv env
source env/bin/activate  # Linux/macOS
# or: .\env\Scripts\Activate.ps1  # Windows

# Install dependencies (including test tools)
pip install -r requirements-dev.txt

# Run application
python main.py
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_engine_mixer.py -v

# Run with coverage
pytest tests/ --cov=core --cov=models
```

### Code Quality

**Style Guidelines:**
- Follow PEP 8
- Use type hints for all functions
- Add docstrings (Google style)

**Linting:**
```bash
# Format code
black .

# Check types
mypy core/ models/
```

### Architecture Guidelines

**Critical Documentation:**
- **[copilot-instructions.md](.github/copilot-instructions.md)** - Complete technical guide
  - Audio callback rules (CRITICAL - read before touching audio code)
  - Component responsibilities
  - Design patterns and anti-patterns
  - Memory architecture
  
- **[PROJECT_BLUEPRINT.md](.github/PROJECT_BLUEPRINT.md)** - Executive summary
- **[ROADMAP_FEATURES.md](.github/ROADMAP_FEATURES.md)** - Future features to implement

**Audio Callback Rules (CRITICAL):**

⚠️ **NEVER do this in audio callback:**
- ❌ Locks, mutexes, semaphores
- ❌ File I/O (read/write)
- ❌ Print or logging
- ❌ Qt Signal emissions
- ❌ Memory allocation

✅ **Only do this:**
- NumPy operations on pre-loaded arrays
- Basic arithmetic
- Read atomic variables

See [copilot-instructions.md](.github/copilot-instructions.md#audio-engine-callback-rules-critical) for complete rules.

### Pull Request Process

1. **Branch naming:** `feature/your-feature-name` or `fix/issue-description`
2. **Commits:** Use conventional commits format:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation
   - `test:` add/update tests
   - `refactor:` code refactoring
3. **Tests:** Add tests for new features
4. **Syntax:** Verify with `python -m py_compile <file>`
5. **Documentation:** Update relevant docs if needed

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# ... edit code ...

# 3. Verify syntax
python -m py_compile <modified_files>

# 4. Run tests
pytest tests/

# 5. Commit
git add .
git commit -m "feat: add my awesome feature"

# 6. Push and create PR
git push origin feature/my-feature
```

---

## 🧪 For Testers

### Testing Focus Areas

**Audio Stability:**
- [ ] Playback stable for 5+ minutes without glitches
- [ ] No xruns (check Audio Monitor in Settings)
- [ ] Volume changes smooth without clicks
- [ ] Solo/mute works correctly

**UI Responsiveness:**
- [ ] Waveform syncs perfectly with audio
- [ ] Timeline zoom modes work (General, Playback, Edit)
- [ ] Lyrics display updates smoothly
- [ ] Video window shows/hides correctly

**Edge Cases:**
- [ ] Load songs with missing metadata
- [ ] Switch songs during playback
- [ ] Seek to different positions
- [ ] Test on legacy hardware (2008-2012)

### Reporting Bugs

**Include in your report:**
1. **System Info:**
   - OS: Windows/Linux/macOS + version
   - CPU: Model and year (e.g., "Intel i5-8400, 2018")
   - RAM: Total amount (e.g., "16 GB")
   - Python version: `python --version`

2. **Audio Stats:**
   - Open Settings → Enable "Show Latency Monitor"
   - Include screenshot or copy:
     - Latency (avg/peak)
     - Xruns count
     - CPU usage

3. **Logs:**
   - Copy terminal output (especially lines with `ERROR` or `WARNING`)
   - Attach `multilyrics.log` if it exists

4. **Steps to Reproduce:**
   - Detailed steps that trigger the bug
   - Sample files if needed (link to multi/video)

**Submit at:** [GitHub Issues](https://github.com/your-org/multilyrics/issues)

### Known Issues

See [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for current known bugs and workarounds.

---

## 📜 License

By contributing, you agree that your contributions will be licensed under **GNU GPLv3**.

- All new files must include GPL header
- Use existing files as template
- Contributions must be compatible with GPLv3

---

## 🙏 Questions?

- **Technical questions:** See [copilot-instructions.md](.github/copilot-instructions.md)
- **Architecture decisions:** See [IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md)
- **General questions:** Open a [GitHub Discussion](https://github.com/your-org/multilyrics/discussions)

---

**Thank you for contributing to MultiLyrics!** 🎵
