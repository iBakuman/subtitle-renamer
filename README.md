# Subtitle Renamer

A utility to rename subtitle files to match video files based on episode numbers.

## Overview

Subtitle Renamer automatically detects video files and their corresponding subtitle files based on episode numbers or similar patterns, and renames the subtitle files to match the video files while preserving their extensions.

This is particularly useful for TV shows, anime, or any video content with episodes where you want the subtitle filenames to match the video filenames.

## Installation

Install from PyPI:

```bash
pip install subtitle-renamer
```

## Usage

### Command Line

```bash
subtitle-renamer [options]
```

### Options

- `-v, --video-dir`: Directory containing video files (defaults to current directory)
- `-s, --subtitle-dir`: Directory containing subtitle files (defaults to video directory)
- `-r, --recursive`: Search recursively in directories
- `-d, --dry-run`: Show what would be done without actually renaming files
- `--remove-originals`: Remove original subtitle files after renaming
- `--keep-existing`: Skip renaming if target file already exists
- `--verbose`: Show detailed logs
- `--video-pattern`: Custom regex pattern to extract episode numbers from video files (can be specified multiple times)
- `--subtitle-pattern`: Custom regex pattern to extract episode numbers from subtitle files (can be specified multiple times)

### Examples

Basic usage (current directory):
```bash
subtitle-renamer
```

Specify video and subtitle directories:
```bash
subtitle-renamer --video-dir /path/to/videos --subtitle-dir /path/to/subtitles
```

Preview changes without renaming:
```bash
subtitle-renamer --dry-run
```

Recursive search through subdirectories:
```bash
subtitle-renamer --recursive
```

### Python API

You can also use Subtitle Renamer as a library in your Python code:

```python
from subtitle_renamer import SubtitleRenamer

renamer = SubtitleRenamer(
    video_dir="/path/to/videos",
    subtitle_dir="/path/to/subtitles",
    dry_run=True,
    recursive=True
)

renamed_count, total_count = renamer.run()
print(f"Renamed {renamed_count} of {total_count} subtitle files")
```

## How It Works

1. The tool scans for video files and subtitle files in the specified directories
2. It extracts episode numbers using regex patterns
3. It matches video and subtitle files with the same episode number
4. It renames the subtitle files to match the video files, keeping their original extension

## Supported Formats

- **Video**: .mkv, .mp4, .avi, .mov, .flv, .wmv, .m4v, .webm
- **Subtitles**: .srt, .ass, .ssa, .vtt, .sub

## License

MIT