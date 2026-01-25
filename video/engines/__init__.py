"""
Video Engines - Backend abstraction for video playback.

This module provides a unified interface for different video backends (VLC, mpv).
"""

from video.engines.base import VisualEngine
from video.engines.vlc_engine import VlcEngine
from video.engines.mpv_engine import MpvEngine

__all__ = ['VisualEngine', 'VlcEngine', 'MpvEngine']
