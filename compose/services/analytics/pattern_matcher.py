"""Pure pattern matching logic for URL analytics (no database dependencies)."""

from urllib.parse import urlparse
from typing import Optional
from .models import LearnedPatternRecord


def extract_domain(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: Full URL (e.g., "https://github.com/user/repo")

    Returns:
        Domain string (e.g., "github.com")

    Examples:
        >>> extract_domain("https://github.com/user/repo")
        'github.com'
        >>> extract_domain("http://example.com:8080/path")
        'example.com:8080'
        >>> extract_domain("https://sub.domain.com/")
        'sub.domain.com'
    """
    parsed = urlparse(url)
    return parsed.netloc


def url_matches_pattern(url: str, pattern: str, pattern_type: str) -> bool:
    """Check if URL matches a pattern.

    Args:
        url: Full URL to test
        pattern: Pattern to match against
        pattern_type: One of 'domain', 'url_pattern', or 'path'

    Returns:
        True if URL matches pattern, False otherwise

    Pattern types:
        - domain: Match against URL's domain (netloc)
        - url_pattern: Substring match against full URL
        - path: Substring match against URL path component

    Examples:
        >>> url_matches_pattern("https://github.com/user/repo", "github.com", "domain")
        True
        >>> url_matches_pattern("https://shop.com/product?coupon=SAVE", "?coupon=", "url_pattern")
        True
        >>> url_matches_pattern("https://example.com/docs/guide", "/docs/", "path")
        True
    """
    url_lower = url.lower()
    pattern_lower = pattern.lower()

    if pattern_type == "domain":
        return pattern_lower in urlparse(url).netloc.lower()
    elif pattern_type == "url_pattern":
        return pattern_lower in url_lower
    elif pattern_type == "path":
        return pattern_lower in urlparse(url).path.lower()
    else:
        return False


def find_matching_pattern(
    url: str,
    patterns: list[LearnedPatternRecord],
) -> Optional[LearnedPatternRecord]:
    """Find first matching pattern for URL from a list of patterns.

    Args:
        url: URL to match
        patterns: List of learned patterns to check

    Returns:
        First matching LearnedPatternRecord, or None if no match

    Examples:
        >>> patterns = [LearnedPatternRecord(pattern="github.com", pattern_type="domain", ...)]
        >>> result = find_matching_pattern("https://github.com/user/repo", patterns)
        >>> result.pattern
        'github.com'
    """
    for pattern in patterns:
        if url_matches_pattern(url, pattern.pattern, pattern.pattern_type):
            return pattern
    return None
