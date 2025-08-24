#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for the subtitle renamer and simple video organizer.
"""

import argparse

from core import SubtitleRenamer
from organizer import VideoOrganizer


def build_parser():
    """Build the root parser with subcommands."""
    parser = argparse.ArgumentParser(
        description='Rename subtitle files or organize videos into a consistent naming scheme',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', required=False)

    # rename (default) - keep backward compatibility with existing flags
    p_rename = subparsers.add_parser('rename', help='Rename subtitle files to match video files')
    p_rename.add_argument('-v', '--video-dir', help='Directory containing video files (defaults to current directory)')
    p_rename.add_argument('-s', '--subtitle-dir',
                          help='Directory containing subtitle files (defaults to video directory)')
    p_rename.add_argument('-r', '--recursive', action='store_true', help='Search recursively in directories')
    p_rename.add_argument('-d', '--dry-run', action='store_true', help='Show actions without renaming files')
    p_rename.add_argument('--remove-originals', action='store_true',
                          help='Remove original subtitle files after renaming')
    p_rename.add_argument('--keep-existing', action='store_true', help='Skip if target file exists')
    p_rename.add_argument('--verbose', action='store_true', help='Show detailed logs')
    p_rename.add_argument('--video-pattern', action='append',
                          help='Regex to extract episode numbers from video files (repeatable)')
    p_rename.add_argument('--subtitle-pattern', action='append',
                          help='Regex to extract episode numbers from subtitle files (repeatable)')

    # organize - single positional directory only
    p_org = subparsers.add_parser('organize', help='Organize videos under season folders to unified naming')
    p_org.add_argument('root', help='Root directory containing series folders and season subfolders')
    p_org.add_argument('-d', '--dry-run', action='store_true', help='Show actions without renaming files')
    p_org.add_argument('--verbose', action='store_true', help='Show detailed logs')

    return parser


def main():
    """Main function for CLI."""
    parser = build_parser()
    args = parser.parse_args()

    # Default to rename if no subcommand provided (backward compatible)
    if args.command == 'rename':
        renamer = SubtitleRenamer(
            video_dir=getattr(args, 'video_dir', None),
            subtitle_dir=getattr(args, 'subtitle_dir', None),
            video_patterns=getattr(args, 'video_pattern', None),
            subtitle_patterns=getattr(args, 'subtitle_pattern', None),
            dry_run=getattr(args, 'dry_run', False),
            recursive=getattr(args, 'recursive', False),
            remove_originals=getattr(args, 'remove_originals', False),
            ignore_existing=not getattr(args, 'keep_existing', False),
            verbose=getattr(args, 'verbose', False),
        )
        renamer.run()
        return

    if args.command == 'organize':
        organizer = VideoOrganizer(root_dir=args.root, dry_run=args.dry_run, verbose=args.verbose)
        organizer.organize()
        return

    print("Unknown command")


if __name__ == "__main__":
    main()
