#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core functionality for the subtitle renamer.
"""

import os
import re
import shutil
import logging
from typing import Dict, List, Tuple, Pattern

from .utils import get_episode_number

# Set up logging
logger = logging.getLogger(__name__)

class SubtitleRenamer:
    """Class for matching and renaming subtitle files to correspond with video files."""

    # Default regex patterns for extracting episode numbers
    DEFAULT_VIDEO_PATTERNS = [
        r'(?:E|EP|Episode|第)\s*?(\d+)',  # E01, EP01, Episode 01, 第01
        r'(?<!\d)(\d{1,3})(?:[^0-9]|$)',  # Standalone numbers like " 01 " or "_01."
        r'S\d+E(\d+)',  # S1E01
    ]

    DEFAULT_SUBTITLE_PATTERNS = [
        r'(?:E|EP|Episode|第)\s*?(\d+)',  # E01, EP01, Episode 01, 第01
        r'(?<!\d)(\d{1,3})(?:[^0-9]|$)',  # Standalone numbers like " 01 " or "_01."
        r'S\d+E(\d+)',  # S1E01
    ]

    # Common video and subtitle extensions
    VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.webm']
    SUBTITLE_EXTENSIONS = ['.srt', '.ass', '.ssa', '.vtt', '.sub']

    def __init__(
            self,
            video_dir: str = None,
            subtitle_dir: str = None,
            video_patterns: List[str] = None,
            subtitle_patterns: List[str] = None,
            dry_run: bool = False,
            recursive: bool = False,
            remove_originals: bool = False,
            ignore_existing: bool = True,
            verbose: bool = False
    ):
        """
        Initialize the SubtitleRenamer with the specified directories and patterns.
        
        Args:
            video_dir: Directory containing video files
            subtitle_dir: Directory containing subtitle files (defaults to video_dir if None)
            video_patterns: List of regex patterns to extract episode numbers from video files
            subtitle_patterns: List of regex patterns to extract episode numbers from subtitle files
            dry_run: If True, don't actually rename files, just print what would be done
            recursive: If True, search subdirectories for files
            remove_originals: If True, remove original subtitle files after renaming
            ignore_existing: If True, skip renaming if target file already exists
            verbose: If True, print detailed logs
        """
        self.video_dir = os.path.abspath(video_dir or os.getcwd())
        self.subtitle_dir = os.path.abspath(subtitle_dir or self.video_dir)
        self.video_patterns = video_patterns or self.DEFAULT_VIDEO_PATTERNS
        self.subtitle_patterns = subtitle_patterns or self.DEFAULT_SUBTITLE_PATTERNS
        self.dry_run = dry_run
        self.recursive = recursive
        self.remove_originals = remove_originals
        self.ignore_existing = ignore_existing
        self.verbose = verbose

        # Compile regex patterns
        self.compiled_video_patterns = [re.compile(p, re.IGNORECASE) for p in self.video_patterns]
        self.compiled_subtitle_patterns = [re.compile(p, re.IGNORECASE) for p in self.subtitle_patterns]

        # Set log level based on verbosity
        if self.verbose:
            logger.setLevel(logging.DEBUG)

    def find_files(self, directory: str, extensions: List[str]) -> List[str]:
        """
        Find all files with the specified extensions in the directory.
        
        Args:
            directory: Directory to search in
            extensions: List of file extensions to look for
            
        Returns:
            List of file paths matching the criteria
        """
        found_files = []

        if self.recursive:
            # Walk through all subdirectories
            for root, _, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext.lower()) for ext in extensions):
                        found_files.append(os.path.join(root, file))
        else:
            # Only search in the specified directory
            for file in os.listdir(directory):
                if any(file.lower().endswith(ext.lower()) for ext in extensions):
                    found_files.append(os.path.join(directory, file))

        return found_files

    def find_video_files(self) -> Dict[int, str]:
        """
        Find all video files and extract their episode numbers.
        
        Returns:
            Dictionary mapping episode numbers to video file paths
        """
        video_files = {}
        found_files = self.find_files(self.video_dir, self.VIDEO_EXTENSIONS)

        for file_path in found_files:
            episode_number = get_episode_number(file_path, self.compiled_video_patterns)
            if episode_number is not None:
                # Simply store the file path, overwriting any previous file for this episode
                video_files[episode_number] = file_path

        if self.verbose:
            logger.debug(f"Found {len(video_files)} video files with episode numbers")
            for ep, path in video_files.items():
                logger.debug(f"Episode {ep}: {os.path.basename(path)}")

        return video_files

    def find_subtitle_files(self) -> Dict[int, List[str]]:
        """
        Find all subtitle files and extract their episode numbers.
        
        Returns:
            Dictionary mapping episode numbers to lists of subtitle file paths
        """
        subtitle_files = {}
        found_files = self.find_files(self.subtitle_dir, self.SUBTITLE_EXTENSIONS)

        for file_path in found_files:
            episode_number = get_episode_number(file_path, self.compiled_subtitle_patterns)
            if episode_number is not None:
                if episode_number not in subtitle_files:
                    subtitle_files[episode_number] = []
                subtitle_files[episode_number].append(file_path)

        if self.verbose:
            logger.debug(
                f"Found {sum(len(subs) for subs in subtitle_files.values())} subtitle files with episode numbers")
            for ep, paths in subtitle_files.items():
                logger.debug(f"Episode {ep}: {', '.join(os.path.basename(p) for p in paths)}")

        return subtitle_files

    def generate_new_name(self, video_file: str, subtitle_file: str) -> str:
        """
        Generate new name for subtitle file based on video file name.
        
        Args:
            video_file: Path to the video file
            subtitle_file: Path to the subtitle file
            
        Returns:
            New path for the subtitle file
        """
        video_basename = os.path.basename(video_file)
        subtitle_ext = os.path.splitext(subtitle_file)[1]

        # Get the base name of the video file without extension
        video_name_without_ext = os.path.splitext(video_basename)[0]

        # Generate new subtitle file name
        new_subtitle_name = f"{video_name_without_ext}{subtitle_ext}"

        # Generate new path
        subtitle_dir = os.path.dirname(subtitle_file)
        new_subtitle_path = os.path.join(subtitle_dir, new_subtitle_name)

        return new_subtitle_path

    def rename_subtitle(self, src_path: str, dst_path: str) -> bool:
        """
        Rename a subtitle file.
        
        Args:
            src_path: Source path of the subtitle file
            dst_path: Destination path for the renamed subtitle file
            
        Returns:
            True if renaming was successful, False otherwise
        """
        if src_path == dst_path:
            logger.info(f"Skipping, source and destination are the same: {os.path.basename(src_path)}")
            return False

        if os.path.exists(dst_path) and self.ignore_existing:
            logger.info(f"Skipping, destination already exists: {os.path.basename(dst_path)}")
            return False

        try:
            if not self.dry_run:
                # Create destination directory if it doesn't exist
                dst_dir = os.path.dirname(dst_path)
                os.makedirs(dst_dir, exist_ok=True)

                # Copy the file
                shutil.copy2(src_path, dst_path)

                # Remove original if requested
                if self.remove_originals:
                    os.remove(src_path)

            rel_src = os.path.relpath(src_path, self.subtitle_dir)
            rel_dst = os.path.relpath(dst_path, self.subtitle_dir)
            action = "Would rename" if self.dry_run else "Renamed"
            logger.info(f"{action}: {rel_src} -> {rel_dst}")

            return True
        except Exception as e:
            logger.error(f"Error renaming {os.path.basename(src_path)}: {str(e)}")
            return False

    def run(self) -> Tuple[int, int]:
        """
        Run the subtitle renaming process.
        
        Returns:
            Tuple of (number of renamed files, total number of subtitle files)
        """
        logger.info(f"Video directory: {self.video_dir}")
        logger.info(f"Subtitle directory: {self.subtitle_dir}")
        logger.info(f"Mode: {'Dry run' if self.dry_run else 'Actual run'}")

        # Find video and subtitle files
        video_files = self.find_video_files()
        subtitle_files = self.find_subtitle_files()

        if not video_files:
            logger.warning("No video files with recognizable episode numbers found")
            return 0, 0

        if not subtitle_files:
            logger.warning("No subtitle files with recognizable episode numbers found")
            return 0, 0

        # Match and rename
        renamed_count = 0
        total_subtitle_count = sum(len(subs) for subs in subtitle_files.values())

        for episode_number, video_file in video_files.items():
            if episode_number in subtitle_files:
                for subtitle_file in subtitle_files[episode_number]:
                    new_subtitle_path = self.generate_new_name(video_file, subtitle_file)
                    if self.rename_subtitle(subtitle_file, new_subtitle_path):
                        renamed_count += 1

        # Print summary
        logger.info(f"\nSummary: Renamed {renamed_count} of {total_subtitle_count} subtitle files")
        if self.dry_run:
            logger.info("Note: This was a dry run, no files were actually renamed")
        elif not self.remove_originals:
            logger.info("Note: Original subtitle files have been preserved")

        return renamed_count, total_subtitle_count
