"""
Subtitle Renamer - A utility to rename subtitle files to match video files

This package provides tools to automatically rename subtitle files to match
corresponding video files based on episode numbers or similar patterns.
"""

__version__ = "0.1.0"

from .core import SubtitleRenamer
from .cli import main
from .utils import get_episode_number

__all__ = ["SubtitleRenamer", "main", "get_episode_number"]