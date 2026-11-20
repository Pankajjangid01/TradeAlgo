"""
Flattrade Pi API client with centralized rate limiting, retry, and circuit breaker.

All broker API calls go through the rate limiter (sliding window) with exponential
backoff retry. Rate limits are configured per endpoint with 80% safety margin.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, TypeVar
from dataclasses import dataclass
import aiohttp
import jwt

from app.config.settings import settings
from app.core.rate_limiter import (
    SlidingWindowRateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
    with_retry,
    get_rate_limiter,
    FLATTRADE_CONFIG,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class FlattradeCredentials:
    api_key: str
    api_secret: str
    client_id: str
    redirect_url: str


@dataclass
class FlattradeSession:
    access_token: str
    refresh_token: str
    client_id: str
    expires_at: datetime


class FlattradeClient:
    def __init__(self, credentials: Optional[FlattradeCredentials] = None):
        self.credentials = credentials or FlattradeCredentials(
            api_key=settings.FLATTRADE_API_KEY,
            api_secret=settings.FLATTRADE_API_SECRET,
            client_id=settings.FLATTRADE_CLIENT_ID,
            redirect_url=settings.FLATTRADE_REDIRECT_URL,
        )
        self.session: Optional[FlattradeSession] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

        # Rate limiters (lazy-initialized)
        self._order_limiter: Optional[SlidingWindowRateLimiter] = None
        self._quote_limiter: Optional[SlidingWindowRateLimiter] = None
        self._limiters_initialized = False

    async def _ensure_limiters(self) -> None:
        if self._limiters_initialized:
            return
        self._order_limiter = await get_rate_limiter("flattrade_orders", FLATTRADE_CONFIG)
        self._quote_limiter = await get_rate_limiter("flattrade_quotes", FLATTRADE_CONFIG)
        self._limiters_initialized = True

    async def _get_http_session(self) -> aiohttp.ClientSession:
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.http_session

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.session.access_token}",
            "Content-Type": "application/json",
        }

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(kw in msg for kw in ["rate limit", "429", "too many requests", "throttle"])

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    async def login(self, auth_code: str) -> FlattradeSession:
        async with self._lock:
            session = aiohttp.ClientSession()
            try:
                url = f"{settings.FLATTRADE_BASE_URL}/api/token"
                data = {
                    "api_key": self.credentials.api_key,
                    "api_secret": self.credentials.api_secret,
                    "code": auth_code,
                    "grant_type": "authorization_code",
                }
                async with session.post(url, data=data) as response:
                    result = await response.json()
                    if response.status != 200:
                        raise Exception(f"Login failed: {result.get('message', 'Unknown error')}")

                    access_token = result["access_token"]
                    refresh_token = result.get("refresh_token", "")
                    payload = jwt.decode(access_token, options={"verify_signature": False})
                    exp = payload.get("exp", 0)
                    expires_at = datetime.fromtimestamp(exp) if exp else datetime.now() + timedelta(hours=23)

                    self.session = FlattradeSession(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        client_id=self.credentials.client_id,
                        expires_at=expires_at,
                    )
                    logger.info("Flattrade login successful")
                    return self.session
            finally:
                await session.close()

    async def generate_auth_url(self) -> str:
        return (
            f"{settings.FLATTRADE_BASE_URL}/api/login?"
            f"api_key={self.credentials.api_key}&"
            f"redirect_uri={self.credentials.redirect_url}"
        )

    async def logout(self) -> bool:
        if self.session:
            self.session = None
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        return True

    async def _ensure_session(self) -> None:
        if not self.session or self.session.expires_at <= datetime.now() + timedelta(minutes=5):
            if self.session and self.session.refresh_token:
                await self._refresh_session()
            else:
                raise Exception("No valid session. Please login first.")
        await self._ensure_limiters()

    async def _refresh_session(self) -> bool:
        if not self.session or not self.session.refresh_token:
            return False
        session = aiohttp.ClientSession()
        try:
            url = f"{settings.FLATTRADE_BASE_URL}/api/token/refresh"
            data = {
                "api_key": self.credentials.api_key,
                "refresh_token": self.session.refresh_token,
                "grant_type": "refresh_token",
            }
            async with session.post(url, data=data) as response:
                result = await response.json()
                if response.status == 200:
                    access_token = result["access_token"]
                    payload = jwt.decode(access_token, options={"verify_signature": False})
                    exp = payload.get("exp", 0)
                    self.session.access_token = access_token
                    self.session.expires_at = datetime.fromtimestamp(exp) if exp else datetime.now() + timedelta(hours=23)
                    if "refresh_token" in result:
                        self.session.refresh_token = result["refresh_token"]
                    logger.info("Flattrade session refreshed")
                    return True
                return False
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            return False
        finally:
            await session.close()

    # ------------------------------------------------------------------
    # Rate-limited API calls
    # ------------------------------------------------------------------

    async def _api_get(self, limiter: SlidingWindowRateLimiter, path: str, params: Optional[Dict] = None) -> Any:
        await self._ensure_session()
        await self._ensure_limiters()

        async def _call() -> Any:
            session = await self._get_http_session()
            async with session.get(
                f"{settings.FLATTRADE_BASE_URL}{path}",
                headers=self._get_headers(),
                params=params,
            ) as response:
                return await response.json()

        return await with_retry(limiter)(_call)()

    async def _api_post(self, limiter: SlidingWindowRateLimiter, path: str, json_data: Optional[Dict] = None) -> Any:
        await self._ensure_session()
        await self._ensure_limiters()

        async def _call() -> Any:
            session = await self._get_http_session()
            async with session.post(
                f"{settings.FLATTRADE_BASE_URL}{path}",
                headers=self._get_headers(),
                json=json_data,
            ) as response:
                return await response.json()

        return await with_retry(limiter)(_call)()

    async def _api_put(self, limiter: SlidingWindowRateLimiter, path: str, json_data: Optional[Dict] = None) -> Any:
        await self._ensure_session()
        await self._ensure_limiters()

        async def _call() -> Any:
            session = await self._get_http_session()
            async with session.put(
                f"{settings.FLATTRADE_BASE_URL}{path}",
                headers=self._get_headers(),
                json=json_data,
            ) as response:
                return await response.json()

        return await with_retry(limiter)(_call)()

    async def _api_delete(self, limiter: SlidingWindowRateLimiter, path: str) -> Any:
        await self._ensure_session()
        await self._ensure_limiters()

        async def _call() -> Any:
            session = await self._get_http_session()
            async with session.delete(
                f"{settings.FLATTRADE_BASE_URL}{path}",
                headers=self._get_headers(),
            ) as response:
                return await response.json()

        return await with_retry(limiter)(_call)()

    # ------------------------------------------------------------------
    # Account endpoints (order-rate limited)
    # ------------------------------------------------------------------

    async def get_profile(self) -> Dict[str, Any]:
        return await self._api_get(self._order_limiter, "/api/user/profile")

    async def get_funds(self) -> Dict[str, Any]:
        return await self._api_get(self._order_limiter, "/api/user/funds")

    async def get_holdings(self) -> List[Dict[str, Any]]:
        return await self._api_get(self._order_limiter, "/api/portfolio/holdings")

    async def get_positions(self) -> List[Dict[str, Any]]:
        return await self._api_get(self._order_limiter, "/api/portfolio/positions")

    async def get_order_book(self) -> List[Dict[str, Any]]:
        return await self._api_get(self._order_limiter, "/api/orders")

    async def get_trade_book(self) -> List[Dict[str, Any]]:
        return await self._api_get(self._order_limiter, "/api/trades")

    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        return await self._api_post(self._order_limiter, "/api/orders", order_params)

    async def modify_order(self, order_id: str, order_params: Dict[str, Any]) -> Dict[str, Any]:
        return await self._api_put(self._order_limiter, f"/api/orders/{order_id}", order_params)

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return await self._api_delete(self._order_limiter, f"/api/orders/{order_id}")

    # ------------------------------------------------------------------
    # Market data endpoints (quote-rate limited)
    # ------------------------------------------------------------------

    async def get_ltp(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        return await self._api_get(
            self._quote_limiter, "/api/market/ltp",
            params={"exchange": exchange, "tokens": ",".join(tokens)},
        )

    async def get_quote(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        return await self._api_get(
            self._quote_limiter, "/api/market/quote",
            params={"exchange": exchange, "tokens": ",".join(tokens)},
        )

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    async def get_historical_data(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        return await self._api_get(
            self._quote_limiter, "/api/market/history",
            params={
                "exchange": exchange,
                "token": symbol_token,
                "interval": interval,
                "from": from_date,
                "to": to_date,
            },
        )

    async def get_instrument_master(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        return await self._api_get(self._quote_limiter, f"/api/instruments/{exchange}")

    async def search_instruments(self, query: str, exchange: str = "NSE") -> List[Dict[str, Any]]:
        master = await self.get_instrument_master(exchange)
        query = query.upper()
        return [
            inst for inst in master
            if query in inst.get("symbol", "").upper() or query in inst.get("name", "").upper()
        ]

    async def get_option_chain(self, underlying: str, expiry: Optional[str] = None) -> Dict[str, Any]:
        params = {"underlying": underlying}
        if expiry:
            params["expiry"] = expiry
        return await self._api_get(self._quote_limiter, "/api/market/option-chain", params=params)

    async def close(self) -> None:
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
