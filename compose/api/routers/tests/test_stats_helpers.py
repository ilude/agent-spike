"""Tests for stats router helper functions.

Run with: uv run pytest compose/api/routers/tests/test_stats_helpers.py
"""

import pytest

from compose.api.routers.stats import is_local_url


# -----------------------------------------------------------------------------
# is_local_url Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestIsLocalUrl:
    """Test is_local_url helper function."""

    def test_localhost_returns_true(self):
        """localhost URLs should be considered local."""
        assert is_local_url("http://localhost:8080") is True
        assert is_local_url("https://localhost/api") is True
        assert is_local_url("http://localhost") is True

    def test_127_0_0_1_returns_true(self):
        """127.0.0.1 URLs should be considered local."""
        assert is_local_url("http://127.0.0.1:6333") is True
        assert is_local_url("https://127.0.0.1/health") is True

    def test_0_0_0_0_returns_true(self):
        """0.0.0.0 URLs should be considered local."""
        assert is_local_url("http://0.0.0.0:8000") is True

    def test_host_docker_internal_returns_true(self):
        """host.docker.internal URLs should be considered local."""
        assert is_local_url("http://host.docker.internal:5432") is True

    def test_docker_service_names_return_true(self):
        """Docker service names should be considered local."""
        assert is_local_url("http://surrealdb:8000") is True
        assert is_local_url("http://infinity:7997") is True
        assert is_local_url("http://api:8000") is True
        assert is_local_url("http://frontend:3000") is True
        assert is_local_url("http://docling:5001") is True
        assert is_local_url("http://minio:9000") is True

    def test_external_urls_return_false(self):
        """External URLs should not be considered local."""
        assert is_local_url("http://google.com") is False
        assert is_local_url("https://openai.com") is False
        assert is_local_url("http://192.168.1.100:8080") is False
        assert is_local_url("https://example.com/endpoint") is False

    def test_case_insensitive(self):
        """URL check should be case insensitive."""
        assert is_local_url("http://LOCALHOST:8080") is True
        assert is_local_url("http://Surrealdb:8000") is True
