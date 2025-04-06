#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for the subtitle renamer.
"""

import argparse
from .core import SubtitleRenamer


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Rename subtitle files to match video files based on episode numbers',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('-v', '--video-dir',
                        help='Directory containing video files (defaults to current directory)')
    parser.add_argument('-s', '--subtitle-dir',
                        help='Directory containing subtitle files (defaults to video directory)')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Search recursively in directories')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Show what would be done without actually renaming files')
    parser.add_argument('--remove-originals', action='store_true',
                        help='Remove original subtitle files after renaming')
    parser.add_argument('--keep-existing', action='store_true',
                        help='Skip renaming if target file already exists')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed logs')
    parser.add_argument('--video-pattern', action='append',
                        help='Custom regex pattern to extract episode numbers from video files (can be specified multiple times)')
    parser.add_argument('--subtitle-pattern', action='append',
                        help='Custom regex pattern to extract episode numbers from subtitle files (can be specified multiple times)')

    return parser.parse_args()


def main():
    """Main function to run the subtitle renamer."""
    args = parse_arguments()

    renamer = SubtitleRenamer(
        video_dir=args.video_dir,
        subtitle_dir=args.subtitle_dir,
        video_patterns=args.video_pattern,
        subtitle_patterns=args.subtitle_pattern,
        dry_run=args.dry_run,
        recursive=args.recursive,
        remove_originals=args.remove_originals,
        ignore_existing=not args.keep_existing,
        verbose=args.verbose
    )

    renamer.run()


if __name__ == "__main__":
    main()
