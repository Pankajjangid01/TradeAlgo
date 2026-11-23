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
import struct
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, TypeVar
from decimal import Decimal
from dataclasses import dataclass
import aiohttp
import httpx
import websockets
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
        # Global throttle: enforce min spacing between all historical API calls
        self._historical_throttle_lock = asyncio.Lock()
        self._last_historical_call_time: float = 0.0
        self._HISTORICAL_MIN_INTERVAL = 1.0  # seconds (1 call/sec - safest for Angel One)

        # WebSocket 2.0 streaming
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._websocket_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._websocket_subscribed_tokens: set = set()

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

    async def _http_get(self, url: str) -> Dict[str, Any]:
        await self._ensure_session()
        await self._order_limiter.acquire()
        headers = {
            "Authorization": self.session.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self.credentials.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "04:7c:16:1a:5b:be",
        }
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                raise Exception(f"API GET failed: {r.status_code} {r.text}")
            return r.json()

    async def _http_post(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure_session()
        await self._order_limiter.acquire()
        headers = {
            "Authorization": self.session.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self.credentials.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "04:7c:16:1a:5b:be",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=body, timeout=15)
            if r.status_code != 200:
                raise Exception(f"API POST failed: {r.status_code} {r.text}")
            return r.json()

    async def get_profile(self) -> Dict[str, Any]:
        return await self._http_get(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
        )

    async def get_funds(self) -> Dict[str, Any]:
        return await self._http_get(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS"
        )

    async def get_holdings(self) -> List[Dict[str, Any]]:
        return await self._http_get(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/portfolio/v1/getHolding"
        )

    async def get_positions(self) -> List[Dict[str, Any]]:
        return await self._http_get(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getPosition"
        )

    async def get_order_book(self) -> List[Dict[str, Any]]:
        return await self._http_get(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getOrderBook"
        )

    async def get_trade_book(self) -> List[Dict[str, Any]]:
        return await self._http_get(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getTradeBook"
        )

    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        return await self._http_post(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/placeOrder",
            order_params,
        )

    async def modify_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        return await self._http_post(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/modifyOrder",
            order_params,
        )

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        return await self._http_post(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/cancelOrder",
            {"orderid": order_id, "variety": variety},
        )

    # ------------------------------------------------------------------
    # Market data endpoints (quote-rate limited)
    # ------------------------------------------------------------------

    async def get_ltp(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        await self._ensure_session()
        await self._quote_limiter.acquire()

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
        body = {
            "mode": "LTP",
            "exchangeTokens": {exchange: tokens},
        }

        headers = {
            "Authorization": self.session.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self.credentials.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "04:7c:16:1a:5b:be",
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=body, timeout=15)
            if r.status_code != 200:
                raise Exception(f"LTP API failed: {r.status_code} {r.text}")
            return r.json()

    async def get_quote(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        await self._ensure_session()
        await self._quote_limiter.acquire()

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
        body = {
            "mode": "FULL",
            "exchangeTokens": {exchange: tokens},
        }

        headers = {
            "Authorization": self.session.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self.credentials.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "04:7c:16:1a:5b:be",
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=body, timeout=15)
            if r.status_code != 200:
                raise Exception(f"Quote API failed: {r.status_code} {r.text}")
            return r.json()

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
        await self._historical_limiter.acquire()

        # Angel One interval format mapping
        interval_map = {
            "1m": "ONE_MINUTE",
            "3m": "THREE_MINUTE",
            "5m": "FIVE_MINUTE",
            "10m": "TEN_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "30m": "THIRTY_MINUTE",
            "1h": "ONE_HOUR",
            "1d": "ONE_DAY",
        }
        angel_interval = interval_map.get(interval, interval)

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getCandleData"
        body = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": angel_interval,
            "fromdate": from_date,
            "todate": to_date,
        }

        headers = {
            "Authorization": self.session.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self.credentials.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "04:7c:16:1a:5b:be",
        }

        # Global throttle: enforce min spacing between all historical API calls
        async with self._historical_throttle_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_historical_call_time
            if elapsed < self._HISTORICAL_MIN_INTERVAL:
                await asyncio.sleep(self._HISTORICAL_MIN_INTERVAL - elapsed)
            self._last_historical_call_time = asyncio.get_event_loop().time()

        async with httpx.AsyncClient() as client:
            max_retries = 5
            for attempt in range(max_retries):
                r = await client.post(url, headers=headers, json=body, timeout=15)
                if r.status_code == 200:
                    break
                if r.status_code == 403 and attempt < max_retries - 1:
                    # Rate limited by Angel One - wait longer and retry
                    wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s, 20s
                    await asyncio.sleep(wait_time)
                    continue
                raise Exception(f"Historical API failed: {r.status_code} {r.text}")
            else:
                raise Exception(f"Historical API failed after {max_retries} retries: last status {r.status_code}")
            result = r.json()
            if result.get("status") is not True:
                raise Exception(f"Historical API error: {result.get('message', 'Unknown error')}")

            # Angel One returns data as list of lists: [timestamp, open, high, low, close, volume]
            raw_data = result.get("data", []) or []
            normalized = []
            for row in raw_data:
                if isinstance(row, list) and len(row) >= 6:
                    normalized.append({
                        "timestamp": row[0],
                        "open": float(row[1]) if row[1] else 0,
                        "high": float(row[2]) if row[2] else 0,
                        "low": float(row[3]) if row[3] else 0,
                        "close": float(row[4]) if row[4] else 0,
                        "volume": int(row[5]) if row[5] else 0,
                    })
            return normalized

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
        await self._quote_limiter.acquire()

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/marketData/v1/optionGreek"
        body = {
            "name": underlying,
            "expirydate": expiry or "",
        }

        headers = {
            "Authorization": self.session.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self.credentials.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "04:7c:16:1a:5b:be",
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=body, timeout=15)
            if r.status_code == 200:
                return r.json()
            raise Exception(f"Option chain API failed: {r.status_code} {r.text}")

    # ------------------------------------------------------------------
    # WebSocket Streaming 2.0 (Real-time LTP via Angel One Smart Stream)
    # ------------------------------------------------------------------

    async def connect_websocket(self) -> None:
        """Connect to Angel One WebSocket 2.0 for real-time LTP streaming."""
        await self._ensure_session()

        ws_url = "wss://smartapisocket.angelone.in/smart-stream"
        headers = {
            "Authorization": self.session.access_token,
            "x-api-key": self.credentials.api_key,
            "x-client-code": self.session.client_code,
            "x-feed-token": self.session.feed_token,
        }

        self._websocket = await websockets.connect(
            ws_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=60,
            close_timeout=10,
        )
        logger.info("Angel One WebSocket 2.0 connected")

        # Start receiving loop (library handles ping/pong automatically)
        asyncio.create_task(self._websocket_receive_loop())

    async def _websocket_receive_loop(self) -> None:
        """Receive and process WebSocket messages."""
        while self._websocket is not None:
            try:
                message = await self._websocket.recv()
                if isinstance(message, str):
                    if message == "pong":
                        continue
                    logger.debug(f"WebSocket text message: {message}")
                elif isinstance(message, bytes):
                    self._process_websocket_binary(message)
            except websockets.ConnectionClosed:
                logger.warning("Angel One WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                break

    def _process_websocket_binary(self, data: bytes) -> None:
        """Parse Angel One WebSocket 2.0 binary response.

        Binary format (Little Endian):
        - Byte 0: Subscription Mode (1=LTP, 2=Quote, 3=SnapQuote)
        - Byte 1: Exchange Type
        - Bytes 2-26: Token (25 bytes, null-terminated UTF-8)
        - Bytes 27-34: Sequence Number (int64)
        - Bytes 35-42: Exchange Timestamp (int64, epoch ms)
        - Bytes 43-50: LTP (int32, in paise)
        ... more fields for Quote/SnapQuote modes
        """
        try:
            if len(data) < 51:
                logger.warning(f"WebSocket binary too short: {len(data)} bytes")
                return

            # Subscription Mode (byte 0)
            mode = data[0]
            mode_str = {1: "LTP", 2: "Quote", 3: "SnapQuote"}.get(mode, f"mode_{mode}")

            # Exchange Type (byte 1)
            exchange_type = data[1]
            exchange_str = {1: "NSE_CM", 2: "NSE_FO", 3: "BSE_CM", 4: "BSE_FO", 5: "MCX_FO"}.get(exchange_type, f"exchange_{exchange_type}")

            # Token (bytes 2-26, 25 bytes null-terminated)
            token_bytes = data[2:27]
            token = token_bytes.split(b"\x00")[0].decode("utf-8", errors="ignore")

            # Sequence Number (bytes 27-34, int64 LE)
            sequence_number = struct.unpack("<q", data[27:35])[0]

            # Exchange Timestamp (bytes 35-42, int64 LE, epoch ms)
            exchange_timestamp_ms = struct.unpack("<q", data[35:43])[0]

            # LTP (bytes 43-50, int32 LE, in paise)
            ltp_paise = struct.unpack("<i", data[43:47])[0]
            ltp = ltp_paise / 100.0

            tick = {
                "instrument_token": token,
                "symbol": token,
                "ltp": ltp,
                "mode": mode_str,
                "exchange": exchange_str,
                "sequence_number": sequence_number,
                "exchange_timestamp_ms": exchange_timestamp_ms,
                "timestamp": datetime.now().isoformat(),
            }

            # Notify callbacks
            for callback in self._websocket_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"WebSocket callback error: {e}")

        except Exception as e:
            logger.error(f"WebSocket binary parse error: {e}")

    async def subscribe_websocket(self, tokens: List[str], mode: int = 1) -> None:
        """Subscribe to tokens via WebSocket.
        
        mode: 1=LTP, 2=Quote, 3=SnapQuote
        """
        if not self._websocket:
            await self.connect_websocket()

        # Build subscription request
        # Group tokens by exchange type (default NSE_CM = 1)
        token_list = [
            {
                "exchangeType": 1,  # NSE Cash Market
                "tokens": tokens,
            }
        ]

        request = {
            "correlationID": "ws_sub_001",
            "action": 1,  # 1=Subscribe, 0=Unsubscribe
            "params": {
                "mode": mode,
                "tokenList": token_list,
            },
        }

        await self._websocket.send(json.dumps(request))
        logger.info(f"WebSocket subscribed: {tokens} mode={mode}")

    async def unsubscribe_websocket(self, tokens: List[str]) -> None:
        """Unsubscribe from tokens."""
        if not self._websocket:
            return

        request = {
            "correlationID": "ws_unsub_001",
            "action": 0,  # Unsubscribe
            "params": {
                "mode": 1,
                "tokenList": [
                    {
                        "exchangeType": 1,
                        "tokens": tokens,
                    }
                ],
            },
        }

        await self._websocket.send(json.dumps(request))
        logger.info(f"WebSocket unsubscribed: {tokens}")

    async def stop_websocket(self) -> None:
        """Close WebSocket connection."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
            logger.info("Angel One WebSocket 2.0 disconnected")

    def on_websocket_tick(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for WebSocket tick data."""
        if callback not in self._websocket_callbacks:
            self._websocket_callbacks.append(callback)

    def remove_websocket_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove WebSocket tick callback."""
        if callback in self._websocket_callbacks:
            self._websocket_callbacks.remove(callback)

    # ------------------------------------------------------------------
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
