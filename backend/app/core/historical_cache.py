"""
Local historical candle cache.

Avoids repeated Angel One API calls for the same historical data by caching
candles locally as JSON files. On each request:
- Checks cache for existing candles
- Computes missing date ranges
- Fetches only missing ranges from the broker API
- Merges and returns complete dataset
- Persists new candles to disk

Cache layout:
    cache/historical/{exchange}_{symbol_token}_{interval}.json

Each file contains:
{
    "exchange": "NSE",
    "symbol_token": "99926000",
    "interval": "5m",
    "cached_at": "2026-11-20T13:00:00",
    "candles": [
        {"timestamp": "2026-11-20 09:15:00", "open": 22500, "high": 22510, "low": 22490, "close": 22500, "volume": 1000},
        ...
    ]
}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class HistoricalCache:
    """
    File-based cache for historical candle data.

    Thread/async-safe via asyncio.Lock. Uses JSON files for simplicity —
    no additional database or migration required.
    """

    def __init__(self, cache_dir: str = "cache/historical", max_age_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(hours=max_age_hours)
        self._lock = asyncio.Lock()
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._memory_loaded: Dict[str, bool] = {}

    def _cache_path(self, exchange: str, symbol_token: str, interval: str) -> Path:
        safe_token = symbol_token.replace("/", "_").replace("\\", "_")
        filename = f"{exchange}_{safe_token}_{interval}.json"
        return self.cache_dir / filename

    def _cache_key(self, exchange: str, symbol_token: str, interval: str) -> str:
        return f"{exchange}:{symbol_token}:{interval}"

    async def _load_from_disk(self, exchange: str, symbol_token: str, interval: str) -> Optional[Dict[str, Any]]:
        """Load cache entry from disk (with asyncio thread executor for file I/O)."""
        key = self._cache_key(exchange, symbol_token, interval)
        path = self._cache_path(exchange, symbol_token, interval)

        if not path.exists():
            return None

        loop = asyncio.get_event_loop()

        def _read() -> Optional[Dict[str, Any]]:
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read cache file {path}: {e}")
                return None

        data = await loop.run_in_executor(None, _read)
        if data:
            self._memory_cache[key] = data
            self._memory_loaded[key] = True
        return data

    async def _save_to_disk(self, exchange: str, symbol_token: str, interval: str, data: Dict[str, Any]) -> None:
        """Save cache entry to disk."""
        key = self._cache_key(exchange, symbol_token, interval)
        path = self._cache_path(exchange, symbol_token, interval)
        # Only set cached_at if not already present (preserve existing timestamps)
        if "cached_at" not in data or not data["cached_at"]:
            data["cached_at"] = datetime.now(IST).isoformat()

        loop = asyncio.get_event_loop()

        def _write() -> None:
            tmp_path = path.with_suffix(".json.tmp")
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, path)

        await loop.run_in_executor(None, _write)
        self._memory_cache[key] = data
        self._memory_loaded[key] = True

    def _is_stale(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is older than max_age."""
        cached_at_str = entry.get("cached_at")
        if not cached_at_str:
            return True
        cached_at = self._parse_iso_timestamp(cached_at_str)
        if cached_at is None:
            return True
        return datetime.now(IST) - cached_at > self.max_age

    def _parse_iso_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse ISO timestamp string, handling Python 3.9 timezone offset limitations."""
        try:
            # Python 3.9 fromisoformat doesn't handle +HH:MM offsets well
            # Try direct fromisoformat first
            try:
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=IST)
                return dt
            except ValueError:
                pass
            # Manual parse: try common formats without timezone
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    dt = datetime.strptime(ts_str, fmt)
                    return dt.replace(tzinfo=IST)
                except ValueError:
                    continue
            # Last resort: strip everything after the seconds
            try:
                dt = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
                return dt.replace(tzinfo=IST)
            except ValueError:
                return None
        except Exception:
            return None
        except Exception:
            return None

    def _parse_candle_timestamp(self, ts: Any) -> Optional[datetime]:
        """Parse a candle timestamp from various formats."""
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=IST)
            return ts
        if isinstance(ts, str):
            # Try fromisoformat first (handles timezone-aware ISO strings)
            try:
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=IST)
                return dt
            except ValueError:
                pass
            # Fall back to strptime for naive format strings
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    return datetime.strptime(ts, fmt).replace(tzinfo=IST)
                except ValueError:
                    continue
        return None

    def _candles_to_dict(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize candles to dict format with ISO timestamps."""
        normalized = []
        for c in candles:
            ts = c.get("timestamp") or c.get("time") or c.get("datetime")
            dt = self._parse_candle_timestamp(ts)
            if dt is None:
                continue
            normalized.append({
                "timestamp": dt.isoformat(),
                "open": float(c.get("open", 0)),
                "high": float(c.get("high", 0)),
                "low": float(c.get("low", 0)),
                "close": float(c.get("close", 0)),
                "volume": int(c.get("volume", 0)),
                "oi": int(c.get("oi", 0)) if c.get("oi") else None,
            })
        return normalized

    def _dict_to_candles(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert cached dict back to candle format."""
        return data  # Already normalized

    async def get_cached_candles(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[datetime, datetime]]]:
        """
        Get candles from cache, returning (cached_candles, missing_ranges).

        missing_ranges is a list of (start, end) datetime tuples that need
        to be fetched from the broker API.
        """
        async with self._lock:
            key = self._cache_key(exchange, symbol_token, interval)

            if not self._memory_loaded.get(key):
                entry = await self._load_from_disk(exchange, symbol_token, interval)
            else:
                entry = self._memory_cache.get(key)

            if not entry or self._is_stale(entry):
                # Cache empty or stale — need full fetch
                return [], [(from_date, to_date)]

            cached_candles = entry.get("candles", [])
            if not cached_candles:
                return [], [(from_date, to_date)]

            # Parse cached candle timestamps
            cached_by_ts: Dict[datetime, Dict[str, Any]] = {}
            for c in cached_candles:
                dt = self._parse_candle_timestamp(c.get("timestamp"))
                if dt:
                    cached_by_ts[dt] = c

            # Find which candles in [from_date, to_date] are missing
            cached_candles_in_range = []
            missing_ranges = []

            # Walk through the requested range in 1-day chunks to find gaps
            current = from_date
            while current <= to_date:
                day_start = current.replace(hour=9, minute=15, second=0, microsecond=0)
                day_end = current.replace(hour=15, minute=30, second=0, microsecond=0)

                # Check if we have candles for this day
                day_candles = [c for ts, c in cached_by_ts.items() if day_start <= ts <= day_end]

                if not day_candles:
                    # Entire day missing
                    missing_ranges.append((current, min(current + timedelta(days=1), to_date)))
                else:
                    # Day partially cached — find gaps within the day
                    # For simplicity, if we have any candles for the day, assume it's covered
                    # (Angel One 5-min candles: 75 per day; if we have some, we likely have most)
                    day_candles_sorted = sorted(day_candles, key=lambda c: self._parse_candle_timestamp(c.get("timestamp")))
                    cached_candles_in_range.extend(day_candles_sorted)

                current += timedelta(days=1)

            return cached_candles_in_range, missing_ranges

    async def store_candles(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        candles: List[Dict[str, Any]],
    ) -> None:
        """Merge and store candles to cache."""
        async with self._lock:
            key = self._cache_key(exchange, symbol_token, interval)

            if not self._memory_loaded.get(key):
                entry = await self._load_from_disk(exchange, symbol_token, interval)
            else:
                entry = self._memory_cache.get(key)

            if not entry:
                entry = {
                    "exchange": exchange,
                    "symbol_token": symbol_token,
                    "interval": interval,
                    "candles": [],
                }

            # Merge new candles (avoid duplicates by timestamp)
            existing_by_ts: Dict[datetime, Dict[str, Any]] = {}
            for c in entry.get("candles", []):
                dt = self._parse_candle_timestamp(c.get("timestamp"))
                if dt:
                    existing_by_ts[dt] = c

            for c in self._candles_to_dict(candles):
                dt = self._parse_candle_timestamp(c.get("timestamp"))
                if dt:
                    existing_by_ts[dt] = c

            # Sort by timestamp
            all_candles = sorted(
                existing_by_ts.values(),
                key=lambda c: self._parse_candle_timestamp(c.get("timestamp")) or datetime.min,
            )

            entry["candles"] = all_candles
            await self._save_to_disk(exchange, symbol_token, interval, entry)
            logger.info(
                f"Cached {len(candles)} candles for {exchange}:{symbol_token}:{interval} "
                f"(total: {len(all_candles)})"
            )

    async def clear_stale(self) -> int:
        """Remove cache entries older than max_age. Returns count cleared."""
        cleared = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if self._is_stale(data):
                    path.unlink()
                    cleared += 1
                    key = self._cache_key(data.get("exchange", ""), data.get("symbol_token", ""), data.get("interval", ""))
                    self._memory_cache.pop(key, None)
                    self._memory_loaded.pop(key, None)
            except Exception as e:
                logger.warning(f"Failed to check cache file {path}: {e}")
        return cleared

    def get_stats(self) -> Dict[str, Any]:
        files = list(self.cache_dir.glob("*.json"))
        total_candles = 0
        for f in files:
            try:
                with open(f, "r") as fh:
                    data = json.load(fh)
                total_candles += len(data.get("candles", []))
            except Exception:
                pass
        return {
            "cache_dir": str(self.cache_dir),
            "cache_files": len(files),
            "total_candles": total_candles,
            "max_age_hours": self.max_age.total_seconds() / 3600,
        }


# Singleton instance
historical_cache = HistoricalCache()
