"""
Centralized async rate limiter for broker API calls.

Implements a sliding-window rate limiter with:
- Endpoint-specific rate limits (orders vs quotes vs historical)
- Configurable safety margins (default 80% of documented broker limits)
- Exponential backoff with jitter on rate-limit errors
- Circuit breaker for repeated failures
- Async-safe (asyncio.Lock) for FastAPI concurrency

Angel One documented limits (verified against smartapi-python source):
- Orders: 20 requests/second
- Quotes: 1 request/second (up to 50 symbols per exchange per call)
- Historical: not explicitly documented, treated conservatively

TradeIQ safety margin: 80% of documented limit by default.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RateLimitConfig:
    """Configuration for a single endpoint's rate limiter."""

    max_calls: int
    per_seconds: float = 1.0
    safety_margin: float = 0.8  # Use 80% of documented limit
    max_retries: int = 3
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    circuit_breaker_threshold: int = 5  # consecutive failures to open circuit
    circuit_breaker_reset_seconds: float = 30.0


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after: Optional[float] = None
    calls_remaining: int = 0
    reset_at: Optional[float] = None


class SlidingWindowRateLimiter:
    """
    Async-safe sliding window rate limiter.

    Tracks request timestamps in a deque. On each acquire():
    - Evicts timestamps outside the window
    - If under limit, records the timestamp and allows the call
    - If at limit, calculates wait time until oldest call exits window
    """

    def __init__(self, name: str, config: RateLimitConfig):
        self.name = name
        self.config = config
        self._effective_max = max(1, int(config.max_calls * config.safety_margin))
        self._timestamps: deque = deque()
        self._lock = asyncio.Lock()
        self._consecutive_failures = 0
        self._circuit_state = CircuitState.CLOSED
        self._circuit_opened_at: Optional[float] = None
        self._total_calls = 0
        self._rejected_calls = 0
        self._rate_limited_calls = 0

    @property
    def effective_max(self) -> int:
        return self._effective_max

    @property
    def stats(self) -> Dict[str, any]:
        return {
            "name": self.name,
            "effective_max_calls": self._effective_max,
            "window_seconds": self.config.per_seconds,
            "total_calls": self._total_calls,
            "rejected_calls": self._rejected_calls,
            "rate_limited_calls": self._rate_limited_calls,
            "circuit_state": self._circuit_state.value,
            "consecutive_failures": self._consecutive_failures,
        }

    async def acquire(self) -> RateLimitResult:
        """
        Acquire permission to make an API call. Blocks until allowed.

        Returns RateLimitResult with allowance status and retry info.
        """
        async with self._lock:
            # Check circuit breaker
            if self._circuit_state == CircuitState.OPEN:
                now = time.monotonic()
                if self._circuit_opened_at and now - self._circuit_opened_at >= self.config.circuit_breaker_reset_seconds:
                    self._circuit_state = CircuitState.HALF_OPEN
                    logger.info(f"Rate limiter {self.name}: circuit half-open, allowing test call")
                else:
                    self._rejected_calls += 1
                    return RateLimitResult(
                        allowed=False,
                        retry_after=self.config.circuit_breaker_reset_seconds,
                        calls_remaining=0,
                    )

            now = time.monotonic()
            window_start = now - self.config.per_seconds

            # Evict old timestamps
            while self._timestamps and self._timestamps[0] < window_start:
                self._timestamps.popleft()

            if len(self._timestamps) < self._effective_max:
                self._timestamps.append(now)
                self._total_calls += 1
                self._consecutive_failures = 0
                if self._circuit_state == CircuitState.HALF_OPEN:
                    self._circuit_state = CircuitState.CLOSED
                    logger.info(f"Rate limiter {self.name}: circuit closed after successful call")
                return RateLimitResult(
                    allowed=True,
                    calls_remaining=self._effective_max - len(self._timestamps),
                    reset_at=now + self.config.per_seconds,
                )

            # Rate limited - calculate wait time
            wait_time = self.config.per_seconds - (now - self._timestamps[0])
            self._rate_limited_calls += 1
            self._rejected_calls += 1
            logger.warning(
                f"Rate limiter {self.name}: limit reached ({len(self._timestamps)}/{self._effective_max}), "
                f"wait {wait_time:.2f}s"
            )
            return RateLimitResult(
                allowed=False,
                retry_after=max(wait_time, 0.001),
                calls_remaining=0,
                reset_at=self._timestamps[0] + self.config.per_seconds,
            )

    async def wait_and_acquire(self) -> RateLimitResult:
        """
        Block until a call slot is available, then acquire it.
        Never returns rejected - always waits.
        """
        while True:
            result = await self.acquire()
            if result.allowed:
                return result
            wait_for = result.retry_after or 0.1
            await asyncio.sleep(min(wait_for, 1.0))

    def record_failure(self, is_rate_limit: bool = False) -> None:
        """Record a failed API call for circuit breaker tracking."""
        self._consecutive_failures += 1
        if is_rate_limit:
            self._rate_limited_calls += 1
        if self._consecutive_failures >= self.config.circuit_breaker_threshold:
            if self._circuit_state != CircuitState.OPEN:
                self._circuit_state = CircuitState.OPEN
                self._circuit_opened_at = time.monotonic()
                logger.error(
                    f"Rate limiter {self.name}: circuit OPEN after "
                    f"{self._consecutive_failures} consecutive failures"
                )

    def record_success(self) -> None:
        """Record a successful API call."""
        self._consecutive_failures = 0
        if self._circuit_state == CircuitState.HALF_OPEN:
            self._circuit_state = CircuitState.CLOSED
            logger.info(f"Rate limiter {self.name}: circuit closed")


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded and circuit is open."""

    def __init__(self, limiter_name: str, retry_after: float):
        self.limiter_name = limiter_name
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {limiter_name}, retry after {retry_after:.1f}s")


def with_retry(
    limiter: SlidingWindowRateLimiter,
    max_retries: Optional[int] = None,
    base_backoff: Optional[float] = None,
    max_backoff: Optional[float] = None,
    jitter: bool = True,
):
    """
    Decorator that wraps an async function with rate limiting and retry logic.

    On rate-limit error (HTTP 429/403 with rate-limit message), waits with
    exponential backoff and retries.
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            retries = max_retries if max_retries is not None else limiter.config.max_retries
            base = base_backoff if base_backoff is not None else limiter.config.base_backoff_seconds
            max_b = max_backoff if max_backoff is not None else limiter.config.max_backoff_seconds

            last_exception = None
            for attempt in range(retries + 1):
                # Wait for a slot
                result = await limiter.wait_and_acquire()

                try:
                    response = await func(*args, **kwargs)
                    limiter.record_success()
                    return response

                except RateLimitExceededError as exc:
                    limiter.record_failure(is_rate_limit=True)
                    last_exception = exc
                    if attempt < retries:
                        wait = min(base * (2 ** attempt), max_b)
                        if jitter:
                            wait = wait * (0.5 + random.random())
                        logger.warning(
                            f"Rate limit hit on {func.__name__}, retry {attempt + 1}/{retries} "
                            f"after {wait:.1f}s"
                        )
                        await asyncio.sleep(wait)
                    else:
                        raise

                except Exception as exc:
                    # Check if this looks like a rate-limit error from the broker
                    error_msg = str(exc).lower()
                    is_rate_limit = any(
                        keyword in error_msg
                        for keyword in ["rate limit", "429", "too many requests", "throttle"]
                    )
                    limiter.record_failure(is_rate_limit=is_rate_limit)
                    last_exception = exc

                    if is_rate_limit and attempt < retries:
                        wait = min(base * (2 ** attempt), max_b)
                        if jitter:
                            wait = wait * (0.5 + random.random())
                        logger.warning(
                            f"Rate-limit error on {func.__name__}, retry {attempt + 1}/{retries} "
                            f"after {wait:.1f}s: {exc}"
                        )
                        await asyncio.sleep(wait)
                    else:
                        raise

            raise last_exception

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Centralized registry - one limiter per endpoint type, shared across all clients
# ---------------------------------------------------------------------------

