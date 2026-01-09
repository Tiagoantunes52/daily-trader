"""Tests for rate limiter service."""

import time

from src.services.rate_limiter import RateLimiter


class TestRateLimiterUnitTests:
    """Unit tests for rate limiter security features."""

    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within the limit."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 5
        window = 60

        # First 5 requests should be allowed
        for _i in range(5):
            allowed, info = rate_limiter.is_allowed(client_id, limit, window)
            assert allowed is True
            assert info["limit"] == limit

    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that rate limiter blocks requests over the limit."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 3
        window = 60

        # First 3 requests should be allowed
        for _i in range(3):
            allowed, info = rate_limiter.is_allowed(client_id, limit, window)
            assert allowed is True

        # 4th request should be blocked
        allowed, info = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is False
        assert "retry_after" in info

    def test_rate_limiter_resets_after_window(self):
        """Test that rate limiter resets after the time window."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 2
        window = 1

        # Use up the limit
        allowed1, _ = rate_limiter.is_allowed(client_id, limit, window)
        allowed2, _ = rate_limiter.is_allowed(client_id, limit, window)
        allowed3, _ = rate_limiter.is_allowed(client_id, limit, window)

        assert allowed1 is True
        assert allowed2 is True
        assert allowed3 is False

        # Wait for window to reset
        time.sleep(1.1)

        # Should be allowed again
        allowed4, _ = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed4 is True

    def test_rate_limiter_different_clients_independent(self):
        """Test that different clients have independent rate limits."""
        rate_limiter = RateLimiter()
        client1 = "client1"
        client2 = "client2"
        limit = 2
        window = 60

        # Client 1 uses up limit
        allowed1, _ = rate_limiter.is_allowed(client1, limit, window)
        allowed2, _ = rate_limiter.is_allowed(client1, limit, window)
        allowed3, _ = rate_limiter.is_allowed(client1, limit, window)

        assert allowed1 is True
        assert allowed2 is True
        assert allowed3 is False

        # Client 2 should still be allowed
        allowed4, _ = rate_limiter.is_allowed(client2, limit, window)
        allowed5, _ = rate_limiter.is_allowed(client2, limit, window)
        allowed6, _ = rate_limiter.is_allowed(client2, limit, window)

        assert allowed4 is True
        assert allowed5 is True
        assert allowed6 is False

    def test_rate_limiter_remaining_requests_info(self):
        """Test rate limit info includes remaining requests."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 5
        window = 60

        # Initially should have full limit
        allowed, info = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is True
        assert info["remaining"] == 4  # After making the request

        # After another request
        allowed, info = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is True
        assert info["remaining"] == 3

    def test_rate_limiter_reset_time_info(self):
        """Test rate limit info includes reset time."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 3
        window = 60

        # Make a request to start the window
        allowed, info = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is True

        current_time = time.time()
        reset_time = info["reset_time"]

        # Reset time should be within the window
        assert reset_time > current_time
        assert reset_time <= current_time + window + 1  # Allow for small timing differences

    def test_rate_limiter_clear_key(self):
        """Test clearing requests for a specific key."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 2
        window = 60

        # Make requests
        rate_limiter.is_allowed(client_id, limit, window)
        rate_limiter.is_allowed(client_id, limit, window)

        # Should be at limit
        allowed, _ = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is False

        # Clear the key
        rate_limiter.clear_key(client_id)

        # Should be allowed again
        allowed, _ = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is True

    def test_rate_limiter_clear_all(self):
        """Test clearing all requests."""
        rate_limiter = RateLimiter()
        client1 = "client1"
        client2 = "client2"
        limit = 1
        window = 60

        # Make requests for both clients
        rate_limiter.is_allowed(client1, limit, window)
        rate_limiter.is_allowed(client2, limit, window)

        # Both should be at limit
        allowed1, _ = rate_limiter.is_allowed(client1, limit, window)
        allowed2, _ = rate_limiter.is_allowed(client2, limit, window)
        assert allowed1 is False
        assert allowed2 is False

        # Clear all
        rate_limiter.clear_all()

        # Both should be allowed again
        allowed1, _ = rate_limiter.is_allowed(client1, limit, window)
        allowed2, _ = rate_limiter.is_allowed(client2, limit, window)
        assert allowed1 is True
        assert allowed2 is True

    def test_rate_limiter_get_stats(self):
        """Test getting statistics for a key."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 3
        window = 60

        # Initially no requests
        stats = rate_limiter.get_stats(client_id)
        assert stats["current_requests"] == 0
        assert stats["key"] == client_id

        # Make some requests
        rate_limiter.is_allowed(client_id, limit, window)
        rate_limiter.is_allowed(client_id, limit, window)

        # Check stats
        stats = rate_limiter.get_stats(client_id)
        assert stats["current_requests"] == 2
        assert len(stats["request_timestamps"]) == 2

    def test_rate_limiter_with_zero_limit(self):
        """Test rate limiter with zero limit blocks all requests."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 0
        window = 60

        # All requests should be blocked
        allowed1, _ = rate_limiter.is_allowed(client_id, limit, window)
        allowed2, _ = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed1 is False
        assert allowed2 is False

    def test_rate_limiter_with_negative_limit(self):
        """Test rate limiter with negative limit blocks all requests."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = -1
        window = 60

        # All requests should be blocked
        allowed, _ = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is False

    def test_rate_limiter_empty_client_id(self):
        """Test rate limiter with empty client ID."""
        rate_limiter = RateLimiter()
        limit = 5
        window = 60

        # Empty client ID should be handled gracefully
        allowed, info = rate_limiter.is_allowed("", limit, window)
        assert allowed is True
        assert info["remaining"] >= 0

    def test_rate_limiter_retry_after_info(self):
        """Test that retry_after is provided when rate limited."""
        rate_limiter = RateLimiter()
        client_id = "test_client"
        limit = 1
        window = 60

        # Use up the limit
        allowed1, _ = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed1 is True

        # Next request should be blocked with retry_after
        allowed2, info = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed2 is False
        assert "retry_after" in info
        assert info["retry_after"] > 0
