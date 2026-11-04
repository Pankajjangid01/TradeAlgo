import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
import aiohttp
import pyotp
from SmartApi import SmartConnect

from app.config.settings import settings

logger = logging.getLogger(__name__)


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

    async def login(self) -> AngelOneSession:
        async with self._lock:
            if self.session and self.session.expires_at > datetime.now():
                return self.session

            try:
                self.smart_api = SmartConnect(api_key=self.credentials.api_key)
                totp = pyotp.TOTP(self.credentials.totp_secret).now()
                data = self.smart_api.generateSession(
                    self.credentials.client_code,
                    self.credentials.password,
                    totp
                )

                if data.get("status") is not True:
                    raise Exception(f"Login failed: {data.get('message', 'Unknown error')}")

                access_token = data["data"]["jwtToken"]
                refresh_token = data["data"]["refreshToken"]
                feed_token = self.smart_api.getfeedToken()

                self.session = AngelOneSession(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    feed_token=feed_token,
                    client_code=self.credentials.client_code,
                    expires_at=datetime.now() + timedelta(hours=23)
                )

                self.smart_api.setAccessToken(access_token)
                self.smart_api.setRefreshToken(refresh_token)
                self.smart_api.setFeedToken(feed_token)

                logger.info("Angel One login successful")
                return self.session

            except Exception as e:
                logger.error(f"Angel One login failed: {e}")
                raise

    async def logout(self) -> bool:
        if self.smart_api and self.session:
            try:
                self.smart_api.terminateSession(self.session.client_code)
                self.session = None
                return True
            except Exception as e:
                logger.error(f"Logout failed: {e}")
                return False
        return True

    async def get_profile(self) -> Dict[str, Any]:
        await self._ensure_session()
        return self.smart_api.getProfile(self.session.refresh_token)

    async def get_funds(self) -> Dict[str, Any]:
        await self._ensure_session()
        return self.smart_api.rmsLimit()

    async def get_holdings(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return self.smart_api.holding()

    async def get_positions(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return self.smart_api.position()

    async def get_order_book(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return self.smart_api.orderBook()

    async def get_trade_book(self) -> List[Dict[str, Any]]:
        await self._ensure_session()
        return self.smart_api.tradeBook()

    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure_session()
        return self.smart_api.placeOrder(order_params)

    async def modify_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure_session()
        return self.smart_api.modifyOrder(order_params)

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        await self._ensure_session()
        return self.smart_api.cancelOrder(order_id, variety)

    async def get_ltp(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        await self._ensure_session()
        return self.smart_api.ltpData(exchange, tokens)

    async def get_quote(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        await self._ensure_session()
        return self.smart_api.getMarketData("FULL", {exchange: tokens})

    async def get_historical_data(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str
    ) -> List[Dict[str, Any]]:
        await self._ensure_session()
        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date,
        }
        return self.smart_api.getCandleData(params)

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
        return self.smart_api.getOptionChain(params)

    async def _ensure_session(self) -> None:
        if not self.session or self.session.expires_at <= datetime.now():
            await self.login()

    async def refresh_session(self) -> AngelOneSession:
        async with self._lock:
            if self.smart_api and self.session:
                try:
                    data = self.smart_api.generateToken(self.session.refresh_token)
                    if data.get("status") is True:
                        self.session.access_token = data["data"]["jwtToken"]
                        self.session.refresh_token = data["data"]["refreshToken"]
                        self.session.feed_token = self.smart_api.getfeedToken()
                        self.session.expires_at = datetime.now() + timedelta(hours=23)
                        self.smart_api.setAccessToken(self.session.access_token)
                        self.smart_api.setRefreshToken(self.session.refresh_token)
                        self.smart_api.setFeedToken(self.session.feed_token)
                        logger.info("Session refreshed successfully")
                        return self.session
                except Exception as e:
                    logger.error(f"Session refresh failed: {e}")
            return await self.login()


class AngelOneWebSocketClient:
    def __init__(self, client: AngelOneClient):
        self.client = client
        self.ws = None
        self.callbacks: Dict[str, callable] = {}
        self._running = False
        self._subscribed_tokens: set = set()

    async def connect(self) -> None:
        await self.client._ensure_session()
        self.ws = await self.client.smart_api.connectWebSocket(
            self.client.session.access_token,
            self.client.session.client_code,
            self.client.session.feed_token
        )
        self._running = True

    async def subscribe(self, tokens: List[str], mode: int = 1) -> None:
        if not self.ws:
            await self.connect()
        self.client.smart_api.subscribe(self.ws, tokens, mode)
        self._subscribed_tokens.update(tokens)

    async def unsubscribe(self, tokens: List[str]) -> None:
        if self.ws:
            self.client.smart_api.unsubscribe(self.ws, tokens)
            self._subscribed_tokens.difference_update(tokens)

    def on_message(self, callback: callable) -> None:
        self.callbacks["message"] = callback

    def on_error(self, callback: callable) -> None:
        self.callbacks["error"] = callback

    def on_close(self, callback: callable) -> None:
        self.callbacks["close"] = callback

    async def run(self) -> None:
        while self._running:
            try:
                if self.ws:
                    message = await self.ws.recv()
                    if message and "message" in self.callbacks:
                        await self.callbacks["message"](json.loads(message))
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if "error" in self.callbacks:
                    await self.callbacks["error"](e)
                await asyncio.sleep(5)
                if self._running:
                    await self.connect()

    async def stop(self) -> None:
        self._running = False
        if self.ws:
            await self.ws.close()