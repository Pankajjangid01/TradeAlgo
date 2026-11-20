"""
Centralized WebSocket manager for live market data.

Maintains a single persistent WebSocket connection to Angel One SmartAPI.
Multiple subscribers can subscribe/unsubscribe to tokens; ticks are fanned
out to all registered callbacks.

Features:
- Shared persistent connection (no separate WS per subscriber)
- Automatic reconnection with exponential backoff
- Heartbeat monitoring (stale-data detection)
- Subscription restoration on reconnect
- Async-safe fan-out to subscribers
- Token-level subscription tracking
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from typing import Callable, Dict, List, Optional, Set

from app.market_data.angelone_client import AngelOneClient, AngelOneWebSocketClient

logger = logging.getLogger(__name__)


@dataclass
class WebSocketStats:
    connected: bool = False
    subscribed_tokens: int = 0
    subscriber_count: int = 0
    total_ticks: int = 0
    last_tick_time: Optional[float] = None
    reconnect_count: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float = 0.0
    connected_at: Optional[float] = None


class CentralizedWebSocketManager:
    """
    Singleton WebSocket manager that maintains ONE connection to Angel One.

    Subscribers register callbacks and subscribe to tokens. The manager
    handles connection lifecycle, reconnection, heartbeat, and tick fan-out.
    """

    _instance: Optional["CentralizedWebSocketManager"] = None
    _instance_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, client: Optional[AngelOneClient] = None) -> "CentralizedWebSocketManager":
        async with cls._instance_lock:
            if cls._instance is None:
                if client is None:
                    raise ValueError("AngelOneClient required for first initialization")
                cls._instance = CentralizedWebSocketManager(client)
            return cls._instance

    def __init__(self, client: AngelOneClient):
        self.client = client
        self.ws_client: Optional[AngelOneWebSocketClient] = None
        self._subscribers: Dict[str, Callable] = {}  # callback_id -> callback
        self._subscriber_tokens: Dict[str, Set[str]] = {}  # callback_id -> set of tokens
        self._all_subscribed_tokens: Set[str] = set()
        self._running = False
        self._ws_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stats = WebSocketStats()
        self._connect_lock = asyncio.Lock()
        self._reconnect_delay = 5.0
        self._max_reconnect_delay = 60.0
        self._heartbeat_interval = 30.0
        self._stale_threshold = 60.0  # seconds without tick = stale data
        self._subscriptions_to_restore: Set[str] = set()

    # ------------------------------------------------------------------
    # Subscriber management
    # ------------------------------------------------------------------

    def subscribe_callback(self, callback_id: str, callback: Callable, tokens: List[str]) -> None:
        """Register a subscriber callback for specific tokens."""
        self._subscribers[callback_id] = callback
        self._subscriber_tokens[callback_id] = set(tokens)
        self._all_subscribed_tokens.update(tokens)
        self._stats.subscriber_count = len(self._subscribers)
        self._stats.subscribed_tokens = len(self._all_subscribed_tokens)
        logger.info(
            f"WebSocket subscriber '{callback_id}' subscribed to {len(tokens)} tokens: {tokens[:5]}..."
        )

        # If already connected, subscribe immediately
        if self._running and self.ws_client:
            asyncio.create_task(self.ws_client.subscribe(list(tokens)))

    def unsubscribe_callback(self, callback_id: str) -> None:
        """Unregister a subscriber and its tokens."""
        tokens = self._subscriber_tokens.pop(callback_id, set())
        self._subscribers.pop(callback_id, None)

        # Recompute global token set
        self._all_subscribed_tokens = set()
        for tset in self._subscriber_tokens.values():
            self._all_subscribed_tokens.update(tset)

        self._stats.subscriber_count = len(self._subscribers)
        self._stats.subscribed_tokens = len(self._all_subscribed_tokens)
        logger.info(f"WebSocket subscriber '{callback_id}' unsubscribed ({len(tokens)} tokens removed)")

    def update_subscriber_tokens(self, callback_id: str, tokens: List[str]) -> None:
        """Update the token set for an existing subscriber."""
        old_tokens = self._subscriber_tokens.get(callback_id, set())
        self._subscriber_tokens[callback_id] = set(tokens)

        # Recompute global set
        self._all_subscribed_tokens = set()
        for tset in self._subscriber_tokens.values():
            self._all_subscribed_tokens.update(tset)

        self._stats.subscribed_tokens = len(self._all_subscribed_tokens)

        # Subscribe to new tokens, unsubscribe from removed ones
        new_tokens = set(tokens) - old_tokens
        removed_tokens = old_tokens - set(tokens)

        if self._running and self.ws_client:
            if new_tokens:
                asyncio.create_task(self.ws_client.subscribe(list(new_tokens)))
            if removed_tokens:
                asyncio.create_task(self.ws_client.unsubscribe(list(removed_tokens)))

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the WebSocket connection and heartbeat monitor."""
        if self._running:
            logger.warning("WebSocket manager already running")
            return

        self._running = True
        self._stats.connected_at = time.monotonic()
        self._ws_task = asyncio.create_task(self._run_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Centralized WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket connection and cleanup."""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self.ws_client:
            await self.ws_client.stop()
            self.ws_client = None
        self._stats.connected = False
        logger.info("Centralized WebSocket manager stopped")

    # ------------------------------------------------------------------
    # Internal run loop
    # ------------------------------------------------------------------

    async def _run_loop(self) -> None:
        """Main WebSocket run loop with reconnection."""
        while self._running:
            try:
                async with self._connect_lock:
                    await self._connect_and_subscribe()

                # Run message loop
                await self._message_loop()

            except Exception as e:
                logger.error(f"WebSocket run loop error: {e}")
                self._stats.last_error = str(e)
                self._stats.connected = False

                if self._running:
                    wait = min(self._reconnect_delay, self._max_reconnect_delay)
                    logger.info(f"Reconnecting in {wait:.1f}s...")
                    await asyncio.sleep(wait)
                    self._reconnect_delay = min(self._reconnect_delay * 1.5, self._max_reconnect_delay)
                    self._stats.reconnect_count += 1

    async def _connect_and_subscribe(self) -> None:
        """Connect WebSocket and restore subscriptions."""
        self.ws_client = AngelOneWebSocketClient(self.client)

        def on_message(message: Dict[str, Any]):
            asyncio.create_task(self._on_tick(message))

        def on_error(error: Exception):
            logger.error(f"WebSocket error callback: {error}")
            self._stats.last_error = str(error)

        def on_close():
            logger.warning("WebSocket closed")
            self._stats.connected = False

        self.ws_client.on_message(on_message)
        self.ws_client.on_error(on_error)
        self.ws_client.on_close(on_close)

        await self.ws_client.connect()
        self._stats.connected = True
        self._stats.reconnect_count = 0
        self._reconnect_delay = 5.0
        self._stats.last_error = None

        # Restore subscriptions
        if self._all_subscribed_tokens:
            await self.ws_client.subscribe(list(self._all_subscribed_tokens))
            logger.info(f"Restored {len(self._all_subscribed_tokens)} token subscriptions")

    async def _message_loop(self) -> None:
        """Receive and process WebSocket messages."""
        while self._running and self.ws_client and self.ws_client.ws:
            try:
                message = await self.ws_client.ws.recv()
                if message:
                    await self._on_tick(json.loads(message))
            except Exception as e:
                logger.error(f"Message receive error: {e}")
                raise  # Will trigger reconnection

    async def _on_tick(self, message: Dict[str, Any]) -> None:
        """Process an incoming tick and fan out to subscribers."""
        try:
            token = message.get("token") or message.get("symboltoken")
            ltp = message.get("ltp")

            if token is None or ltp is None:
                return

            now = time.monotonic()
            self._stats.total_ticks += 1
            self._stats.last_tick_time = now

            # Fan out to all subscribers interested in this token
            for callback_id, callback in self._subscribers.items():
                subscriber_tokens = self._subscriber_tokens.get(callback_id, set())
                if str(token) in subscriber_tokens:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(token, ltp, message)
                        else:
                            callback(token, ltp, message)
                    except Exception as e:
                        logger.error(f"Subscriber callback '{callback_id}' error: {e}")

        except Exception as e:
            logger.error(f"Error processing tick: {e}")

    async def _heartbeat_loop(self) -> None:
        """Monitor connection health and detect stale data."""
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)

            if not self._stats.connected:
                continue

            now = time.monotonic()
            if self._stats.last_tick_time:
                silence = now - self._stats.last_tick_time
                if silence > self._stale_threshold:
                    logger.warning(
                        f"WebSocket stale: no ticks for {silence:.0f}s (threshold {self._stale_threshold}s)"
                    )
                    self._stats.last_error = f"stale data: {silence:.0f}s silence"
                    # Trigger reconnection
                    self._running = False  # Will cause run loop to exit and reconnect

            if self._stats.connected_at:
                self._stats.uptime_seconds = now - self._stats.connected_at

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "connected": self._stats.connected,
            "subscribed_tokens": self._stats.subscribed_tokens,
            "subscriber_count": self._stats.subscriber_count,
            "total_ticks": self._stats.total_ticks,
            "last_tick_time": self._stats.last_tick_time,
            "reconnect_count": self._stats.reconnect_count,
            "last_error": self._stats.last_error,
            "uptime_seconds": round(self._stats.uptime_seconds, 1),
            "stale_threshold_seconds": self._stale_threshold,
        }

    def is_connected(self) -> bool:
        return self._stats.connected and self.ws_client is not None

    def is_data_fresh(self, max_age_seconds: float = 30.0) -> bool:
        """Check if latest tick is within max_age_seconds."""
        if self._stats.last_tick_time is None:
            return False
        return (time.monotonic() - self._stats.last_tick_time) <= max_age_seconds