_rate_limiters: Dict[str, SlidingWindowRateLimiter] = {}
_registry_lock = asyncio.Lock()


async def get_rate_limiter(name: str, config: RateLimitConfig) -> SlidingWindowRateLimiter:
    """Get or create a named rate limiter (singleton per name)."""
    async with _registry_lock:
        if name not in _rate_limiters:
            _rate_limiters[name] = SlidingWindowRateLimiter(name, config)
            logger.info(
                f"Created rate limiter '{name}': {config.max_calls} calls/{config.per_seconds}s "
                f"(effective: {_rate_limiters[name].effective_max} with {config.safety_margin:.0%} margin)"
            )
        return _rate_limiters[name]


async def get_all_limiter_stats() -> list:
    """Return stats for all registered rate limiters."""
    async with _registry_lock:
        return [limiter.stats for limiter in _rate_limiters.values()]


# Default Angel One rate limit configurations
ANGELONE_ORDER_CONFIG = RateLimitConfig(
    max_calls=20,
    per_seconds=1.0,
    safety_margin=0.8,  # 16 effective calls/sec
    max_retries=3,
    base_backoff_seconds=1.0,
    max_backoff_seconds=30.0,
)

ANGELONE_QUOTE_CONFIG = RateLimitConfig(
    max_calls=1,
    per_seconds=1.0,
    safety_margin=0.8,  # 0.8 -> 1 effective call/sec (min 1)
    max_retries=5,
    base_backoff_seconds=2.0,
    max_backoff_seconds=30.0,
)

ANGELONE_HISTORICAL_CONFIG = RateLimitConfig(
    max_calls=5,
    per_seconds=1.0,
    safety_margin=0.8,
    max_retries=3,
    base_backoff_seconds=2.0,
    max_backoff_seconds=30.0,
)

FLATTRADE_CONFIG = RateLimitConfig(
    max_calls=10,
    per_seconds=1.0,
    safety_margin=0.8,
    max_retries=3,
    base_backoff_seconds=1.0,
    max_backoff_seconds=30.0,
)
