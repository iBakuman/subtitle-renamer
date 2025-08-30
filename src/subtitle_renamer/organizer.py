#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Organize video, subtitle, and NFO files into a consistent naming scheme within existing season folders.

Input directory layout expectation:
<root>/
  <Series Name>/
    Season 01/
      <any video files>
    Season 02/
      <any video files>

This tool renames files to: "<Series Name> S<season:02>E<episode:02><ext>"

Only a single root directory is required, and the tool scans existing season
subdirectories. If a series folder has no season subfolders but contains videos,
the tool will create "Season 01" and move all entries into it, then rename videos.

Per-series configuration: put a `.organizer.toml` file under each series
directory (e.g., `<root>/<Series>/.organizer.toml`) to control episode
extraction (modes A/B/F). Series without this file fall back to heuristic
parsing and will skip non-matching files rather than error.
"""

import os
import re
import logging
from typing import Optional, Tuple, List, Dict, Callable

try:  # Python 3.11+
    import tomllib as _toml  # type: ignore
except Exception:  # Python 3.10 with tomli installed
    try:
        import tomli as _toml  # type: ignore
    except Exception:
        _toml = None  # Will error when loading config


logger = logging.getLogger(__name__)


# Known extensions (duplicated from core to avoid import cycles)
VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.webm']
SUBTITLE_EXTENSIONS = ['.srt', '.ass', '.ssa', '.vtt', '.sub']
NFO_EXTENSIONS = ['.nfo']
TARGET_EXTENSIONS = VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS + NFO_EXTENSIONS


def _is_target_file(filename: str) -> bool:
    """Return True if filename has a known target extension (video/subtitle/nfo)."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in TARGET_EXTENSIONS)


def _load_config(root_dir: str) -> Optional[Dict[str, object]]:
    """Load .organizer.toml from root_dir. Returns None if missing.

    Defaults when present: on_miss=error, ignore_version_suffix=true
    """
    config_path = os.path.join(root_dir, ".organizer.toml")
    if not os.path.exists(config_path):
        return None
    if _toml is None:
        raise RuntimeError("TOML parser not available. Use Python 3.11+ or install tomli.")
    with open(config_path, "rb") as f:
        data = _toml.load(f)  # type: ignore
    if not isinstance(data, dict):
        raise ValueError("Invalid .organizer.toml content")
    # set defaults
    data.setdefault("ignore_version_suffix", True)
    data.setdefault("on_miss", "error")
    return data


def _build_extractor_from_config(config: Dict[str, object]) -> Callable[[str], Optional[int]]:
    """Build an episode extractor function based on config (modes A, B, F)."""
    mode = str(config.get("mode", "")).strip().upper()
    ignore_version_suffix = bool(config.get("ignore_version_suffix", True))

    if mode == "A":
        index = int(config.get("number_index", 1))
        return _extract_by_nth_number(index, ignore_version_suffix)

    if mode == "B":
        open_tok = str(config.get("bracket_open", "["))
        close_tok = str(config.get("bracket_close", "]"))
        bindex = int(config.get("bracket_index", 1))
        return _extract_in_nth_bracket(open_tok, close_tok, bindex, ignore_version_suffix)

    if mode == "F":
        sample = str(config.get("sample", ""))
        if not sample:
            raise ValueError("F mode requires 'sample'")
        return _extract_by_sample(sample, ignore_version_suffix)

    raise ValueError("Unsupported or missing mode. Use A, B, or F in .organizer.toml")


def _extract_by_nth_number(number_index: int, ignore_version_suffix: bool) -> Callable[[str], Optional[int]]:
    """Return extractor using the N-th number in filename (1-based, negative for from-end)."""
    # Pattern: capture digits, allow optional immediate version suffix vN after the digits
    suffix = r"(?:[vV]\d+)?" if ignore_version_suffix else ""
    pattern = re.compile(rf"(\d{{1,3}}){suffix}")

    def _extract(name: str) -> Optional[int]:
        base = os.path.basename(name)
        matches = [m.group(1) for m in pattern.finditer(base)]
        if not matches:
            return None
        idx = number_index
        if idx == 0:
            idx = 1
        try:
            value = matches[idx - 1] if idx > 0 else matches[idx]
            return int(value)
        except Exception:
            return None

    return _extract


def _find_bracket_spans(text: str, open_tok: str, close_tok: str) -> List[Tuple[int, int]]:
    """Find non-overlapping spans between open_tok and close_tok in order."""
    spans: List[Tuple[int, int]] = []
    if not open_tok or not close_tok:
        return spans
    start = 0
    L = len(text)
    while start < L:
        s = text.find(open_tok, start)
        if s == -1:
            break
        e = text.find(close_tok, s + len(open_tok))
        if e == -1:
            break
        spans.append((s + len(open_tok), e))
        start = e + len(close_tok)
    return spans


