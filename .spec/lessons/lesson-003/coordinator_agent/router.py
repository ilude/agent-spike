"""URL classification and routing logic."""

import re
from enum import Enum
from urllib.parse import urlparse


class URLType(Enum):
    """Types of URLs that can be processed."""

    YOUTUBE = "youtube"
    WEBPAGE = "webpage"
    INVALID = "invalid"


class URLRouter:
    """Routes URLs to appropriate specialized agents."""

    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"(?:https?://)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:m\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
    ]

    @classmethod
    def classify_url(cls, url: str) -> URLType:
        """
        Classify a URL as YouTube, webpage, or invalid.

        Args:
            url: The URL to classify

        Returns:
            URLType enum value
        """
        # Basic validation
        if not url or not isinstance(url, str):
            return URLType.INVALID

        url = url.strip()

        # Check for YouTube patterns
        if cls._is_youtube_url(url):
            return URLType.YOUTUBE

        # Check if it's a valid URL
        if cls._is_valid_url(url):
            return URLType.WEBPAGE

        return URLType.INVALID

    @classmethod
    def _is_youtube_url(cls, url: str) -> bool:
        """Check if URL matches YouTube patterns."""
        for pattern in cls.YOUTUBE_PATTERNS:
            if re.match(pattern, url, re.IGNORECASE):
                return True
        return False

    @classmethod
    def _is_valid_url(cls, url: str) -> bool:
        """Check if URL is valid and has http/https scheme."""
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False

    @classmethod
    def get_handler_name(cls, url_type: URLType) -> str:
        """Get human-readable handler name for URL type."""
        if url_type == URLType.YOUTUBE:
            return "YouTube Agent"
        elif url_type == URLType.WEBPAGE:
            return "Webpage Agent"
        else:
            return "Unknown"
