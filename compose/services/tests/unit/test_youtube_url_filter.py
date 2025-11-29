"""Unit tests for YouTube URL filtering.

Tests for url_filter.py - URL extraction and filtering

Run with: uv run pytest compose/services/tests/unit/test_youtube_url_filter.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import os


class TestExtractUrls:
    """Test URL extraction from text."""

    @pytest.mark.unit
    def test_extract_single_url(self):
        """Test extracting a single URL."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Check out https://github.com/user/repo for more info."
        urls = extract_urls(text)

        assert urls == ["https://github.com/user/repo"]

    @pytest.mark.unit
    def test_extract_multiple_urls(self):
        """Test extracting multiple URLs."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Visit https://example.com and http://test.org for details."
        urls = extract_urls(text)

        assert urls == ["https://example.com", "http://test.org"]

    @pytest.mark.unit
    def test_extract_urls_deduplicates(self):
        """Test that duplicate URLs are removed."""
        from compose.services.youtube.url_filter import extract_urls

        text = "See https://example.com first, then https://example.com again."
        urls = extract_urls(text)

        assert urls == ["https://example.com"]

    @pytest.mark.unit
    def test_extract_urls_removes_trailing_punctuation(self):
        """Test that trailing punctuation is removed."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Check https://example.com. Also https://test.org!"
        urls = extract_urls(text)

        assert urls == ["https://example.com", "https://test.org"]

    @pytest.mark.unit
    def test_extract_urls_handles_parentheses(self):
        """Test handling of unbalanced parentheses."""
        from compose.services.youtube.url_filter import extract_urls

        text = "(See https://example.com/path)"
        urls = extract_urls(text)

        # Should handle unbalanced closing paren
        assert "https://example.com/path" in urls[0]

    @pytest.mark.unit
    def test_extract_urls_no_urls(self):
        """Test extraction from text with no URLs."""
        from compose.services.youtube.url_filter import extract_urls

        text = "This is plain text with no links."
        urls = extract_urls(text)

        assert urls == []

    @pytest.mark.unit
    def test_extract_urls_complex_urls(self):
        """Test extraction of URLs with query parameters."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Link: https://example.com/path?foo=bar&baz=qux"
        urls = extract_urls(text)

        assert urls == ["https://example.com/path?foo=bar&baz=qux"]


class TestIsBlockedByHeuristic:
    """Test heuristic URL blocking."""

    @pytest.mark.unit
    def test_blocked_domain_gumroad(self):
        """Test that gumroad.com is blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://gumroad.com/product")

        assert is_blocked is True
        assert "gumroad.com" in reason

    @pytest.mark.unit
    def test_blocked_domain_patreon(self):
        """Test that patreon.com/join is blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://patreon.com/join/creator"
        )

        assert is_blocked is True
        assert "patreon.com/join" in reason

    @pytest.mark.unit
    def test_blocked_domain_bit_ly(self):
        """Test that bit.ly is blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://bit.ly/abc123")

        assert is_blocked is True
        assert "bit.ly" in reason

    @pytest.mark.unit
    def test_blocked_pattern_checkout(self):
        """Test that checkout URLs are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://store.example.com/checkout"
        )

        assert is_blocked is True
        assert "checkout" in reason

    @pytest.mark.unit
    def test_blocked_pattern_utm(self):
        """Test that URLs with UTM parameters are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://example.com/page?utm_source=youtube"
        )

        assert is_blocked is True
        assert "utm_" in reason

    @pytest.mark.unit
    def test_blocked_pattern_affiliate(self):
        """Test that affiliate links are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://example.com/product?affiliate=abc"
        )

        assert is_blocked is True
        assert "affiliate=" in reason

    @pytest.mark.unit
    def test_blocked_social_twitter_profile(self):
        """Test that Twitter/X profiles are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://twitter.com/username")

        assert is_blocked is True
        assert "Social media profile" in reason

    @pytest.mark.unit
    def test_blocked_social_instagram_profile(self):
        """Test that Instagram profiles are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://instagram.com/username")

        assert is_blocked is True
        assert "Social media profile" in reason

    @pytest.mark.unit
    def test_blocked_social_youtube_channel(self):
        """Test that YouTube channel profiles are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://youtube.com/@username")

        assert is_blocked is True
        assert "Social media profile" in reason

    @pytest.mark.unit
    def test_not_blocked_github(self):
        """Test that GitHub repos are not blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://github.com/user/repo")

        assert is_blocked is False
        assert reason is None

    @pytest.mark.unit
    def test_not_blocked_documentation(self):
        """Test that documentation sites are not blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://docs.python.org/3/")

        assert is_blocked is False
        assert reason is None

    @pytest.mark.unit
    def test_not_blocked_clean_url(self):
        """Test that clean URLs without patterns are not blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://example.com/tutorial")

        assert is_blocked is False
        assert reason is None


class TestApplyHeuristicFilter:
    """Test applying heuristic filter to URL list."""

    @pytest.mark.unit
    def test_apply_filter_mixed_urls(self):
        """Test filtering a mix of blocked and allowed URLs."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        urls = [
            "https://github.com/user/repo",
            "https://gumroad.com/product",
            "https://docs.python.org",
            "https://bit.ly/abc123",
        ]

        result = apply_heuristic_filter(urls)

        assert len(result["blocked"]) == 2
        assert len(result["remaining"]) == 2
        assert "https://github.com/user/repo" in result["remaining"]
        assert "https://docs.python.org" in result["remaining"]

    @pytest.mark.unit
    def test_apply_filter_all_blocked(self):
        """Test filtering when all URLs are blocked."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        urls = ["https://gumroad.com/a", "https://bit.ly/b", "https://amzn.to/c"]

        result = apply_heuristic_filter(urls)

        assert len(result["blocked"]) == 3
        assert len(result["remaining"]) == 0

    @pytest.mark.unit
    def test_apply_filter_none_blocked(self):
        """Test filtering when no URLs are blocked."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        urls = [
            "https://github.com/user/repo",
            "https://docs.python.org",
            "https://stackoverflow.com/questions/123",
        ]

        result = apply_heuristic_filter(urls)

        assert len(result["blocked"]) == 0
        assert len(result["remaining"]) == 3

    @pytest.mark.unit
    def test_apply_filter_empty_list(self):
        """Test filtering empty URL list."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        result = apply_heuristic_filter([])

        assert result["blocked"] == []
        assert result["remaining"] == []


class TestClassifyUrlWithLlm:
    """Test LLM-based URL classification."""

    @pytest.mark.unit
    def test_classify_url_content(self):
        """Test classifying a content URL."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"classification": "content", "confidence": 0.95, "reason": "Documentation site"}'
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://docs.python.org",
                video_context={"video_title": "Python Tutorial"},
                api_key="test-key",
            )

            assert classification == "content"
            assert confidence == 0.95
            assert reason == "Documentation site"
            assert cost > 0

    @pytest.mark.unit
    def test_classify_url_marketing(self):
        """Test classifying a marketing URL."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"classification": "marketing", "confidence": 0.85, "reason": "Product page"}'
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://store.example.com/product",
                video_context={"video_title": "Review"},
                api_key="test-key",
            )

            assert classification == "marketing"
            assert confidence == 0.85

    @pytest.mark.unit
    def test_classify_url_with_suggested_pattern(self):
        """Test classification that includes a suggested pattern."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""{
                "classification": "content",
                "confidence": 0.9,
                "reason": "GitHub repo",
                "suggested_pattern": {
                    "pattern": "github.com",
                    "type": "domain",
                    "rationale": "GitHub repos are typically content"
                }
            }"""
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 80

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://github.com/user/repo",
                video_context={"video_title": "Tutorial"},
                api_key="test-key",
            )

            assert pattern is not None
            assert pattern["pattern"] == "github.com"
            assert pattern["type"] == "domain"

    @pytest.mark.unit
    def test_classify_url_fallback_parsing(self):
        """Test fallback when JSON parsing fails."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Invalid response - not JSON")]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://example.com",
                video_context={"video_title": "Test"},
                api_key="test-key",
            )

            # Should fall back to marketing with 0.5 confidence
            assert classification == "marketing"
            assert confidence == 0.5
            assert "Failed to parse" in reason

    @pytest.mark.unit
    def test_classify_url_no_api_key(self):
        """Test that missing API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            from compose.services.youtube.url_filter import classify_url_with_llm

            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
                classify_url_with_llm(
                    url="https://example.com",
                    video_context={"video_title": "Test"},
                )


class TestFilterUrls:
    """Test the main filter_urls orchestrator function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_filter_urls_no_urls(self):
        """Test filtering text with no URLs."""
        from compose.services.youtube.url_filter import filter_urls

        result = await filter_urls(
            description="No URLs here",
            video_context={"video_title": "Test"},
            use_llm=False,
        )

        assert result["all_urls"] == []
        assert result["content_urls"] == []
        assert result["blocked_urls"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_filter_urls_heuristic_only(self):
        """Test filtering with heuristics only (no LLM)."""
        from compose.services.youtube.url_filter import filter_urls

        result = await filter_urls(
            description="Check https://github.com/user/repo and https://gumroad.com/product",
            video_context={"video_title": "Test"},
            use_llm=False,
        )

        assert len(result["all_urls"]) == 2
        assert "https://gumroad.com/product" in result["blocked_urls"]
        # Without LLM, remaining URLs go to content
        assert "https://github.com/user/repo" in result["content_urls"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_filter_urls_all_blocked(self):
        """Test when all URLs are blocked by heuristics."""
        from compose.services.youtube.url_filter import filter_urls

        result = await filter_urls(
            description="Links: https://gumroad.com/a https://bit.ly/b",
            video_context={"video_title": "Test"},
            use_llm=False,
        )

        assert len(result["blocked_urls"]) == 2
        assert result["content_urls"] == []
        assert result["remaining"] if "remaining" in result else True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_filter_urls_cost_tracking(self):
        """Test that LLM costs are tracked."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"classification": "content", "confidence": 0.9, "reason": "Test"}'
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 100

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import filter_urls

            result = await filter_urls(
                description="Check https://docs.python.org for info",
                video_context={"video_title": "Tutorial"},
                use_llm=True,
                api_key="test-key",
            )

            assert result["total_llm_cost"] > 0
            assert len(result["llm_classifications"]) == 1