def _extract_in_nth_bracket(open_tok: str, close_tok: str, bracket_index: int, ignore_version_suffix: bool) -> Callable[[str], Optional[int]]:
    """Return extractor that takes first number inside the N-th bracketed segment."""
    suffix = r"(?:[vV]\d+)?" if ignore_version_suffix else ""
    num_re = re.compile(rf"(\d{{1,3}}){suffix}")

    def _extract(name: str) -> Optional[int]:
        base = os.path.basename(name)
        spans = _find_bracket_spans(base, open_tok, close_tok)
        if not spans:
            return None
        idx = bracket_index
        if idx == 0:
            idx = 1
        try:
            span = spans[idx - 1] if idx > 0 else spans[idx]
        except Exception:
            return None
        segment = base[span[0]:span[1]]
        m = num_re.search(segment)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    return _extract


def _extract_by_sample(sample: str, ignore_version_suffix: bool) -> Callable[[str], Optional[int]]:
    """Return extractor generated from a sample with one {digits} marker.

    Example: sample="[{07}v2] Title" will match both with or without vN after the digits.
    """
    m = re.search(r"\{([^}]*)\}", sample)
    if not m:
        raise ValueError("F mode 'sample' must contain one {...} marking episode digits")
    # Build regex: escape literal parts, replace {...} with capture for digits
    prefix = sample[:m.start()]
    suffix_text = sample[m.end():]
    # Escape literals
    pre_esc = re.escape(prefix)
    suf_esc = re.escape(suffix_text)
    # Captured digits with optional version suffix
    vsuf = r"(?:[vV]\d+)?" if ignore_version_suffix else ""
    group = rf"(\d{{1,3}}){vsuf}"
    regex = re.compile(pre_esc + group + suf_esc, re.IGNORECASE)

    def _extract(name: str) -> Optional[int]:
        base = os.path.basename(name)
        mm = regex.search(base)
        if not mm:
            return None
        # group(1) contains only digits due to grouping
        try:
            return int(mm.group(1))
        except Exception:
            return None

    return _extract


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

    # Space-padded numbers: " 07 " → use the number
    m = re.search(r"\s(\d{1,3})\s", base)
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

        # Failures are collected per-series, and raised after series processed if configured
        missing: List[str] = []

        if not os.path.isdir(self.root_dir):
            logger.warning(f"Not a directory: {self.root_dir}")
            return 0, 0

        for series_name in sorted(os.listdir(self.root_dir)):
            series_path = os.path.join(self.root_dir, series_name)
            if not os.path.isdir(series_path):
                continue

            # Load per-series config (root/<series>/.organizer.toml)
            series_config = _load_config(series_path)
            if series_config is None:
                extractor: Callable[[str], Optional[int]] = _parse_episode_from_filename
                fail_fast = False
            else:
                extractor = _build_extractor_from_config(series_config)
                on_miss = (str(series_config.get('on_miss', 'error')) or 'error').lower()
                fail_fast = (on_miss == 'error')

            # series_name is used as-is in target filenames
            entries = sorted(os.listdir(series_path))

            # Detect whether there are season subdirectories
            season_dirs = [d for d in entries if os.path.isdir(os.path.join(series_path, d)) and _parse_season_from_dirname(d) is not None]

            # If there is no valid season dir but there are files, create Season 01 and move all entries
            if not season_dirs:
                has_files = any(os.path.isfile(os.path.join(series_path, e)) for e in entries)
                if has_files:
                    season01 = os.path.join(series_path, "Season 01")
                    if not self.dry_run:
                        os.makedirs(season01, exist_ok=True)
                    else:
                        logger.info(f"Would create directory: {os.path.relpath(season01, self.root_dir)}")

                    for e in entries:
                        src_e = os.path.join(series_path, e)
                        # move everything (files and subdirs) into Season 01
                        dst_e = os.path.join(season01, e)
                        if self.dry_run:
                            logger.info(f"Would move: {os.path.relpath(src_e, self.root_dir)} -> {os.path.relpath(dst_e, self.root_dir)}")
                            continue
                        try:
                            os.rename(src_e, dst_e)
                        except Exception as move_err:
                            logger.error(f"Error moving {os.path.relpath(src_e, self.root_dir)}: {str(move_err)}")

                    # refresh entries and season_dirs after moving
                    entries = sorted(os.listdir(series_path))
                    season_dirs = [d for d in entries if os.path.isdir(os.path.join(series_path, d)) and _parse_season_from_dirname(d) is not None]

            for season_dir in season_dirs:
                season_path = os.path.join(series_path, season_dir)
                if not os.path.isdir(season_path):
                    continue

                season_num = _parse_season_from_dirname(season_dir)
                if season_num is None:
                    # Skip non-season folders
                    logger.debug(f"Skip non-season folder: {season_path}")
                    continue

                for name in sorted(os.listdir(season_path)):
                    if not _is_target_file(name):
                        continue

                    total += 1
                    src = os.path.join(season_path, name)
                    episode = extractor(name)
                    if episode is None:
                        rel = os.path.relpath(src, self.root_dir)
                        missing.append(rel)
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

        # If any missing with any series configured as error, raise summary error
        if missing:
            lines = "\n".join(missing)
            raise RuntimeError(f"Episode extraction failed for the following files:\n{lines}")

        return renamed, total


