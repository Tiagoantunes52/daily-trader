"""Rate limiting service for API endpoints."""

import time
from collections import defaultdict


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    This implementation uses a sliding window approach to track requests
    and enforce rate limits based on IP addresses or other keys.
    """

    def __init__(self):
        """Initialize the rate limiter with empty request tracking."""
        # Dictionary to store request timestamps for each key
        # Format: {key: [timestamp1, timestamp2, ...]}
        self._requests: dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, dict]:
        """
        Check if a request is allowed based on rate limiting rules.

        Args:
            key: Unique identifier for the client (e.g., IP address)
            limit: Maximum number of requests allowed in the time window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_info) where:
            - is_allowed: Boolean indicating if request is allowed
            - rate_info: Dictionary with rate limit information
        """
        current_time = time.time()
        window_start = current_time - window_seconds

        # Clean up old requests outside the current window
        self._requests[key] = [
            timestamp for timestamp in self._requests[key] if timestamp > window_start
        ]

        # Count current requests in the window
        current_count = len(self._requests[key])

        # Calculate remaining requests
        remaining = max(0, limit - current_count)

        # Calculate reset time (when the oldest request will expire)
        reset_time = int(current_time + window_seconds)
        if self._requests[key]:
            oldest_request = min(self._requests[key])
            reset_time = int(oldest_request + window_seconds)

        # Prepare rate limit information
        rate_info = {
            "limit": limit,
            "remaining": remaining,
            "reset_time": reset_time,
            "window_seconds": window_seconds,
        }

        # Check if request is allowed
        if current_count >= limit:
            # Calculate retry after time
            if self._requests[key]:
                oldest_request = min(self._requests[key])
                retry_after = int((oldest_request + window_seconds) - current_time)
                rate_info["retry_after"] = max(1, retry_after)
            else:
                rate_info["retry_after"] = window_seconds

            return False, rate_info

        # Request is allowed, record it
        self._requests[key].append(current_time)
        rate_info["remaining"] = remaining - 1

        return True, rate_info

    def clear_key(self, key: str) -> None:
        """
        Clear all requests for a specific key.

        Args:
            key: The key to clear
        """
        if key in self._requests:
            del self._requests[key]

    def clear_all(self) -> None:
        """Clear all stored requests."""
        self._requests.clear()

    def get_stats(self, key: str) -> dict:
        """
        Get current statistics for a key.

        Args:
            key: The key to get stats for

        Returns:
            Dictionary with current request count and timestamps
        """
        return {
            "key": key,
            "current_requests": len(self._requests[key]),
            "request_timestamps": self._requests[key].copy(),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()
