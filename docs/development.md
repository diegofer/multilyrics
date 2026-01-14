# Development Guide

> **Note**: This document is a work in progress. It will be expanded with comprehensive development workflows and guidelines.

## Getting Started

### Prerequisites
- Python 3.11+
- FFmpeg (system-wide installation)
- Windows 10/11 (primary platform)

### Environment Setup

```powershell
# Clone repository
git clone <repository-url>
cd multi_lyrics

# Create virtual environment
python -m venv env
.\env\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```powershell
python main.py
```

## Development Workflow

### Testing

```powershell
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_timeline_model.py -v

# Run with coverage
pytest --cov=. tests/
```

### UI Development

Qt Designer files (`.ui`) are in `ui/`. After editing:

```powershell
pyside6-uic ui/main_window.ui -o ui/main_window.py
```

**Important**: Never edit generated `.py` files directly.

### Code Style

- Follow PEP 8
- Use type hints
- Google Style docstrings
- Maximum line length: 100 characters

## Project Conventions

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Qt Signals: `camelCase`
- Callbacks: `_on_event_name`

### Imports
- Standard library first
- Third-party libraries
- Local imports last
- Absolute imports preferred

### Coordinate Systems
- Audio: samples (int)
- Time: seconds (float)
- UI: pixels (int)

## Future Sections

- Debugging tips
- Performance profiling
- Adding new audio analysis features
- Contributing guidelines
- Release process
