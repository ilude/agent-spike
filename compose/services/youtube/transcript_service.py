"""Centralized YouTube Transcript API service with proxy support.

This service wraps youtube-transcript-api with:
- Automatic proxy configuration (Webshare)
- Configurable via environment variables
- Dependency injection pattern
- Drop-in replacement for direct API usage

Environment variables:
- WEBSHARE_PROXY_USERNAME: Webshare proxy username
- WEBSHARE_PROXY_PASSWORD: Webshare proxy password
- YOUTUBE_TRANSCRIPT_USE_PROXY: Set to "false" to disable proxy (default: true)
"""

import os
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


class YouTubeTranscriptService:
    """Wrapper for YouTubeTranscriptApi with proxy support.

    Automatically configures proxies from environment variables.
    Falls back to direct connection if proxy credentials not found.

    Example:
        >>> service = YouTubeTranscriptService()
        >>> transcript = service.fetch_transcript("dQw4w9WgXcQ")
    """

    def __init__(
        self,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        use_proxy: Optional[bool] = None,
    ):
        """Initialize YouTube transcript service.

        Args:
            proxy_username: Webshare proxy username (default: from WEBSHARE_PROXY_USERNAME env)
            proxy_password: Webshare proxy password (default: from WEBSHARE_PROXY_PASSWORD env)
            use_proxy: Whether to use proxy (default: from YOUTUBE_TRANSCRIPT_USE_PROXY env, or True)
        """
        # Get proxy credentials from env if not provided
        self.proxy_username = proxy_username or os.getenv("WEBSHARE_PROXY_USERNAME")
        self.proxy_password = proxy_password or os.getenv("WEBSHARE_PROXY_PASSWORD")

        # Check if proxy should be used
        if use_proxy is None:
            use_proxy_env = os.getenv("YOUTUBE_TRANSCRIPT_USE_PROXY", "true").lower()
            use_proxy = use_proxy_env in ("true", "1", "yes")

        self.use_proxy = use_proxy

        # Configure proxy if enabled and credentials available
        self.proxy_config = None
        if self.use_proxy and self.proxy_username and self.proxy_password:
            # Create Webshare proxy config
            self.proxy_config = WebshareProxyConfig(
                proxy_username=self.proxy_username,
                proxy_password=self.proxy_password,
            )
            self._proxy_configured = True
        else:
            self._proxy_configured = False

    def fetch_transcript(self, video_id: str, languages: Optional[list[str]] = None) -> str:
        """Fetch transcript for a YouTube video.

        Args:
            video_id: YouTube video ID (11 characters)
            languages: Preferred transcript languages (default: ['en'])

        Returns:
            Full transcript text as a single string

        Raises:
            TranscriptsDisabled: If transcripts are disabled for the video
            NoTranscriptFound: If no transcript found in requested languages
            Exception: For other errors (network, parsing, etc.)
        """
        if languages is None:
            languages = ["en"]

        # Create API instance with or without proxy config
        if self._proxy_configured:
            api = YouTubeTranscriptApi(proxy_config=self.proxy_config)
        else:
            api = YouTubeTranscriptApi()

        # Fetch transcript
        fetched = api.fetch(video_id, languages=languages)

        # Combine all transcript snippets into single text
        full_text = " ".join(snippet.text for snippet in fetched.snippets)

        return full_text

    def fetch_timed_transcript(
        self, video_id: str, languages: Optional[list[str]] = None
    ) -> list[dict]:
        """Fetch transcript with timestamps for a YouTube video.

        Args:
            video_id: YouTube video ID (11 characters)
            languages: Preferred transcript languages (default: ['en'])

        Returns:
            List of transcript segments with timestamps:
            [{"text": str, "start": float, "duration": float}, ...]

        Raises:
            TranscriptsDisabled: If transcripts are disabled for the video
            NoTranscriptFound: If no transcript found in requested languages
            Exception: For other errors (network, parsing, etc.)
        """
        if languages is None:
            languages = ["en"]

        # Create API instance with or without proxy config
        if self._proxy_configured:
            api = YouTubeTranscriptApi(proxy_config=self.proxy_config)
        else:
            api = YouTubeTranscriptApi()

        # Fetch transcript
        fetched = api.fetch(video_id, languages=languages)

        # Return snippets with timestamps
        return [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in fetched.snippets
        ]

    def fetch_transcript_safe(
        self,
        video_id: str,
        languages: Optional[list[str]] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """Fetch transcript with error handling.

        Args:
            video_id: YouTube video ID
            languages: Preferred transcript languages

        Returns:
            Tuple of (transcript_text, error_message)
            - If successful: (transcript, None)
            - If failed: (None, error_message)
        """
        try:
            transcript = self.fetch_transcript(video_id, languages)
            return (transcript, None)
        except TranscriptsDisabled:
            return (None, "Transcripts are disabled for this video")
        except NoTranscriptFound:
            return (None, f"No transcript found for languages: {languages}")
        except Exception as e:
            return (None, f"Error fetching transcript: {str(e)}")

    def is_proxy_configured(self) -> bool:
        """Check if proxy is configured and enabled.

        Returns:
            True if proxy is configured, False otherwise
        """
        return self._proxy_configured

    def get_proxy_info(self) -> dict[str, str]:
        """Get proxy configuration info (without password).

        Returns:
            Dictionary with proxy info for debugging
        """
        return {
            "use_proxy": str(self.use_proxy),
            "proxy_configured": str(self._proxy_configured),
            "proxy_username": self.proxy_username if self._proxy_configured else "not configured",
            "proxy_host": "p.webshare.io:80" if self._proxy_configured else "not configured",
        }


# Singleton instance for convenience
_default_service: Optional[YouTubeTranscriptService] = None


def get_default_service() -> YouTubeTranscriptService:
    """Get or create the default YouTubeTranscriptService instance.

    This singleton is configured from environment variables on first use.

    Returns:
        Shared YouTubeTranscriptService instance
    """
    global _default_service
    if _default_service is None:
        _default_service = YouTubeTranscriptService()
    return _default_service


def fetch_transcript(video_id: str, languages: Optional[list[str]] = None) -> str:
    """Convenience function using the default service.

    Args:
        video_id: YouTube video ID
        languages: Preferred transcript languages (default: ['en'])

    Returns:
        Full transcript text

    Raises:
        Same exceptions as YouTubeTranscriptService.fetch_transcript()
    """
    service = get_default_service()
    return service.fetch_transcript(video_id, languages)


def fetch_transcript_safe(
    video_id: str,
    languages: Optional[list[str]] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Convenience function using the default service with error handling.

    Args:
        video_id: YouTube video ID
        languages: Preferred transcript languages

    Returns:
        Tuple of (transcript_text, error_message)
    """
    service = get_default_service()
    return service.fetch_transcript_safe(video_id, languages)
