"""
Visual Backgrounds - Playback strategies for different video modes.

This module provides different playback strategies (full sync, loop, static frame).
"""

from video.backgrounds.base import VisualBackground
from video.backgrounds.video_lyrics_background import VideoLyricsBackground
from video.backgrounds.loop_background import VideoLoopBackground
from video.backgrounds.static_background import StaticFrameBackground
from video.backgrounds.blank_background import BlankBackground

__all__ = [
    'VisualBackground',
    'VideoLyricsBackground',
    'VideoLoopBackground',
    'StaticFrameBackground',
    'BlankBackground'
]
