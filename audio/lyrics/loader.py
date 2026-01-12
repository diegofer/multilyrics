"""LyricsLoader service for loading and parsing synchronized lyrics.

Provides modular API for lyrics operations:
- load(): High-level method with automatic fallback (local → API → filter → save)
- search_all(): Search API without duration filtering (for manual selection)
- auto_download(): Automatic download with duration filtering
- download_and_save(): Download specific result and save locally
- load_from_local(): Load from existing lyrics.lrc file
"""

import re
import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Optional

from .model import LyricsModel, LyricLine


class LyricsLoader:
    """Service for loading synchronized lyrics from local files or LRCLIB API.
    
    Architecture:
    - Public API methods: load(), search_all(), auto_download(), download_and_save()
    - Private helper methods: _search_lrclib_api(), _select_best_match(), _save_lrc()
    """
    
    # LRCLIB API configuration
    LRCLIB_BASE_URL = "https://lrclib.net"
    DURATION_TOLERANCE_SECONDS = 1.0
    
    # === METADATA NORMALIZATION ===
    
    @staticmethod
    def _normalize_metadata(metadata: dict) -> tuple[str, str, float]:
        """Normalize metadata keys from legacy to new format.
        
        Supports both new format (track_name, artist_name, duration_seconds)
        and legacy format (title, artist, duration) with fallback chain.
        
        Args:
            metadata: Dictionary with metadata in any supported format
            
        Returns:
            Tuple of (track_name, artist_name, duration_seconds)
            Returns empty strings and 0.0 for missing values
            
        Examples:
            >>> # New format
            >>> _normalize_metadata({'track_name': 'Song', 'artist_name': 'Artist', 'duration_seconds': 180.5})
            ('Song', 'Artist', 180.5)
            
            >>> # Legacy format
            >>> _normalize_metadata({'title': 'Old Song', 'artist': 'Old Artist', 'duration': 200.0})
            ('Old Song', 'Old Artist', 200.0)
            
            >>> # Mixed/partial
            >>> _normalize_metadata({'track_name': 'New', 'artist': 'Old'})
            ('New', 'Old', 0.0)
        """
        track_name = metadata.get('track_name') or metadata.get('title') or ''
        artist_name = metadata.get('artist_name') or metadata.get('artist') or ''
        duration = metadata.get('duration_seconds') or metadata.get('duration') or 0.0
        
        return track_name, artist_name, float(duration)
    
    # === HIGH-LEVEL API (Public Methods) ===
    
    def load(self, song_folder: Path, metadata: dict) -> Optional[LyricsModel]:
        """Load lyrics with automatic fallback: local file → API search → save.
        
        This is a convenience method that combines local loading and auto-download.
        For more control, use load_from_local() or auto_download() directly.
        
        Args:
            song_folder: Path to the folder containing the song
            metadata: Dictionary with keys: 'track_name', 'artist_name', 'duration_seconds'
                     Also supports legacy keys: 'title', 'artist', 'duration'
            
        Returns:
            LyricsModel if lyrics were found, None otherwise
        """
        # Step 1: Try local file first
        model = self.load_from_local(song_folder)
        if model:
            return model
        
        # Step 2: Try auto-download from API
        # Normalize metadata keys (support both new and legacy formats)
        track_name, artist_name, duration = self._normalize_metadata(metadata)
        
        return self.auto_download(song_folder, track_name, artist_name, duration)
    
    def search_all(self, track_name: str, artist_name: str) -> list[dict]:
        """Search all lyrics without duration filtering.
        
        Returns only results with synchronized lyrics.
        Useful for manual selection by user when auto-download fails.
        
        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            
        Returns:
            List of results with syncedLyrics, empty list if none found
        """
        results = self._search_lrclib_api(track_name, artist_name)
        return [r for r in results if r.get('syncedLyrics')]
    
    def auto_download(self, song_folder: Path, track_name: str, 
                     artist_name: str, duration_seconds: float = None) -> Optional[LyricsModel]:
        """Automatically download and save best matching lyrics.
        
        Filters by duration tolerance if provided, otherwise selects first result
        with synchronized lyrics. Saves to lyrics.lrc automatically.
        
        Args:
            song_folder: Path to save lyrics.lrc
            track_name: Name of the track
            artist_name: Name of the artist
            duration_seconds: Optional duration for filtering (uses DURATION_TOLERANCE_SECONDS)
            
        Returns:
            LyricsModel if successful, None if no suitable match found
        """
        if not track_name or not artist_name:
            return None
        
        try:
            results = self._search_lrclib_api(track_name, artist_name)
            if not results:
                return None
            
            # Select best match
            best_match = None
            if duration_seconds is not None:
                best_match = self._select_best_match(results, duration_seconds)
            else:
                # No duration filtering, take first result with synced lyrics
                for result in results:
                    if result.get('syncedLyrics'):
                        best_match = result
                        break
            
            if not best_match:
                return None
            
            # Download and save
            return self.download_and_save(best_match, song_folder)
            
        except Exception:
            # Network failures fail gracefully
            return None
    
    def download_and_save(self, result: dict, song_folder: Path) -> Optional[LyricsModel]:
        """Download and save a specific result.
        
        Use this after manual selection from search_all() results.
        
        Args:
            result: A single search result dictionary from LRCLIB
            song_folder: Path to save lyrics.lrc
            
        Returns:
            LyricsModel if successful, None if result has no syncedLyrics
        """
        lrc_text = result.get('syncedLyrics')
        if not lrc_text:
            return None
        
        self._save_lrc(lrc_text, song_folder)
        return self.parse_lrc(lrc_text)
    
    # === FILE I/O ===
    
    # === FILE I/O ===
    
    def load_from_local(self, song_folder: Path) -> Optional[LyricsModel]:
        """Load lyrics from local lyrics.lrc file.
        
        Args:
            song_folder: Path to the folder containing the song
            
        Returns:
            LyricsModel if file exists and is valid, None otherwise
        """
        lrc_path = song_folder / "lyrics.lrc"
        
        if not lrc_path.exists():
            return None
        
        try:
            text = lrc_path.read_text(encoding='utf-8')
            return self.parse_lrc(text)
        except Exception:
            return None
    
    # === LRCLIB API ACCESS (Internal) ===
    
    def _search_lrclib_api(self, track_name: str, artist_name: str) -> list[dict]:
        """Search LRCLIB API for lyrics (internal method).
        
        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            
        Returns:
            List of result dictionaries from the API
        """
        params = urllib.parse.urlencode({
            'track_name': track_name,
            'artist_name': artist_name
        })
        url = f"{self.LRCLIB_BASE_URL}/api/search?{params}"
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data if isinstance(data, list) else []
        except Exception:
            return []
    
    def _select_best_match(self, results: list[dict], duration_seconds: float) -> Optional[dict]:
        """Select the best matching result based on duration (internal method).
        
        Filters results by duration tolerance and prefers synchronized lyrics.
        
        Args:
            results: List of search results from LRCLIB
            duration_seconds: Duration of the local song in seconds
            
        Returns:
            Best matching result, or None if no suitable match found
        """
        candidates = []
        
        for result in results:
            # Skip results without synchronized lyrics
            if not result.get('syncedLyrics'):
                continue
            
            result_duration = result.get('duration')
            if result_duration is None:
                continue
            
            # Calculate duration difference
            duration_diff = abs(result_duration - duration_seconds)
            
            # Only consider results within tolerance
            if duration_diff <= self.DURATION_TOLERANCE_SECONDS:
                candidates.append((duration_diff, result))
        
        if not candidates:
            return None
        
        # Return the result with the smallest duration difference
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    def _save_lrc(self, text: str, song_folder: Path) -> None:
        """Save LRC text to lyrics.lrc in the song folder (internal method).
        
        Args:
            text: LRC format text content
            song_folder: Path to the folder containing the song
        """
        lrc_path = song_folder / "lyrics.lrc"
        
        try:
            # Ensure the folder exists
            song_folder.mkdir(parents=True, exist_ok=True)
            lrc_path.write_text(text, encoding='utf-8')
        except Exception:
            # Fail gracefully if save fails
            pass
    
    # === LEGACY API (Deprecated, maintained for backward compatibility) ===
    
    def search_lrclib(self, track_name: str, artist_name: str) -> list[dict]:
        """Search LRCLIB API for lyrics.
        
        DEPRECATED: Use search_all() or _search_lrclib_api() instead.
        Maintained for backward compatibility.
        
        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            
        Returns:
            List of result dictionaries from the API
        """
        return self._search_lrclib_api(track_name, artist_name)
    
    def select_best_match(self, results: list[dict], duration_seconds: float) -> Optional[dict]:
        """Select the best matching result based on duration.
        
        DEPRECATED: Use _select_best_match() instead.
        Maintained for backward compatibility.
        
        Args:
            results: List of search results from LRCLIB
            duration_seconds: Duration of the local song in seconds
            
        Returns:
            Best matching result, or None if no suitable match found
        """
        return self._select_best_match(results, duration_seconds)
    
    def download_synced_lyrics(self, result: dict) -> Optional[str]:
        """Extract synchronized lyrics content from a result.
        
        DEPRECATED: Use download_and_save() instead.
        Maintained for backward compatibility.
        
        Args:
            result: A single search result dictionary from LRCLIB
            
        Returns:
            LRC text content, or None if not available
        """
        synced_lyrics = result.get('syncedLyrics')
        return synced_lyrics if synced_lyrics else None
    
    def save_lrc(self, text: str, song_folder: Path) -> None:
        """Save LRC text to lyrics.lrc in the song folder.
        
        DEPRECATED: Use _save_lrc() instead.
        Maintained for backward compatibility.
        
        Args:
            text: LRC format text content
            song_folder: Path to the folder containing the song
        """
        self._save_lrc(text, song_folder)
    
    # === PARSING ===
    
    # === PARSING ===
    
    def parse_lrc(self, text: str) -> LyricsModel:
        """Parse LRC format text into a LyricsModel.
        
        Supports:
        - Multiple timestamps per line: [00:12.00][00:17.20]Repeated line
        - Metadata tags (ignored): [ar:], [ti:], [al:], etc.
        - Standard format: [mm:ss.xx]Lyric text
        
        Args:
            text: LRC format text content
            
        Returns:
            LyricsModel with parsed and sorted lyric lines
        """
        lines = []
        
        # Pattern to match LRC timestamps: [mm:ss.xx] or [mm:ss]
        timestamp_pattern = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\]')
        
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Find all timestamps in the line
            timestamps = timestamp_pattern.findall(line)
            
            if not timestamps:
                continue
            
            # Remove all timestamps to get the lyric text
            lyric_text = timestamp_pattern.sub('', line).strip()
            
            # Skip metadata tags
            if lyric_text.startswith('[') and ':' in lyric_text and lyric_text.endswith(']'):
                continue
            
            # Convert each timestamp to seconds and create a LyricLine
            for minutes, seconds in timestamps:
                time_seconds = int(minutes) * 60 + float(seconds)
                lines.append(LyricLine(time_s=time_seconds, text=lyric_text))
        
        # Sort by time
        lines.sort(key=lambda l: l.time_s)
        
        return LyricsModel(lines)
    
    def save_lrc(self, text: str, song_folder: Path) -> None:
        """Save LRC text to lyrics.lrc in the song folder.
        
        Args:
            text: LRC format text content
            song_folder: Path to the folder containing the song
        """
        lrc_path = song_folder / "lyrics.lrc"
        
        try:
            # Ensure the folder exists
            song_folder.mkdir(parents=True, exist_ok=True)
            lrc_path.write_text(text, encoding='utf-8')
        except Exception:
            # Fail gracefully if save fails
            pass


