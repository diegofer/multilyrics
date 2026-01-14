# Multi Lyrics Architecture

> **Note**: This document is a work in progress. It will be expanded with detailed architectural diagrams and component descriptions.

## Overview

Multi Lyrics follows a modular architecture with clear separation of concerns:

- **models/**: Data models and business logic entities
- **core/**: Application core (playback, sync, orchestration)
- **audio/**: Audio processing (extraction, analysis, playback)
- **video/**: Video playback integration
- **ui/**: User interface components (Qt widgets, styles)
- **utils/**: Cross-cutting utilities (logging, error handling, helpers)

## Core Principles

### Single Source of Truth
`TimelineModel` is the canonical source for playhead time. All UI components observe this model directly.

### Observer Pattern
Non-Qt components use callbacks instead of signals for loose coupling and testability.

### Track-Based Rendering
Timeline visualization uses a modular track system where each renderer (waveform, beats, chords, lyrics) paints independently.

## Key Components

### TimelineModel
Central state container for beats, chords, lyrics, and playhead position.

### PlaybackManager
Coordinates audio/video players and propagates time updates.

### SyncController
Handles audio-video synchronization with smooth interpolation.

### TimelineView
Custom QWidget with three zoom modes (GENERAL, PLAYBACK, EDIT).

## Data Flow

```
Audio Playback (sounddevice)
  → SyncController.audio_callback()
  → PlaybackManager._on_audio_time()
  → TimelineModel.set_playhead_time()
  → Observers notified (TimelineView, controls, etc.)
```

## Future Sections

- Component interaction diagrams
- Class hierarchy
- Threading model
- Error handling strategy
- Testing architecture
