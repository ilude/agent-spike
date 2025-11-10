"""YouTube API tools for fetching video data.

This module re-exports functions from the centralized YouTube service.
For new code, import directly from tools.services.youtube instead.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Re-export from centralized service
from tools.services.youtube import (
    extract_video_id,
    get_video_info,
    get_transcript,
    YouTubeTranscriptService,
)

__all__ = [
    "extract_video_id",
    "get_video_info",
    "get_transcript",
    "YouTubeTranscriptService",
]
