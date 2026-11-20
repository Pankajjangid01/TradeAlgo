import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.config.settings import settings
from app.core.historical_cache import historical_cache, IST
from app.core.websocket_manager import CentralizedWebSocketManager
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
        self._websocket_manager: Optional[CentralizedWebSocketManager] = None

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
    async def _resolve_tokens(self, exchange: str, tokens: List[str], client) -> List[str]:
        """Resolve symbol names to instrument tokens. Numeric tokens pass through."""
        resolved = []
        master = await client.get_instrument_master(exchange)
        # Build lookup: symbol name -> token
        lookup = {}
        for inst in master:
            sym = inst.get("symbol", "").upper()
            name = inst.get("name", "").upper()
            token = inst.get("symboltoken") or inst.get("token")
            if token:
                lookup[sym] = str(token)
                if name and name != sym:
                    lookup[name] = str(token)

        for token in tokens:
            if token.isdigit():
                resolved.append(token)
            else:
                key = token.upper()
                found = lookup.get(key)
                if not found:
                    # Try prefix match (e.g. "NIFTY" matches "NIFTY 50")
                    for sym, tok in lookup.items():
                        if sym == key or sym.startswith(key + " "):
                            found = tok
                            break
                resolved.append(found if found else token)
        return resolved

    async def get_ltp(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        resolved_tokens = await self._resolve_tokens(exchange, tokens, client)
        return await client.get_ltp(exchange, resolved_tokens)

    async def get_quote(self, exchange: str, tokens: List[str]) -> Dict[str, Any]:
        client = self.get_active_client()
        if not client:
            raise Exception("No active market data provider")
        resolved_tokens = await self._resolve_tokens(exchange, tokens, client)
        return await client.get_quote(exchange, resolved_tokens)

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

        # Parse date range
        from_dt = datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S") if " " in from_date else datetime.strptime(from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S") if " " in to_date else datetime.strptime(to_date, "%Y-%m-%d")

        # Make timezone-aware (IST)
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=IST)
        if to_dt.tzinfo is None:
            to_dt = to_dt.replace(tzinfo=IST)

        # Check cache first
        cached_candles, missing_ranges = await historical_cache.get_cached_candles(
            exchange, symbol_token, interval, from_dt, to_dt
        )

        if not missing_ranges:
            # All data in cache
            logger.info(f"Cache HIT: {exchange}:{symbol_token}:{interval} {from_date} to {to_date} ({len(cached_candles)} candles)")
            return cached_candles

        logger.info(
            f"Cache PARTIAL: {exchange}:{symbol_token}:{interval} "
            f"({len(cached_candles)} cached, {len(missing_ranges)} missing ranges)"
        )

        # Fetch missing ranges from broker
        all_candles = list(cached_candles)
        for range_start, range_end in missing_ranges:
            range_from = range_start.strftime("%Y-%m-%d %H:%M:%S")
            range_to = range_end.strftime("%Y-%m-%d %H:%M:%S")
            try:
                fetched = await client.get_historical_data(
                    exchange, symbol_token, interval, range_from, range_to
                )
                if fetched:
                    # Normalize fetched candles
                    normalized = []
                    for c in fetched:
                        normalized.append({
                            "timestamp": c.get("timestamp") or c.get("time") or c.get("datetime", ""),
                            "open": float(c.get("open", 0)),
                            "high": float(c.get("high", 0)),
                            "low": float(c.get("low", 0)),
                            "close": float(c.get("close", 0)),
                            "volume": int(c.get("volume", 0)),
                            "oi": int(c.get("oi", 0)) if c.get("oi") else None,
                        })
                    all_candles.extend(normalized)
                    await historical_cache.store_candles(exchange, symbol_token, interval, normalized)
            except Exception as e:
                logger.error(f"Failed to fetch historical {range_from} to {range_to}: {e}")

        # Sort and deduplicate by timestamp
        seen = set()
        unique_candles = []
        for c in sorted(all_candles, key=lambda x: x.get("timestamp", "")):
            ts = c.get("timestamp", "")
            if ts not in seen:
                seen.add(ts)
                unique_candles.append(c)

        logger.info(
            f"Historical fetch complete: {exchange}:{symbol_token}:{interval} "
            f"returned {len(unique_candles)} candles"
        )
        return unique_candles

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

    async def _ensure_websocket_manager(self) -> CentralizedWebSocketManager:
        """Lazy-initialize the centralized WebSocket manager."""
        if self._websocket_manager is None:
            if not self.angelone_client:
                raise Exception("Angel One client not initialized for WebSocket")
            self._websocket_manager = await CentralizedWebSocketManager.get_instance(self.angelone_client)
            await self._websocket_manager.start()
        return self._websocket_manager

    async def start_websocket(self, tokens: List[str], callback_id: str = "default",
                              callback: Optional[Callable[[str, float, Dict[str, Any]], None]] = None) -> None:
        """
        Subscribe to tokens via the centralized WebSocket manager.

        If callback is provided, it's registered as a subscriber receiving ticks.
        Tokens are always subscribed on the shared connection.
        """
        manager = await self._ensure_websocket_manager()

        # Subscribe tokens on the shared connection
        if tokens:
            await manager.ws_client.subscribe(tokens)

        # Register callback subscriber if provided
        if callback:
            manager.subscribe_callback(callback_id, callback, tokens)

        # Also notify legacy tick callbacks
        if callback:
            async def _bridge(token: str, ltp: float, raw: Dict[str, Any]):
                tick = MarketTick(
                    instrument_token=str(token),
                    timestamp=datetime.now(IST),
                    ltp=Decimal(str(ltp)),
                    volume=raw.get("volume", 0),
                    oi=raw.get("oi"),
                    bid=Decimal(str(raw["bid"])) if raw.get("bid") else None,
                    ask=Decimal(str(raw["ask"])) if raw.get("ask") else None,
                    bid_qty=raw.get("bid_qty"),
                    ask_qty=raw.get("ask_qty"),
                )
                for cb in self._tick_callbacks:
                    try:
                        cb(tick)
                    except Exception as e:
                        logger.error(f"Legacy tick callback error: {e}")
            manager.subscribe_callback(f"{callback_id}_legacy", _bridge, tokens)

    def get_websocket_stats(self) -> Optional[Dict[str, Any]]:
        """Return WebSocket connection stats for dashboard monitoring."""
        if self._websocket_manager:
            return self._websocket_manager.get_stats()
        return None

    def is_websocket_connected(self) -> bool:
        if self._websocket_manager:
            return self._websocket_manager.is_connected()
        return False

    def is_market_data_fresh(self, max_age_seconds: float = 30.0) -> bool:
        """Check if latest WebSocket tick is fresh."""
        if self._websocket_manager:
            return self._websocket_manager.is_data_fresh(max_age_seconds)
        return False

    async def stop_websocket(self) -> None:
        if self._websocket_manager:
            await self._websocket_manager.stop()
            self._websocket_manager = None
        self._running = False
        for task in self._ws_tasks:
            task.cancel()
        await asyncio.gather(*self._ws_tasks, return_exceptions=True)
        self._ws_tasks.clear()

    async def _process_angelone_message(self, message: Dict[str, Any]) -> None:
        try:
            if "token" in message and "ltp" in message:
                tick = MarketTick(
                    instrument_token=str(message["token"]),
                    timestamp=datetime.now(IST),
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

    async def close(self) -> None:
        await self.stop_websocket()
        if self.angelone_client:
            await self.angelone_client.logout()
        if self.flattrade_client:
            await self.flattrade_client.close()


# Singleton instance
market_data_service = MarketDataService()