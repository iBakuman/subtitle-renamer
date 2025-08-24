#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Organize video files into a consistent naming scheme within existing season folders.

Input directory layout expectation:
<root>/
  <Series Name>/
    Season 01/
      <any video files>
    Season 02/
      <any video files>

This tool renames videos to: "<Series Name> S<season:02>E<episode:02><ext>"

Only a single root directory is required, and the tool scans existing season
subdirectories. It does not move directories; it only renames video files in place.
"""

import os
import re
import logging
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


# Reuse video extensions from core without importing to avoid cycles
VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.webm']


def _is_video_file(filename: str) -> bool:
    """Return True if filename has a known video extension."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in VIDEO_EXTENSIONS)


def _parse_season_from_dirname(dirname: str) -> Optional[int]:
    """Parse season number from a directory name like "Season 01" or "Season 1"."""
    m = re.search(r"season\s*(\d{1,2})", dirname, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _parse_episode_from_filename(filename: str) -> Optional[int]:
    """Parse episode number from common patterns in a video filename.

    Supports patterns like:
    - S01E02
    - E02, EP02, Episode 02, 第02
    - Standalone numbers (last number group in name)
    """
    base = os.path.basename(filename)

    # SxxEyy
    m = re.search(r"S\d+E(\d{1,3})", base, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Eyy / EPyy / Episode yy / 第yy
    m = re.search(r"(?:E|EP|Episode|第)\s*?(\d{1,3})", base, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Bracket token: [07] or [07v2] → use leading number, ignore v-suffix
    m = re.search(r"\[(\d{1,3})(?:v\d+)?\]", base, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Fallback: last number sequence
    numbers = re.findall(r"(\d{1,3})", base)
    if numbers:
        try:
            return int(numbers[-1])
        except ValueError:
            return None
    return None


def _build_target_name(series: str, season: int, episode: int, ext: str) -> str:
    """Return formatted file name: '<Series> SxxEyy<ext>'"""
    return f"{series} S{season:02d}E{episode:02d}{ext}"


class VideoOrganizer:
    """Rename video files under season subfolders to a unified naming scheme."""

    def __init__(self, root_dir: str, dry_run: bool = False, verbose: bool = False) -> None:
        """Initialize with a root directory containing series folders.

        - root_dir: directory that contains series directories
        - dry_run: if True, only log actions
        - verbose: if True, set DEBUG log level
        """
        self.root_dir = os.path.abspath(root_dir)
        self.dry_run = dry_run
        self.verbose = verbose

        if self.verbose:
            logger.setLevel(logging.DEBUG)

    def organize(self) -> Tuple[int, int]:
        """Walk series/season directories and rename videos in place.

        Returns (renamed_count, total_video_count).
        """
        renamed = 0
        total = 0

        if not os.path.isdir(self.root_dir):
            logger.warning(f"Not a directory: {self.root_dir}")
            return 0, 0

        for series_name in sorted(os.listdir(self.root_dir)):
            series_path = os.path.join(self.root_dir, series_name)
            if not os.path.isdir(series_path):
                continue

            # series_name is used as-is in target filenames
            for season_dir in sorted(os.listdir(series_path)):
                season_path = os.path.join(series_path, season_dir)
                if not os.path.isdir(season_path):
                    continue

                season_num = _parse_season_from_dirname(season_dir)
                if season_num is None:
                    # Skip non-season folders
                    logger.debug(f"Skip non-season folder: {season_path}")
                    continue

                for name in sorted(os.listdir(season_path)):
                    if not _is_video_file(name):
                        continue

                    total += 1
                    src = os.path.join(season_path, name)
                    episode = _parse_episode_from_filename(name)
                    if episode is None:
                        logger.info(f"Skipping (no episode found): {os.path.relpath(src, self.root_dir)}")
                        continue

                    ext = os.path.splitext(name)[1]
                    dst_name = _build_target_name(series_name, season_num, episode, ext)
                    dst = os.path.join(season_path, dst_name)

                    if src == dst:
                        logger.debug(f"Already correct: {os.path.relpath(src, self.root_dir)}")
                        continue

                    if os.path.exists(dst):
                        logger.info(f"Skipping (exists): {os.path.relpath(dst, self.root_dir)}")
                        continue

                    if self.dry_run:
                        logger.info(f"Would rename: {os.path.relpath(src, self.root_dir)} -> {os.path.relpath(dst, self.root_dir)}")
                        renamed += 1
                        continue

                    try:
                        os.rename(src, dst)
                        logger.info(f"Renamed: {os.path.relpath(src, self.root_dir)} -> {os.path.relpath(dst, self.root_dir)}")
                        renamed += 1
                    except Exception as e:
                        logger.error(f"Error renaming {name}: {str(e)}")

        return renamed, total


