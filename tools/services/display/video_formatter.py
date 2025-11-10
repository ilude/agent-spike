"""Format video metadata for console display.

This module provides consistent formatting for displaying YouTube video
metadata across different scripts (search, list, verify).

Example:
    >>> from tools.services.display import format_video_display
    >>> video = {
    ...     "video_id": "abc123",
    ...     "url": "https://youtube.com/watch?v=abc123",
    ...     "metadata": {"title": "Test Video", "subject_matter": ["AI", "Python"]}
    ... }
    >>> print(format_video_display(video, index=1))
    1. abc123
       URL: https://youtube.com/watch?v=abc123
       Title: Test Video
       ...
"""

from typing import Any


def format_video_display(
    video: dict[str, Any],
    index: int,
    show_score: bool = False
) -> str:
    """Format video metadata for console display.

    Handles both old (tags string) and new (structured metadata dict) formats
    for backwards compatibility.

    Args:
        video: Video data dict with video_id, url, metadata, etc.
        index: Display index number (1-based)
        show_score: If True, show relevance score (from semantic search)

    Returns:
        Formatted string ready for printing to console

    Example (new format):
        >>> video = {
        ...     "video_id": "1_z3h2r93OY",
        ...     "url": "https://youtube.com/watch?v=1_z3h2r93OY",
        ...     "transcript_length": 11460,
        ...     "metadata": {
        ...         "title": "MCP token waste and the solution",
        ...         "subject_matter": ["MCP protocol", "token efficiency"],
        ...         "content_style": "demonstration"
        ...     },
        ...     "_score": 0.875  # From semantic search
        ... }
        >>> output = format_video_display(video, 1, show_score=True)
        >>> "Relevance: 0.875" in output
        True
        >>> "MCP protocol" in output
        True

    Example (old format fallback):
        >>> video = {
        ...     "video_id": "abc123",
        ...     "url": "https://youtube.com/watch?v=abc123",
        ...     "tags": "AI, machine learning, tutorial"
        ... }
        >>> output = format_video_display(video, 1)
        >>> "AI, machine learning, tutorial" in output
        True
    """
    # Extract basic fields
    video_id = video.get('video_id', 'N/A')
    url = video.get('url', 'N/A')
    transcript_length = video.get('transcript_length', 0)

    # Extract metadata (new format) or fall back to old format
    metadata = video.get('metadata', {})
    if metadata:
        title = metadata.get('title', 'N/A')
        subject = ', '.join(metadata.get('subject_matter', [])[:3]) or 'N/A'
        content_style = metadata.get('content_style', 'N/A')
    else:
        # Fallback to old format
        title = 'N/A'
        subject = video.get('tags', 'N/A')
        content_style = 'N/A'

    # Build output lines
    lines = [
        f"{index}. {video_id}",
        f"   URL: {url}",
        f"   Title: {title}",
        f"   Subject: {subject}",
        f"   Style: {content_style}",
        f"   Transcript: {transcript_length:,} characters",
    ]

    # Add relevance score if present (from semantic search)
    if show_score and '_score' in video:
        score = video['_score']
        lines.insert(1, f"   Relevance: {score:.3f}")

    return "\n".join(lines) + "\n"
