"""Retry decorator with exponential backoff for unreliable operations.

Provides a decorator for retrying functions that may fail due to
transient errors (network issues, service timeouts, rate limits).

Example:
    @retry_on_failure(max_retries=3, base_delay=1.0)
    def call_external_api():
        response = httpx.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
"""

import logging
import random
import time
from functools import wraps
from typing import Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default exceptions to retry on
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    httpx.RequestError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
)


def retry_on_failure(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = RETRYABLE_EXCEPTIONS,
    jitter: bool = True,
) -> Callable:
    """Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 30.0)
        exceptions: Tuple of exception types to retry on
        jitter: Add random jitter to delay to prevent thundering herd

    Returns:
        Decorated function that retries on failure

    Example:
        @retry_on_failure(max_retries=3, base_delay=2.0)
        def embed_text(text: str) -> list[float]:
            return infinity_client.embed(text)

    Backoff schedule (with base_delay=1.0):
        Attempt 1: immediate
        Attempt 2: 1s delay (+ jitter)
        Attempt 3: 2s delay (+ jitter)
        Attempt 4: 4s delay (+ jitter)
        (capped at max_delay)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.warning(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2**attempt), max_delay)

                    # Add jitter (0-25% of delay)
                    if jitter:
                        delay += random.uniform(0, delay * 0.25)

                    logger.info(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_on_failure_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = RETRYABLE_EXCEPTIONS,
    jitter: bool = True,
) -> Callable:
    """Async version of retry decorator.

    Same as retry_on_failure but for async functions.
    Uses asyncio.sleep instead of time.sleep.

    Example:
        @retry_on_failure_async(max_retries=3)
        async def fetch_data():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com")
                return response.json()
    """
    import asyncio

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.warning(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    delay = min(base_delay * (2**attempt), max_delay)
                    if jitter:
                        delay += random.uniform(0, delay * 0.25)

                    logger.info(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    await asyncio.sleep(delay)

            if last_exception:
                raise last_exception

        return wrapper

    return decorator
