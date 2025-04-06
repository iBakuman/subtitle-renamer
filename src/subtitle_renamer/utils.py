#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for the subtitle renamer.
"""

import os
import logging
from typing import List, Optional, Pattern

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_episode_number(filename: str, patterns: List[Pattern]) -> Optional[int]:
    """
    Extract episode number from filename using the provided patterns.

    Args:
        filename: The filename to extract episode number from
        patterns: List of compiled regex patterns to use

    Returns:
        Episode number as integer, or None if no match is found
    """
    base_name = os.path.basename(filename)

    for pattern in patterns:
        match = pattern.search(base_name)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue

    return None