"""Tests for webpage docling service.

Run with: uv run pytest compose/services/tests/unit/test_webpage.py
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from compose.services.cache import create_in_memory_cache
from compose.services.webpage.docling_service import fetch_webpage, get_page_info


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache():
    """Create an in-memory cache for testing."""
    return create_in_memory_cache()


@pytest.fixture
def sample_docling_response():
    """Sample successful response from Docling API."""
    return {
        "status": "success",
        "document": {
            "md_content": "# Sample Page\n\nThis is sample markdown content from the page."
            * 5  # Make it longer than 100 chars
        },
    }


@pytest.fixture
def short_content_response():
    """Response with content shorter than 100 chars."""
    return {
        "status": "success",
        "document": {"md_content": "Short content"},
    }


@pytest.fixture
def long_content_response():
    """Response with content longer than max_chars."""
    return {
        "status": "success",
        "document": {
            "md_content": "A" * 20000,  # Longer than default 15000
        },
    }


# =============================================================================
# fetch_webpage tests
# =============================================================================


@pytest.mark.unit
def test_fetch_webpage_success(sample_docling_response):
    """Test successful webpage fetch from Docling API."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = sample_docling_response

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        result = fetch_webpage("https://example.com")

        assert "Sample Page" in result
        assert "ERROR:" not in result
        mock_post.assert_called_once()


@pytest.mark.unit
def test_fetch_webpage_cache_hit(mock_cache):
    """Test that cached content is returned without API call."""
    test_url = "https://example.com/cached"
    cached_content = "# Cached Markdown\n\nThis is cached content."

    # Manually populate cache with expected key format
    import hashlib

    url_hash = hashlib.sha256(test_url.encode()).hexdigest()[:16]
    cache_key = f"webpage:content:{url_hash}"
    mock_cache.set(cache_key, {"markdown": cached_content, "url": test_url})

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        result = fetch_webpage(test_url, cache=mock_cache)

        assert result == cached_content
        mock_post.assert_not_called()


@pytest.mark.unit
def test_fetch_webpage_cache_miss_then_store(mock_cache, sample_docling_response):
    """Test that cache miss calls API and stores result."""
    test_url = "https://example.com/new"

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = sample_docling_response

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        # First call - should hit API
        result = fetch_webpage(test_url, cache=mock_cache)

        assert "Sample Page" in result
        mock_post.assert_called_once()

        # Verify cache was populated
        import hashlib

        url_hash = hashlib.sha256(test_url.encode()).hexdigest()[:16]
        cache_key = f"webpage:content:{url_hash}"
        assert mock_cache.exists(cache_key)


@pytest.mark.unit
def test_fetch_webpage_truncation(mock_cache, long_content_response):
    """Test that content exceeding max_chars is truncated."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = long_content_response

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        result = fetch_webpage("https://example.com", max_chars=15000)

        assert "[Content truncated for analysis...]" in result
        # Check truncation happened at correct point
        assert len(result) == 15000 + len("\n\n[Content truncated for analysis...]")


@pytest.mark.unit
def test_fetch_webpage_short_content_error(short_content_response):
    """Test that short content (<100 chars) returns error."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = short_content_response

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        result = fetch_webpage("https://example.com")

        assert result.startswith("ERROR:")
        assert "too short" in result or "paywall" in result


@pytest.mark.unit
def test_fetch_webpage_connect_error():
    """Test handling of connection errors."""
    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        result = fetch_webpage("https://example.com")

        assert result.startswith("ERROR:")
        assert "connect" in result.lower()


@pytest.mark.unit
def test_fetch_webpage_timeout_error():
    """Test handling of timeout errors."""
    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        result = fetch_webpage("https://example.com")

        assert result.startswith("ERROR:")
        assert "timeout" in result.lower()


@pytest.mark.unit
def test_fetch_webpage_http_status_error():
    """Test handling of HTTP status errors (e.g., 500)."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )

        result = fetch_webpage("https://example.com")

        assert result.startswith("ERROR:")
        assert "500" in result


@pytest.mark.unit
def test_fetch_webpage_missing_key_in_response():
    """Test handling of unexpected response format (missing keys)."""
    # Response missing 'document' key
    bad_response = {"status": "success"}

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = bad_response

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        result = fetch_webpage("https://example.com")

        assert result.startswith("ERROR:")
        assert "missing" in result.lower() or "format" in result.lower()


@pytest.mark.unit
def test_fetch_webpage_docling_failure_status():
    """Test handling of Docling API returning non-success status."""
    failure_response = {
        "status": "error",
        "errors": ["Failed to parse HTML"],
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = failure_response

    with patch("compose.services.webpage.docling_service.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        result = fetch_webpage("https://example.com")

        assert result.startswith("ERROR:")
        assert "Docling conversion failed" in result


# =============================================================================
# get_page_info tests
# =============================================================================


@pytest.mark.unit
def test_get_page_info_https_url():
    """Test getting page info for valid HTTPS URL."""
    url = "https://example.com/page"
    info = get_page_info(url)

    assert info["url"] == url
    assert info["protocol"] == "https"
    assert "error" not in info


@pytest.mark.unit
def test_get_page_info_http_url():
    """Test getting page info for valid HTTP URL."""
    url = "http://example.com/page"
    info = get_page_info(url)

    assert info["url"] == url
    assert info["protocol"] == "http"
    assert "error" not in info


@pytest.mark.unit
def test_get_page_info_invalid_url_no_prefix():
    """Test that URL without http/https prefix returns error."""
    url = "example.com/page"
    info = get_page_info(url)

    assert "error" in info
    assert "http" in info["error"].lower()


@pytest.mark.unit
def test_get_page_info_invalid_url_ftp():
    """Test that FTP URL returns error."""
    url = "ftp://example.com/file"
    info = get_page_info(url)

    assert "error" in info


@pytest.mark.unit
def test_get_page_info_caching(mock_cache):
    """Test that page info is cached correctly."""
    url = "https://example.com/cached-info"

    # First call - should cache
    info1 = get_page_info(url, cache=mock_cache)
    assert info1["url"] == url
    assert info1["protocol"] == "https"

    # Second call - should use cache
    info2 = get_page_info(url, cache=mock_cache)
    assert info2 == info1

    # Verify cache key exists
    import hashlib

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_key = f"webpage:info:{url_hash}"
    assert mock_cache.exists(cache_key)


@pytest.mark.unit
def test_get_page_info_cache_hit(mock_cache):
    """Test that cached page info is returned without recomputation."""
    url = "https://example.com/pre-cached"

    # Pre-populate cache
    import hashlib

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_key = f"webpage:info:{url_hash}"
    cached_info = {"url": url, "protocol": "https", "extra": "cached_data"}
    mock_cache.set(cache_key, cached_info)

    # Call should return cached data with extra field
    info = get_page_info(url, cache=mock_cache)
    assert info["extra"] == "cached_data"
