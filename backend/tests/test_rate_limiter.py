"""
Tests for the centralized rate limiter.
"""
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.core.rate_limiter import (
    SlidingWindowRateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
    with_retry,
    get_rate_limiter,
    ANGELONE_ORDER_CONFIG,
    ANGELONE_QUOTE_CONFIG,
)


class TestRateLimiter:
    """Test sliding window rate limiter."""

    @pytest.fixture
    def limiter(self):
        return SlidingWindowRateLimiter(
            "test",
            RateLimitConfig(max_calls=5, per_seconds=1.0, safety_margin=1.0)
        )

    @pytest.mark.asyncio
    async def test_allows_calls_under_limit(self, limiter):
        """Calls under the limit should be allowed immediately."""
        for i in range(5):
            result = await limiter.acquire()
            assert result.allowed is True
            assert result.calls_remaining == 4 - i

    @pytest.mark.asyncio
    async def test_blocks_at_limit(self, limiter):
        """Calls at the limit should be blocked."""
        for i in range(5):
            await limiter.acquire()
        result = await limiter.acquire()
        assert result.allowed is False
        assert result.retry_after is not None
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_wait_and_acquire(self, limiter):
        """wait_and_acquire should always return allowed=True."""
        for i in range(5):
            await limiter.acquire()
        # The 6th call should block then succeed
        result = await limiter.wait_and_acquire()
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_sliding_window_expiry(self, limiter):
        """Old timestamps should expire from the window."""
        config = RateLimitConfig(max_calls=2, per_seconds=0.1, safety_margin=1.0)
        lim = SlidingWindowRateLimiter("test_sliding", config)

        await lim.acquire()
        await lim.acquire()
        # Blocked now
        result = await lim.acquire()
        assert result.allowed is False

        # Wait for window to expire
        await asyncio.sleep(0.15)
        result = await lim.acquire()
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, limiter):
        """Circuit breaker should open after consecutive failures."""
        config = RateLimitConfig(
            max_calls=5, per_seconds=1.0, safety_margin=1.0,
            circuit_breaker_threshold=3, circuit_breaker_reset_seconds=1
        )
        lim = SlidingWindowRateLimiter("test_cb", config)

        # Record failures
        lim.record_failure(is_rate_limit=True)
        lim.record_failure(is_rate_limit=True)
        lim.record_failure(is_rate_limit=True)

        # Circuit should be open
        result = await lim.acquire()
        assert result.allowed is False
        assert result.retry_after is not None

        # Wait for circuit to reset
        await asyncio.sleep(1.1)
        result = await lim.acquire()
        assert result.allowed is True  # Half-open allows test call

    @pytest.mark.asyncio
    async def test_stats(self, limiter):
        """Stats should reflect calls and rejections."""
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()
        # All 3 under limit of 5
        stats = limiter.stats
        assert stats["total_calls"] == 3
        assert stats["rejected_calls"] == 0

        # Block the 4th and 5th (effective_max=5, so 4th succeeds, 5th blocks)
        await limiter.acquire()  # 4th succeeds
        await limiter.acquire()  # 5th succeeds (at limit now)
        result = await limiter.acquire()  # 6th blocked
        assert result.allowed is False

        stats = limiter.stats
        assert stats["total_calls"] == 5
        assert stats["rejected_calls"] >= 1


class TestRateLimitDecorator:
    """Test the with_retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Successful call should not retry."""
        config = RateLimitConfig(max_calls=100, per_seconds=1.0, safety_margin=1.0)
        lim = SlidingWindowRateLimiter("test_decorator", config)
        call_count = 0

        @with_retry(lim)
        async def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """Rate limit error should trigger retry."""
        config = RateLimitConfig(
            max_calls=1, per_seconds=1.0, safety_margin=1.0,
            max_retries=2, base_backoff_seconds=0.01, max_backoff_seconds=1
        )
        lim = SlidingWindowRateLimiter("test_retry", config)
        call_count = 0

        @with_retry(lim)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitExceededError("test", 0.1)
            return "success_after_retry"

        result = await func()
        assert result == "success_after_retry"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_exhausts_retries(self):
        """Exhausting retries should raise RateLimitExceededError."""
        config = RateLimitConfig(
            max_calls=1, per_seconds=1.0, safety_margin=1.0,
            max_retries=1, base_backoff_seconds=0.01, max_backoff_seconds=1
        )
        lim = SlidingWindowRateLimiter("test_exhaust", config)

        @with_retry(lim)
        async def func():
            raise RateLimitExceededError("test", 0.1)

        with pytest.raises(RateLimitExceededError):
            await func()


class TestRateLimitConfigs:
    """Test predefined rate limit configurations."""

    def test_angelone_order_config(self):
        assert ANGELONE_ORDER_CONFIG.max_calls == 20
        assert ANGELONE_ORDER_CONFIG.safety_margin == 0.8
        assert ANGELONE_ORDER_CONFIG.max_retries == 3

    def test_angelone_quote_config(self):
        assert ANGELONE_QUOTE_CONFIG.max_calls == 1
        assert ANGELONE_QUOTE_CONFIG.max_retries == 5

    @pytest.mark.asyncio
    async def test_get_rate_limiter_singleton(self):
        """Same name should return same limiter instance."""
        lim1 = await get_rate_limiter("singleton_test", ANGELONE_ORDER_CONFIG)
        lim2 = await get_rate_limiter("singleton_test", ANGELONE_ORDER_CONFIG)
        assert lim1 is lim2
