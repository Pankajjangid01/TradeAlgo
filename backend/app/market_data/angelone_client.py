"""
Angel One SmartAPI client with centralized rate limiting, retry, and circuit breaker.

All broker API calls go through the rate limiter (sliding window) with exponential
backoff retry. Rate limits are endpoint-specific (orders: 20/s, quotes: 1/s,
historical: 5/s) with 80% safety margin by default.

SmartAPI synchronous methods are run in a thread executor to avoid blocking
the asyncio event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, TypeVar
from decimal import Decimal
from dataclasses import dataclass
import aiohttp
import pyotp
from SmartApi import SmartConnect

from app.config.settings import settings
from app.core.rate_limiter import (
    SlidingWindowRateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
    with_retry,
    get_rate_limiter,
    ANGELONE_ORDER_CONFIG,
    ANGELONE_QUOTE_CONFIG,
    ANGELONE_HISTORICAL_CONFIG,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class AngelOneCredentials:
    api_key: str
    client_code: str
    password: str
    totp_secret: str


@dataclass
class AngelOneSession:
    access_token: str
    refresh_token: str
    feed_token: str
    client_code: str
    expires_at: datetime


class AngelOneClient:
    def __init__(self, credentials: Optional[AngelOneCredentials] = None):
        self.credentials = credentials or AngelOneCredentials(
            api_key=settings.ANGELONE_API_KEY,
            client_code=settings.ANGELONE_CLIENT_CODE,
            password=settings.ANGELONE_PASSWORD,
            totp_secret=settings.ANGELONE_TOTP_SECRET,
        )
        self.smart_api: Optional[SmartConnect] = None
        self.session: Optional[AngelOneSession] = None
        self._lock = asyncio.Lock()

        # Centralized rate limiters (singleton per endpoint type)
        self._order_limiter: Optional[SlidingWindowRateLimiter] = None
        self._quote_limiter: Optional[SlidingWindowRateLimiter] = None
        self._historical_limiter: Optional[SlidingWindowRateLimiter] = None
        self._limiters_initialized = False

    async def _ensure_limiters(self) -> None:
        """Lazy-initialize rate limiters (must be called within running event loop)."""
        if self._limiters_initialized:
            return
        self._order_limiter = await get_rate_limiter("angelone_orders", ANGELONE_ORDER_CONFIG)
        self._quote_limiter = await get_rate_limiter("angelone_quotes", ANGELONE_QUOTE_CONFIG)
        self._historical_limiter = await get_rate_limiter("angelone_historical", ANGELONE_HISTORICAL_CONFIG)
        self._limiters_initialized = True

    async def _run_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Run a synchronous SmartAPI call in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _rate_limited_call(
        self,
        limiter: SlidingWindowRateLimiter,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """Execute a SmartAPI call through the rate limiter with retry on rate-limit errors."""
        await self._ensure_limiters()

        async def _call() -> T:
            return await self._run_sync(func, *args, **kwargs)

        return await with_retry(limiter)(_call)()

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        """Detect if an exception is a rate-limit/throttle error from Angel One."""
        msg = str(exc).lower()
        return any(
            kw in msg
            for kw in ["rate limit", "429", "too many requests", "throttle", "api limit"]
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def login(self) -> AngelOneSession:
        async with self._lock:
            if self.session and self.session.expires_at > datetime.now():
                return self.session

            try:
                self.smart_api = SmartConnect(api_key=self.credentials.api_key)
                totp = pyotp.TOTP(self.credentials.totp_secret).now()
                data = await self._run_sync(
                    self.smart_api.generateSession,
                    self.credentials.client_code,
                    self.credentials.password,
                    totp,
                )

                if data.get("status") is not True:
                    raise Exception(f"Login failed: {data.get('message', 'Unknown error')}")

                access_token = data["data"]["jwtToken"]
                refresh_token = data["data"]["refreshToken"]
                feed_token = await self._run_sync(self.smart_api.getfeedToken)

                self.session = AngelOneSession(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    feed_token=feed_token,
                    client_code=self.credentials.client_code,
                    expires_at=datetime.now() + timedelta(hours=23),
                )

                await self._run_sync(self.smart_api.setAccessToken, access_token)
                await self._run_sync(self.smart_api.setRefreshToken, refresh_token)
                await self._run_sync(self.smart_api.setFeedToken, feed_token)

                logger.info("Angel One login successful")
                return self.session

            except Exception as e:
                logger.error(f"Angel One login failed: {e}")
                raise

    async def logout(self) -> bool:
        if self.smart_api and self.session:
            try:
                await self._run_sync(self.smart_api.terminateSession, self.session.client_code)
                self.session = None
                return True
            except Exception as e:
                logger.error(f"Logout failed: {e}")
                return False
        return True

    async def _ensure_session(self) -> None:
        if not self.session or self.session.expires_at <= datetime.now():
            await self.login()
        await self._ensure_limiters()

    # ------------------------------------------------------------------
    # Account endpoints (order-rate limited)
    # ------------------------------------------------------------------

    async def get_profile(self) -> Dict[str, Any]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.getProfile, self.session.refresh_token
        )

    async def get_funds(self) -> Dict[str, Any]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.rmsLimit
        )

    async def get_holdings(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.holding
        )

    async def get_positions(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.position
        )

    async def get_order_book(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.orderBook
        )

    async def get_trade_book(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.tradeBook
        )

    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.placeOrder, order_params
        )

    async def modify_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.modifyOrder, order_params
        )

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._order_limiter, self.smart_api.cancelOrder, order_id, variety
        )

    # ------------------------------------------------------------------
    # Market data endpoints (quote-rate limited)
    # ------------------------------------------------------------------

    async def get_ltp(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        await self._ensure_session()
        symboltoken = ",".join(tokens)
        # Use the token as tradingsymbol too; Angel One may accept it
        return await self._rate_limited_call(
            self._quote_limiter, self.smart_api.ltpData, exchange, symboltoken, symboltoken
        )

    async def get_quote(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        await self._ensure_session()
        return await self._rate_limited_call(
            self._quote_limiter, self.smart_api.getMarketData, "FULL", {exchange: tokens}
        )

    # ------------------------------------------------------------------
    # Historical data (separate limiter)
    # ------------------------------------------------------------------

    async def get_historical_data(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        await self._ensure_session()
        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date,
        }
        return await self._rate_limited_call(
            self._historical_limiter, self.smart_api.getCandleData, params
        )

    # ------------------------------------------------------------------
    # Instrument master (no rate limit - public JSON file)
    # ------------------------------------------------------------------

    async def get_instrument_master(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        await self._ensure_session()
        url = f"https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                raise Exception(f"Failed to fetch instrument master: {response.status}")

    async def search_instruments(self, query: str, exchange: str = "NSE") -> List[Dict[str, Any]]:
        master = await self.get_instrument_master(exchange)
        query = query.upper()
        return [
            inst for inst in master
            if query in inst.get("symbol", "").upper() or query in inst.get("name", "").upper()
        ]

    async def get_option_chain(self, underlying: str, expiry: Optional[str] = None) -> Dict[str, Any]:
        await self._ensure_session()
        params = {"name": underlying}
        if expiry:
            params["expiry"] = expiry
        return await self._rate_limited_call(
            self._quote_limiter, self.smart_api.getOptionChain, params
        )

    async def refresh_session(self) -> AngelOneSession:
        async with self._lock:
            if self.smart_api and self.session:
                try:
                    data = await self._run_sync(self.smart_api.generateToken, self.session.refresh_token)
                    if data.get("status") is True:
                        self.session.access_token = data["data"]["jwtToken"]
                        self.session.refresh_token = data["data"]["refreshToken"]
                        self.session.feed_token = await self._run_sync(self.smart_api.getfeedToken)
                        self.session.expires_at = datetime.now() + timedelta(hours=23)
                        await self._run_sync(self.smart_api.setAccessToken, self.session.access_token)
                        await self._run_sync(self.smart_api.setRefreshToken, self.session.refresh_token)
                        await self._run_sync(self.smart_api.setFeedToken, self.session.feed_token)
                        logger.info("Session refreshed successfully")
                        return self.session
                except Exception as e:
                    logger.error(f"Session refresh failed: {e}")
            return await self.login()


class AngelOneWebSocketClient:
    def __init__(self, client: AngelOneClient):
        self.client = client
        self.ws = None
        self.callbacks: Dict[str, Callable] = {}
        self._running = False
        self._subscribed_tokens: set = set()
        self._reconnect_delay = 5.0
        self._max_reconnect_delay = 60.0
        self._heartbeat_interval = 30.0
        self._last_message_time: Optional[float] = None

    async def connect(self) -> None:
        await self.client._ensure_session()
        self.ws = await self._run_sync(
            self.client.smart_api.connectWebSocket,
            self.client.session.access_token,
            self.client.session.client_code,
            self.client.session.feed_token,
        )
        self._running = True
        self._last_message_time = asyncio.get_event_loop().time()
        logger.info("Angel One WebSocket connected")

    async def subscribe(self, tokens: List[str], mode: int = 1) -> None:
        if not self.ws:
            await self.connect()
        await self._run_sync(self.client.smart_api.subscribe, self.ws, tokens, mode)
        self._subscribed_tokens.update(tokens)
        logger.info(f"Subscribed to {len(tokens)} tokens: {tokens[:5]}...")

    async def unsubscribe(self, tokens: List[str]) -> None:
        if self.ws:
            await self._run_sync(self.client.smart_api.unsubscribe, self.ws, tokens)
            self._subscribed_tokens.difference_update(tokens)

    def on_message(self, callback: Callable) -> None:
        self.callbacks["message"] = callback

    def on_error(self, callback: Callable) -> None:
        self.callbacks["error"] = callback

    def on_close(self, callback: Callable) -> None:
        self.callbacks["close"] = callback

    async def run(self) -> None:
        """Main WebSocket run loop with reconnection and heartbeat monitoring."""
        while self._running:
            try:
                if not self.ws:
                    await self.connect()

                # Check heartbeat - if no message for 2x heartbeat interval, reconnect
                now = asyncio.get_event_loop().time()
                if self._last_message_time and now - self._last_message_time > self._heartbeat_interval * 2:
                    logger.warning("WebSocket heartbeat timeout, reconnecting")
                    await self.stop()
                    await asyncio.sleep(self._reconnect_delay)
                    continue

                if self.ws:
                    message = await self.ws.recv()
                    self._last_message_time = now
                    if message and "message" in self.callbacks:
                        await self.callbacks["message"](json.loads(message))

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if "error" in self.callbacks:
                    try:
                        await self.callbacks["error"](e)
                    except Exception:
                        pass
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 1.5, self._max_reconnect_delay)
                if self._running:
                    await self.connect()
                    self._reconnect_delay = 5.0  # Reset after successful reconnect

    async def stop(self) -> None:
        self._running = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
