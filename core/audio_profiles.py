"""
Multi Lyrics - Audio Profile System
Copyright (C) 2026 Diego Fernando

Auto-detects hardware capabilities and loads appropriate audio configuration profile.
Profiles are stored in config/profiles/{os}/{profile_name}.json

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AudioProfile:
    """Audio configuration profile for specific hardware."""
    
    name: str
    description: str
    
    # Audio settings
    blocksize: int
    samplerate: Optional[int]
    gc_policy: str
    latency_mode: str
    prime_buffers: bool
    
    # Performance targets
    target_latency_ms: float
    xrun_tolerance: int
    cpu_threshold_pct: int
    
    # Target hardware specs (for auto-detection)
    cpu_year_min: int
    cpu_year_max: int
    ram_min_gb: int
    cores_min: int
    
    # Optional fields
    notes: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, profile_path: Path) -> 'AudioProfile':
        """Load profile from JSON file."""
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract nested fields
        audio_settings = data.get('audio_settings', {})
        performance = data.get('performance', {})
        target_hw = data.get('target_hardware', {})
        
        return cls(
            name=data.get('name', 'Unknown'),
            description=data.get('description', ''),
            blocksize=audio_settings.get('blocksize', 2048),
            samplerate=audio_settings.get('samplerate'),
            gc_policy=audio_settings.get('gc_policy', 'disable_during_playback'),
            latency_mode=audio_settings.get('latency_mode', 'high'),
            prime_buffers=audio_settings.get('prime_buffers', True),
            target_latency_ms=performance.get('target_latency_ms', 43.0),
            xrun_tolerance=performance.get('xrun_tolerance', 3),
            cpu_threshold_pct=performance.get('cpu_threshold_pct', 70),
            cpu_year_min=target_hw.get('cpu_year_min', 2008),
            cpu_year_max=target_hw.get('cpu_year_max', 2030),
            ram_min_gb=target_hw.get('ram_min_gb', 4),
            cores_min=target_hw.get('cores_min', 2),
            notes=data.get('notes', ''),
            requirements=data.get('requirements', {})
        )
    
    def to_engine_kwargs(self) -> Dict[str, Any]:
        """Convert profile to MultiTrackPlayer constructor kwargs."""
        return {
            'samplerate': self.samplerate,
            'blocksize': self.blocksize,
            'gc_policy': self.gc_policy
        }


class AudioProfileManager:
    """Manages audio profiles and hardware auto-detection."""
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Initialize profile manager.
        
        Args:
            profiles_dir: Path to profiles directory. If None, uses default.
        """
        if profiles_dir is None:
            # Default: config/profiles/ in project root
            self.profiles_dir = Path(__file__).parent.parent / 'config' / 'profiles'
        else:
            self.profiles_dir = Path(profiles_dir)
        
        self._profiles_cache: Dict[str, AudioProfile] = {}
        self._detected_os = self._detect_os()
        logger.info(f"🖥️  Detected OS: {self._detected_os}")
    
    def _detect_os(self) -> str:
        """Detect operating system."""
        system = platform.system().lower()
        if system == 'linux':
            return 'linux'
        elif system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        else:
            logger.warning(f"⚠️  Unknown OS: {system}, defaulting to linux")
            return 'linux'
    
    def _detect_hardware_year(self) -> int:
        """
        Estimate CPU year based on available information.
        This is a heuristic - not 100% accurate.
        """
        # Try to get CPU info from platform
        cpu_info = platform.processor()
        
        # Heuristic: newer Python versions typically run on newer hardware
        python_version = sys.version_info
        if python_version >= (3, 11):
            base_year = 2018  # Python 3.11 released 2022, likely 2018+ CPU
        elif python_version >= (3, 9):
            base_year = 2015  # Python 3.9 released 2020
        elif python_version >= (3, 7):
            base_year = 2012  # Python 3.7 released 2018
        else:
            base_year = 2010  # Older Python
        
        # Adjust based on CPU cores if psutil available
        if PSUTIL_AVAILABLE:
            cores = psutil.cpu_count(logical=False)
            if cores >= 16:
                return max(base_year, 2020)  # High core count = modern
            elif cores >= 8:
                return max(base_year, 2017)
            elif cores >= 4:
                return max(base_year, 2013)
            else:
                return base_year  # 2 cores = likely legacy
        
        return base_year
    
    def _detect_hardware_specs(self) -> Dict[str, Any]:
        """Detect current hardware specifications."""
        specs = {
            'cpu_year': self._detect_hardware_year(),
            'ram_gb': 8,  # Default fallback
            'cores': 2,   # Default fallback
            'os': self._detected_os
        }
        
        if PSUTIL_AVAILABLE:
            specs['ram_gb'] = round(psutil.virtual_memory().total / (1024**3))
            specs['cores'] = psutil.cpu_count(logical=False) or 2
        
        logger.info(f"💻 Detected hardware: ~{specs['cpu_year']} CPU, "
                   f"{specs['ram_gb']} GB RAM, {specs['cores']} cores")
        
        return specs
    
    def list_profiles(self, os_name: Optional[str] = None) -> list[str]:
        """List available profiles for an OS."""
        if os_name is None:
            os_name = self._detected_os
        
        profile_dir = self.profiles_dir / os_name
        if not profile_dir.exists():
            logger.warning(f"⚠️  No profiles found for {os_name}")
            return []
        
        profiles = []
        for json_file in profile_dir.glob('*.json'):
            profiles.append(json_file.stem)
        
        return sorted(profiles)
    
    def load_profile(self, profile_name: str, os_name: Optional[str] = None) -> Optional[AudioProfile]:
        """Load a specific profile by name."""
        if os_name is None:
            os_name = self._detected_os
        
        cache_key = f"{os_name}/{profile_name}"
        if cache_key in self._profiles_cache:
            return self._profiles_cache[cache_key]
        
        profile_path = self.profiles_dir / os_name / f"{profile_name}.json"
        if not profile_path.exists():
            logger.error(f"❌ Profile not found: {profile_path}")
            return None
        
        try:
            profile = AudioProfile.from_json(profile_path)
            self._profiles_cache[cache_key] = profile
            logger.info(f"✅ Loaded profile: {profile.name}")
            return profile
        except Exception as e:
            logger.error(f"❌ Failed to load profile {profile_path}: {e}")
            return None
    
    def auto_select_profile(self, override_name: Optional[str] = None) -> AudioProfile:
        """
        Auto-select best profile for current hardware.
        
        Args:
            override_name: If provided, load this profile instead of auto-detecting
            
        Returns:
            AudioProfile instance (falls back to 'balanced' if auto-detect fails)
        """
        # Manual override
        if override_name:
            profile = self.load_profile(override_name)
            if profile:
                logger.info(f"🎯 Using manual override: {profile.name}")
                return profile
            else:
                logger.warning(f"⚠️  Override profile '{override_name}' not found, using auto-detect")
        
        # Auto-detect hardware
        specs = self._detect_hardware_specs()
        cpu_year = specs['cpu_year']
        ram_gb = specs['ram_gb']
        cores = specs['cores']
        
        # Decision tree based on hardware
        available_profiles = self.list_profiles()
        
        # Try to match based on CPU year
        if cpu_year <= 2012 and 'legacy' in available_profiles:
            profile_name = 'legacy'
        elif cpu_year >= 2020 and cores >= 8 and 'low_latency' in available_profiles:
            profile_name = 'low_latency'
        elif cpu_year >= 2019 and 'modern' in available_profiles:
            profile_name = 'modern'
        else:
            profile_name = 'balanced'  # Default fallback
        
        profile = self.load_profile(profile_name)
        if profile:
            logger.info(f"🎯 Auto-selected profile: {profile.name} (CPU ~{cpu_year}, {ram_gb}GB RAM, {cores} cores)")
            return profile
        else:
            # Ultimate fallback: create a basic balanced profile
            logger.warning(f"⚠️  Failed to load any profile, using hardcoded fallback")
            return AudioProfile(
                name="Fallback Balanced",
                description="Hardcoded fallback when no profiles available",
                blocksize=2048,
                samplerate=None,
                gc_policy='disable_during_playback',
                latency_mode='high',
                prime_buffers=True,
                target_latency_ms=43.0,
                xrun_tolerance=3,
                cpu_threshold_pct=70,
                cpu_year_min=2008,
                cpu_year_max=2030,
                ram_min_gb=4,
                cores_min=2
            )


# Singleton instance for global access
_profile_manager: Optional[AudioProfileManager] = None


def get_profile_manager() -> AudioProfileManager:
    """Get singleton instance of AudioProfileManager."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = AudioProfileManager()
    return _profile_manager
