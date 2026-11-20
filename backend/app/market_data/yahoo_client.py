"""
Yahoo Finance market data client for TradeIQ.
Provides live NSE prices, historical OHLCV, and instrument lookup via Yahoo Finance
(free, no API key). Used for the live market data feed; Angel One SmartAPI is retained
only for order placement.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import quote

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://query1.finance.yahoo.com"

SYMBOL_ALIASES = {
    "IOCL": "IOC",
    "MOTHERSUMI": "MOTHERSON",
    "ADANIGAS": "ATGL",
    "CADILAHC": "ZYDUSLIFE",
    "MINDTREE": "LTIM",
    "L&TFH": "LTF",
}

NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC",
    "KOTAKBANK", "LT", "SBIN", "AXISBANK", "BAJFINANCE", "BHARTIARTL", "ASIANPAINT",
    "HCLTECH", "MARUTI", "SUNPHARMA", "TITAN", "NESTLEIND", "WIPRO", "ULTRACEMCO",
    "NTPC", "POWERGRID", "TECHM", "TATAMOTORS", "BAJAJ-AUTO", "DRREDDY", "DIVISLAB",
    "CIPLA", "COALINDIA", "ONGC", "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS",
    "INDUSINDBK", "BAJAJFINSV", "HEROMOTOCO", "EICHERMOT", "GRASIM",
    "HDFCLIFE", "SBILIFE", "APOLLOHOSP", "TATACONSUM", "BEL",
    "HINDALCO", "LTIM", "M&M", "SHRIRAMFIN", "TRENT",
]

INDEX_TICKERS = {
    "NIFTY50": "^NSEI",
    "NIFTY 50": "^NSEI",
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
    "BANK NIFTY": "^NSEBANK",
    "NIFTYMID": "^NSEMDCP50",
    "INDIAVIX": "^INDIAVIX",
    "INDIA VIX": "^INDIAVIX",
}

_CACHE: dict = {}


def _cache_get(key):
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def _cache_set(key, value, ttl):
    _CACHE[key] = (time.time() + ttl, value)
    return value


def resolve_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    return SYMBOL_ALIASES.get(s, s)


def yahoo_ticker(symbol: str) -> str:
    s = resolve_symbol(symbol)
    if s in INDEX_TICKERS:
        return INDEX_TICKERS[s]
    if s.startswith("^") or "=" in s or s.endswith(".NS") or s.endswith(".BO"):
        return s
    return f"{s}.NS"


class YahooFinanceClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10, headers=HEADERS)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Session-like interface (Yahoo has no session; kept for compatibility) ──
    async def login(self) -> Dict[str, Any]:
        return {"status": True, "provider": "yahoo"}

    async def _ensure_session(self):
        return True

    # ── Market data ──
    async def get_ltp(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        client = await self._get_client()
        sem = asyncio.Semaphore(12)

        async def one(symbol: str):
            async with sem:
                return await self._fetch_quote(client, symbol)

        results = await asyncio.gather(*[one(t) for t in tokens], return_exceptions=True)
        for sym, res in zip(tokens, results):
            if isinstance(res, dict) and res:
                result[sym] = res
        return result

    async def _fetch_quote(self, client: httpx.AsyncClient, symbol: str) -> Optional[dict]:
        key = ("quote", symbol.upper())
        cached = _cache_get(key)
        if cached:
            return cached
        try:
            ticker = yahoo_ticker(symbol)
            r = await client.get(
                f"{BASE}/v8/finance/chart/{quote(ticker, safe='^=.')}",
                params={"range": "1d", "interval": "1d"},
                timeout=8,
            )
            if r.status_code != 200:
                return None
            chart = r.json()["chart"]["result"][0]
            meta = chart["meta"]
            price = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
            prev = meta.get("previousClose") or meta.get("chartPreviousClose") or price
            chg = round(float(price) - float(prev), 2)
            chg_pct = round((chg / float(prev) * 100), 2) if prev else 0
            q = {
                "symbol": symbol,
                "price": round(float(price), 2),
                "prev_close": round(float(prev), 2),
                "change": chg,
                "change_pct": chg_pct,
                "day_high": round(float(meta.get("regularMarketDayHigh") or price), 2),
                "day_low": round(float(meta.get("regularMarketDayLow") or price), 2),
                "volume": meta.get("regularMarketVolume", 0),
                "market_state": meta.get("marketState", "CLOSED"),
                "name": meta.get("longName") or meta.get("shortName") or symbol,
                "high_52w": meta.get("fiftyTwoWeekHigh"),
                "low_52w": meta.get("fiftyTwoWeekLow"),
                "timestamp": datetime.now().isoformat(),
                "ltp": round(float(price), 2),
            }
            return _cache_set(key, q, 5)
        except Exception:
            return None

    async def get_quote(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        return await self.get_ltp(exchange, tokens)

    async def get_historical_data(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        key = ("hist", symbol_token.upper(), interval, from_date, to_date)
        cached = _cache_get(key)
        if cached:
            return cached

        range_str, yf_interval = self._map_interval(interval)

        try:
            client = await self._get_client()
            ticker = yahoo_ticker(symbol_token)
            r = await client.get(
                f"{BASE}/v8/finance/chart/{quote(ticker, safe='^=.')}",
                params={"range": range_str, "interval": yf_interval, "includePrePost": "false"},
                timeout=12,
            )
            if r.status_code != 200:
                return []
            chart = r.json()["chart"]["result"][0]
            timestamps = chart.get("timestamp", [])
            ohlcv = chart["indicators"]["quote"][0]
            opens = ohlcv.get("open", [])
            highs = ohlcv.get("high", [])
            lows = ohlcv.get("low", [])
            closes = ohlcv.get("close", [])
            volumes = ohlcv.get("volume", [])

            candles = []
            for i, ts in enumerate(timestamps):
                c = closes[i] if i < len(closes) and closes[i] else None
                if c is None:
                    continue
                candles.append({
                    "timestamp": datetime.fromtimestamp(ts).isoformat(),
                    "open": round(opens[i] or c, 2),
                    "high": round(highs[i] or c, 2),
                    "low": round(lows[i] or c, 2),
                    "close": round(c, 2),
                    "volume": volumes[i] or 0,
                })
            return _cache_set(key, candles, 300)
        except Exception:
            return []

    def _map_interval(self, interval: str):
        interval_map = {
            "1m": ("1d", "1m"),
            "5m": ("5d", "5m"),
            "15m": ("5d", "15m"),
            "30m": ("5d", "30m"),
            "1h": ("5d", "60m"),
            "1d": ("1y", "1d"),
            "1w": ("3y", "1wk"),
            "1mo": ("3y", "1mo"),
        }
        return interval_map.get(interval, ("1y", "1d"))

    async def get_instrument_master(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        master = []
        for sym in NIFTY50_SYMBOLS:
            master.append({
                "symbol": sym,
                "name": sym,
                "symboltoken": sym,
                "token": sym,
                "exchange": exchange,
            })
        return master

    async def search_instruments(self, query: str, exchange: str = "NSE") -> List[Dict[str, Any]]:
        master = await self.get_instrument_master(exchange)
        query = query.upper()
        return [
            inst for inst in master
            if query in inst.get("symbol", "").upper() or query in inst.get("name", "").upper()
        ]

    async def get_option_chain(self, underlying: str, expiry: Optional[str] = None) -> Dict[str, Any]:
        return {"underlying": underlying, "expiry": expiry, "data": [], "source": "yahoo"}

    # ── Order/account methods NOT supported (Angel One handles these) ──
    async def get_funds(self):
        raise NotImplementedError("Yahoo Finance does not support account/funds")

    async def get_positions(self):
        raise NotImplementedError("Yahoo Finance does not support positions")

    async def get_holdings(self):
        raise NotImplementedError("Yahoo Finance does not support holdings")

    async def place_order(self, order_params):
        raise NotImplementedError("Yahoo Finance does not support order placement")

    async def modify_order(self, order_params):
        raise NotImplementedError("Yahoo Finance does not support order modification")

    async def cancel_order(self, order_id, variety="NORMAL"):
        raise NotImplementedError("Yahoo Finance does not support order cancellation")

    async def logout(self):
        await self.close()
