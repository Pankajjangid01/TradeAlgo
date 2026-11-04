import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.config.settings import settings
from app.market_data.angelone_client import AngelOneClient, AngelOneCredentials
from app.market_data.flattrade_client import FlattradeClient, FlattradeCredentials

logger = logging.getLogger(__name__)


class DataProvider(str, Enum):
    ANGELONE = "angelone"
    FLATTRADE = "flattrade"


@dataclass
class MarketTick:
    instrument_token: str
    timestamp: datetime
    ltp: Decimal
    volume: int
    oi: Optional[int] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None


@dataclass
class CandleData:
    instrument_token: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: Optional[int] = None
    vwap: Optional[Decimal] = None


class MarketDataService:
    def __init__(self):
        self.angelone_client: Optional[AngelOneClient] = None
        self.flattrade_client: Optional[FlattradeClient] = None
        self.active_provider: DataProvider = DataProvider.ANGELONE
        self._tick_callbacks: List[Callable[[MarketTick], None]] = []
        self._candle_callbacks: List[Callable[[CandleData], None]] = []
        self._ws_tasks: List[asyncio.Task] = []
        self._running = False

    async def initialize(self) -> None:
        if settings.ANGELONE_API_KEY:
            self.angelone_client = AngelOneClient()
            try:
                await self.angelone_client.login()
                logger.info("Angel One client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Angel One: {e}")

        if settings.FLATTRADE_API_KEY:
            self.flattrade_client = FlattradeClient()
            logger.info("Flattrade client initialized (requires auth code)")

        self.active_provider = DataProvider(settings.MARKET_DATA_PROVIDER)

    async def set_active_provider(self, provider: DataProvider) -> bool:
        if provider == DataProvider.ANGELONE and self.angelone_client:
            self.active_provider = provider
            return True
        elif provider == DataProvider.FLATTRADE and self.flattrade_client and self.flattrade_client.session:
            self.active_provider = provider
            return True
        return False

    def get_active_client(self):
        if self.active_provider == DataProvider.ANGELONE:
            return self.angelone_client
        return self.flattrade_client

    # Market Data Methods
    async def get_ltp(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_ltp(exchange, tokens)

    async def get_quote(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_quote(exchange, tokens)

    async def get_historical_data(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str
    ) -> List[Dict[str, Any]]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_historical_data(exchange, symbol_token, interval, from_date, to_date)

    async def get_instrument_master(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_instrument_master(exchange)

    async def search_instruments(self, query: str, exchange: str = "NSE") -> List[Dict[str, Any]]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.search_instruments(query, exchange)

    async def get_option_chain(self, underlying: str, expiry: Optional[str] = None) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_option_chain(underlying, expiry)

    # Account Methods
    async def get_funds(self) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_funds()

    async def get_positions(self) -> List[Dict[str, Any]]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_positions()

    async def get_holdings(self) -> List[Dict[str, Any]]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_holdings()

    async def get_order_book(self) -> List[Dict[str, Any]]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_order_book()

    async def get_trade_book(self) -> List[Dict[str, Any]]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.get_trade_book()

    # Order Methods
    async def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.place_order(order_params)

    async def modify_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.modify_order(order_params)

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        return await client.cancel_order(order_id, variety)

    # WebSocket Methods
    def add_tick_callback(self, callback: Callable[[MarketTick], None]) -> None:
        self._tick_callbacks.append(callback)

    def add_candle_callback(self, callback: Callable[[CandleData], None]) -> None:
        self._candle_callbacks.append(callback)

    async def start_websocket(self, tokens: List[str]) -> None:
        if self.active_provider == DataProvider.ANGELONE and self.angelone_client:
            from app.market_data.angelone_client import AngelOneWebSocketClient
            ws_client = AngelOneWebSocketClient(self.angelone_client)
            
            async def on_message(message: Dict[str, Any]):
                await self._process_angelone_message(message)
            
            ws_client.on_message(on_message)
            await ws_client.connect()
            await ws_client.subscribe(tokens)
            
            task = asyncio.create_task(ws_client.run())
            self._ws_tasks.append(task)

    async def _process_angelone_message(self, message: Dict[str, Any]) -> None:
        try:
            if "token" in message and "ltp" in message:
                tick = MarketTick(
                    instrument_token=str(message["token"]),
                    timestamp=datetime.now(),
                    ltp=Decimal(str(message["ltp"])),
                    volume=message.get("volume", 0),
                    oi=message.get("oi"),
                    bid=Decimal(str(message["bid"])) if message.get("bid") else None,
                    ask=Decimal(str(message["ask"])) if message.get("ask") else None,
                    bid_qty=message.get("bid_qty"),
                    ask_qty=message.get("ask_qty"),
                )
                for callback in self._tick_callbacks:
                    try:
                        callback(tick)
                    except Exception as e:
                        logger.error(f"Tick callback error: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def stop_websocket(self) -> None:
        self._running = False
        for task in self._ws_tasks:
            task.cancel()
        await asyncio.gather(*self._ws_tasks, return_exceptions=True)
        self._ws_tasks.clear()

    async def close(self) -> None:
        await self.stop_websocket()
        if self.angelone_client:
            await self.angelone_client.logout()
        if self.flattrade_client:
            await self.flattrade_client.close()


# Singleton instance
market_data_service = MarketDataService()