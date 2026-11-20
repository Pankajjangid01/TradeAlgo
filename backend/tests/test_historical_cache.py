"""
Tests for historical data cache.
"""
import pytest
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

from app.core.historical_cache import HistoricalCache, historical_cache


class TestHistoricalCache:
    """Test file-based historical candle cache."""

    @pytest.fixture
    def cache(self):
        """Create a temporary cache instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, "cache", "historical")
            c = HistoricalCache(cache_dir=cache_dir, max_age_hours=24)
            yield c

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, cache):
        """Store candles and retrieve them from cache."""
        candles = [
            {"timestamp": "2026-01-01 09:15:00", "open": 19800, "high": 19810, "low": 19790, "close": 19800, "volume": 1000},
            {"timestamp": "2026-01-01 09:20:00", "open": 19800, "high": 19820, "low": 19795, "close": 19810, "volume": 1200},
        ]

        await cache.store_candles("NSE", "99926000", "5m", candles)

        from_date = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
        to_date = datetime(2026, 1, 1, 10, 0, tzinfo=IST)

        cached, missing = await cache.get_cached_candles("NSE", "99926000", "5m", from_date, to_date)
        assert len(cached) == 2
        assert len(missing) == 0

    @pytest.mark.asyncio
    async def test_empty_cache_returns_missing(self, cache):
        """Empty cache should report all ranges as missing."""
        from_date = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
        to_date = datetime(2026, 1, 1, 10, 0, tzinfo=IST)

        cached, missing = await cache.get_cached_candles("NSE", "99926000", "5m", from_date, to_date)
        assert len(cached) == 0
        assert len(missing) == 1

    @pytest.mark.asyncio
    async def test_stale_cache_returns_missing(self, cache):
        """Stale cache (older than max_age) should be treated as missing."""
        candles = [
            {"timestamp": "2026-01-01 09:15:00", "open": 19800, "high": 19810, "low": 19790, "close": 19800, "volume": 1000},
        ]
        await cache.store_candles("NSE", "99926000", "5m", candles)

        # Manually set stale timestamp
        key = "NSE:99926000:5m"
        cache._memory_cache[key]["cached_at"] = "2020-01-01T00:00:00+05:30"
        await cache._save_to_disk("NSE", "99926000", "5m", cache._memory_cache[key])

        from_date = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
        to_date = datetime(2026, 1, 1, 10, 0, tzinfo=IST)

        cached, missing = await cache.get_cached_candles("NSE", "99926000", "5m", from_date, to_date)
        assert len(cached) == 0
        assert len(missing) == 1

    @pytest.mark.asyncio
    async def test_merge_avoids_duplicates(self, cache):
        """Merging candles should not create duplicates."""
        candles1 = [
            {"timestamp": "2026-01-01 09:15:00", "open": 19800, "high": 19810, "low": 19790, "close": 19800, "volume": 1000},
        ]
        candles2 = [
            {"timestamp": "2026-01-01 09:15:00", "open": 19800, "high": 19810, "low": 19790, "close": 19800, "volume": 1000},  # duplicate
            {"timestamp": "2026-01-01 09:20:00", "open": 19810, "high": 19820, "low": 19800, "close": 19810, "volume": 1200},
        ]

        await cache.store_candles("NSE", "99926000", "5m", candles1)
        await cache.store_candles("NSE", "99926000", "5m", candles2)

        from_date = datetime(2026, 1, 1, 9, 15, tzinfo=IST)
        to_date = datetime(2026, 1, 1, 10, 0, tzinfo=IST)

        cached, missing = await cache.get_cached_candles("NSE", "99926000", "5m", from_date, to_date)
        assert len(cached) == 2  # No duplicate

    def test_stats(self, cache):
        """Stats should return cache info."""
        stats = cache.get_stats()
        assert "cache_dir" in stats
        assert "cache_files" in stats
        assert "total_candles" in stats

    @pytest.mark.asyncio
    async def test_clear_stale(self, cache):
        """Stale entries should be cleared."""
        candles = [
            {"timestamp": "2026-01-01 09:15:00", "open": 19800, "high": 19810, "low": 19790, "close": 19800, "volume": 1000},
        ]
        await cache.store_candles("NSE", "99926000", "5m", candles)

        # Make it stale
        key = "NSE:99926000:5m"
        cache._memory_cache[key]["cached_at"] = "2020-01-01T00:00:00+05:30"
        await cache._save_to_disk("NSE", "99926000", "5m", cache._memory_cache[key])

        cleared = await cache.clear_stale()
        assert cleared >= 1
