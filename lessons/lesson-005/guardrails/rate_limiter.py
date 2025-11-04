"""Rate limiting for security guardrails."""

import time
from typing import Dict, Tuple
from collections import defaultdict


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, wait_seconds: float):
        self.wait_seconds = wait_seconds
        super().__init__(
            f"Rate limit exceeded. Please wait {wait_seconds:.1f} seconds before retrying."
        )


class RateLimiter:
    """
    Simple in-memory rate limiter.

    Tracks requests per user/identifier and enforces limits.
    Note: This is a simple implementation suitable for learning.
    For production, use Redis or similar distributed rate limiting.
    """

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        cooldown_seconds: int = 30,
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
            cooldown_seconds: Cooldown period after exceeding limit
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds

        # Track requests: {user_id: [(timestamp, count), ...]}
        self._requests: Dict[str, list[float]] = defaultdict(list)

        # Track cooldowns: {user_id: cooldown_until_timestamp}
        self._cooldowns: Dict[str, float] = {}

    def check_rate_limit(self, user_id: str = "default") -> None:
        """
        Check if user is within rate limits.

        Args:
            user_id: Identifier for the user/client

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        now = time.time()

        # Check if user is in cooldown
        if user_id in self._cooldowns:
            cooldown_until = self._cooldowns[user_id]
            if now < cooldown_until:
                wait_time = cooldown_until - now
                raise RateLimitExceeded(wait_time)
            else:
                # Cooldown expired, remove it
                del self._cooldowns[user_id]

        # Clean up old requests outside the window
        window_start = now - self.window_seconds
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts >= window_start
        ]

        # Check current request count
        current_count = len(self._requests[user_id])

        if current_count >= self.max_requests:
            # Rate limit exceeded, add cooldown
            self._cooldowns[user_id] = now + self.cooldown_seconds
            raise RateLimitExceeded(self.cooldown_seconds)

        # Record this request
        self._requests[user_id].append(now)

    def get_remaining_requests(self, user_id: str = "default") -> Tuple[int, float]:
        """
        Get remaining requests for user.

        Args:
            user_id: Identifier for the user/client

        Returns:
            Tuple of (remaining_requests, window_reset_seconds)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean up old requests
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts >= window_start
        ]

        current_count = len(self._requests[user_id])
        remaining = max(0, self.max_requests - current_count)

        # Calculate window reset time
        if self._requests[user_id]:
            oldest_request = min(self._requests[user_id])
            reset_in = self.window_seconds - (now - oldest_request)
        else:
            reset_in = 0

        return remaining, reset_in

    def reset_user(self, user_id: str) -> None:
        """
        Reset rate limit for a user.

        Args:
            user_id: Identifier for the user/client
        """
        if user_id in self._requests:
            del self._requests[user_id]
        if user_id in self._cooldowns:
            del self._cooldowns[user_id]

    def reset_all(self) -> None:
        """Reset rate limits for all users."""
        self._requests.clear()
        self._cooldowns.clear()


# Global rate limiter instance
_global_limiter = RateLimiter(max_requests=60, window_seconds=60, cooldown_seconds=30)


def check_rate_limit(user_id: str = "default") -> None:
    """
    Check rate limit using global limiter.

    Args:
        user_id: Identifier for the user/client

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    _global_limiter.check_rate_limit(user_id)


def get_remaining_requests(user_id: str = "default") -> Tuple[int, float]:
    """
    Get remaining requests using global limiter.

    Args:
        user_id: Identifier for the user/client

    Returns:
        Tuple of (remaining_requests, window_reset_seconds)
    """
    return _global_limiter.get_remaining_requests(user_id)


def reset_rate_limit(user_id: str = "default") -> None:
    """
    Reset rate limit for a user using global limiter.

    Args:
        user_id: Identifier for the user/client
    """
    _global_limiter.reset_user(user_id)
