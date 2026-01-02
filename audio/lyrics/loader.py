"""LyricsLoader service for loading and parsing synchronized lyrics.

Implements a strict loading order:
1. Check for local lyrics.lrc file
2. Query LRCLIB API if not found
3. Filter results by duration
4. Download and save synchronized lyrics
"""

import re
import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Optional

from .model import LyricsModel, LyricLine


class LyricsLoader:
    """Service for loading synchronized lyrics from local files or LRCLIB API."""
    
    # LRCLIB API configuration
    LRCLIB_BASE_URL = "https://lrclib.net"
    DURATION_TOLERANCE_SECONDS = 2.0
    
    def load(self, song_folder: Path, metadata: dict) -> Optional[LyricsModel]:
        """Load lyrics following the strict loading order.
        
        Args:
            song_folder: Path to the folder containing the song
            metadata: Dictionary with keys: 'track_name', 'artist_name', 'duration_seconds'
            
        Returns:
            LyricsModel if lyrics were found, None otherwise
        """
        # Step 1: Try local file
        model = self.load_from_local(song_folder)
        if model:
            return model
        
        # Step 2: Try LRCLIB API
        track_name = metadata.get('track_name')
        artist_name = metadata.get('artist_name')
        duration = metadata.get('duration_seconds')
        
        if not track_name or not artist_name:
            return None
        
        try:
            results = self.search_lrclib(track_name, artist_name)
            
            if not results:
                return None
            
            # Step 3: Filter by duration if available
            best_match = None
            if duration is not None:
                best_match = self.select_best_match(results, duration)
            else:
                # No duration filtering possible, take first result with synced lyrics
                for result in results:
                    if result.get('syncedLyrics'):
                        best_match = result
                        break
            
            if not best_match:
                return None
            
            # Step 4: Download synchronized lyrics
            lrc_text = self.download_synced_lyrics(best_match)
            if not lrc_text:
                return None
            
            # Step 5: Save locally
            self.save_lrc(lrc_text, song_folder)
            
            # Step 6: Parse and return
            return self.parse_lrc(lrc_text)
            
        except Exception:
            # Network failures fail gracefully
            return None
    
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
    
    def search_lrclib(self, track_name: str, artist_name: str) -> list[dict]:
        """Search LRCLIB API for lyrics.
        
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
    
    def select_best_match(self, results: list[dict], duration_seconds: float) -> Optional[dict]:
        """Select the best matching result based on duration.
        
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
    
    def download_synced_lyrics(self, result: dict) -> Optional[str]:
        """Extract synchronized lyrics content from a result.
        
        Args:
            result: A single search result dictionary from LRCLIB
            
        Returns:
            LRC text content, or None if not available
        """
        synced_lyrics = result.get('syncedLyrics')
        return synced_lyrics if synced_lyrics else None
    
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


