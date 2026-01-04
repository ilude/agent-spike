"""Tests for retry decorator with exponential backoff."""

import asyncio
from unittest.mock import patch

import httpx
import pytest

from compose.lib.retry import retry_on_failure, retry_on_failure_async


class TestRetryOnFailure:
    """Tests for synchronous retry decorator."""

    def test_success_no_retry(self):
        """Function succeeds on first try - no retry needed."""
        call_count = 0

        @retry_on_failure(max_retries=3)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeed()
        assert result == "success"
        assert call_count == 1

    def test_retry_then_success(self):
        """Function fails twice then succeeds."""
        call_count = 0

        @retry_on_failure(max_retries=3, base_delay=0.01)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temporary failure")
            return "success"

        result = fail_twice()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Function fails all retries and raises."""
        call_count = 0

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("permanent failure")

        with pytest.raises(ConnectionError, match="permanent failure"):
            always_fail()

        # max_retries=2 means 3 total attempts (1 initial + 2 retries)
        assert call_count == 3

    def test_non_retryable_exception(self):
        """Non-retryable exceptions are raised immediately."""
        call_count = 0

        @retry_on_failure(max_retries=3, base_delay=0.01)
        def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            raise_value_error()

        assert call_count == 1  # No retry for ValueError

    def test_httpx_exceptions_retried(self):
        """httpx exceptions are retried."""
        call_count = 0

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def httpx_timeout():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ReadTimeout("timeout")
            return "success"

        result = httpx_timeout()
        assert result == "success"
        assert call_count == 2

    def test_custom_exceptions(self):
        """Custom exception types can be specified."""
        call_count = 0

        @retry_on_failure(max_retries=2, base_delay=0.01, exceptions=(KeyError,))
        def raise_key_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise KeyError("retry this")
            return "success"

        result = raise_key_error()
        assert result == "success"
        assert call_count == 2

    def test_exponential_backoff_timing(self):
        """Verify exponential backoff delays."""
        delays = []

        @retry_on_failure(max_retries=3, base_delay=0.1, jitter=False)
        def fail_with_timing():
            raise ConnectionError("fail")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ConnectionError):
                fail_with_timing()

            # Check delays: 0.1, 0.2, 0.4 (exponential)
            assert mock_sleep.call_count == 3
            calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert calls[0] == pytest.approx(0.1)
            assert calls[1] == pytest.approx(0.2)
            assert calls[2] == pytest.approx(0.4)

    def test_max_delay_cap(self):
        """Delay is capped at max_delay."""
        @retry_on_failure(max_retries=5, base_delay=10, max_delay=15, jitter=False)
        def fail():
            raise ConnectionError("fail")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ConnectionError):
                fail()

            # All delays should be capped at 15
            for call in mock_sleep.call_args_list:
                assert call[0][0] <= 15


class TestRetryOnFailureAsync:
    """Tests for async retry decorator."""

    @pytest.mark.asyncio
    async def test_async_success_no_retry(self):
        """Async function succeeds on first try."""
        call_count = 0

        @retry_on_failure_async(max_retries=3)
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await succeed()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_then_success(self):
        """Async function fails then succeeds."""
        call_count = 0

        @retry_on_failure_async(max_retries=3, base_delay=0.01)
        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("temporary")
            return "success"

        result = await fail_once()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_max_retries_exceeded(self):
        """Async function fails all retries."""
        call_count = 0

        @retry_on_failure_async(max_retries=2, base_delay=0.01)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("permanent")

        with pytest.raises(TimeoutError, match="permanent"):
            await always_fail()

        assert call_count == 3
