"""
Centralized logging system for Multi Lyrics application.

Usage:
    from core.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Application started")
    logger.debug("Detailed debug information")
    logger.warning("Something might be wrong")
    logger.error("An error occurred", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
import os

# Log levels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(level=None, log_to_file=True, log_dir='logs'):
    """
    Configure logging for the entire application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR). 
               If None, reads from env var MULTI_LYRICS_LOG_LEVEL
        log_to_file: Whether to write logs to file
        log_dir: Directory for log files
    """
    # Determine log level
    if level is None:
        env_level = os.getenv('MULTI_LYRICS_LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, env_level, logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        fmt='%(levelname)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        log_file = log_path / f"multi_lyrics_{datetime.now():%Y%m%d}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name):
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)


# Initialize logging on import (can be reconfigured later)
# Check if running in debug mode
debug_mode = os.getenv('MULTI_LYRICS_DEBUG', '0') == '1'
default_level = logging.DEBUG if debug_mode else logging.INFO

setup_logging(level=default_level)
