"""
Background Signal Scanner Service.
Continuously scans the market for trading setups and generates signals.
Runs independently of which frontend tab is open.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
import pandas as pd

from app.config.settings import settings
from app.market_data.service import market_data_service
from app.services.indicator_engine import indicator_engine, IndicatorValues
from app.services.market_structure import market_structure_engine, MarketStructure
from app.services.regime_detection import regime_detection_engine, RegimeAnalysis
from app.strategies.engine import strategy_engine, SignalDirection as StrategySignalDirection
from app.core.signal_lifecycle import (
    signal_lifecycle, SignalDirection, SignalStatus, StructuredSignal
)

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 30  # Scan every 30 seconds
MAX_CONSECUTIVE_ERRORS = 5
HISTORICAL_CACHE_SECONDS = 300  # Cache historical data for 5 minutes


class SignalScanner:
    """
    Background scanner that continuously evaluates market conditions
    and generates trading signals when setups are detected.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._error_count = 0
        self._last_signals: Dict[str, str] = {}  # index_name -> signal_id
        self._historical_cache: Dict[str, tuple] = {}  # symbol -> (timestamp, data)

    async def start(self) -> None:
        """Start the background scanning loop."""
        if self._running:
            logger.warning("Signal scanner already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("Signal scanner started")

    async def stop(self) -> None:
        """Stop the background scanning loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Signal scanner stopped")

    async def _scan_loop(self) -> None:
        """Main scanning loop."""
        while self._running:
            try:
                await self._scan_all_instruments()
                self._error_count = 0
            except Exception as e:
                self._error_count += 1
                logger.error(f"Signal scanner error (count={self._error_count}): {e}")
                if self._error_count >= MAX_CONSECUTIVE_ERRORS:
                    logger.critical("Too many consecutive scanner errors, stopping")
                    self._running = False
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)

    async def _scan_all_instruments(self) -> None:
        """Scan all configured trading instruments."""
        instruments = settings.TRADING_INSTRUMENTS or ["NIFTY", "SENSEX"]

        # Add jitter to avoid hitting API at same time for both instruments
        jitter = random.uniform(0, 2)

        for i, instrument in enumerate(instruments):
            # Add small delay between instrument scans
            if i > 0:
                await asyncio.sleep(jitter)
            await self._scan_instrument(instrument)

    async def _scan_instrument(self, symbol: str) -> None:
        """Scan a single instrument for trade setups."""
        # Get live LTP
        ltp_result = await market_data_service.get_ltp("NSE", [symbol])
        spot_price = self._extract_spot_price(ltp_result, symbol)

        if spot_price <= 0:
            logger.warning(f"No live price for {symbol}, skipping scan")
            return

        # Check if we have recent historical data cached (within HISTORICAL_CACHE_SECONDS)
        now = datetime.now()
        cache_key = symbol
        cached_data = self._historical_cache.get(cache_key)
        if cached_data:
            cached_time, cached_hist = cached_data
            if (now - cached_time).total_seconds() < HISTORICAL_CACHE_SECONDS:
                hist_result = cached_hist
                logger.debug(f"{symbol}: Using cached historical data ({len(hist_result)} candles)")
            else:
                # Cache expired, fetch fresh
                hist_result = await self._fetch_historical_data(symbol, now)
                self._historical_cache[cache_key] = (now, hist_result)
        else:
            hist_result = await self._fetch_historical_data(symbol, now)
            self._historical_cache[cache_key] = (now, hist_result)

        if not hist_result or len(hist_result) < 50:
            logger.warning(f"{symbol}: Not enough historical data ({len(hist_result) if hist_result else 0} candles)")
            return

        # Build DataFrame
        df = pd.DataFrame(hist_result)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Calculate indicators
        indicators_df = indicator_engine.calculate_all(df)
        indicators = indicators_df.iloc[-1].to_dict() if not indicators_df.empty else {}

        # Detect market structure
        structure = market_structure_engine.analyze(df)

        # Detect market regime
        regime = regime_detection_engine.detect(df, indicators)

        # Current price as Decimal
        current_price = Decimal(str(spot_price))
        current_time = pd.Timestamp(now)

        # Run strategy engine
        logger.info(f"Scanning {symbol}: spot={spot_price}, regime={regime.regime.value if hasattr(regime.regime, 'value') else str(regime.regime)}, adx={regime.adx if hasattr(regime, 'adx') else 'N/A'}")
        strategy_signals = strategy_engine.evaluate_all(
            df=df,
            indicators=indicators,
            structure=structure,
            regime=regime,
            current_price=current_price,
            current_time=current_time,
        )

        if not strategy_signals:
            logger.info(f"{symbol}: No strategy signals found (regime={regime.regime.value if hasattr(regime.regime, 'value') else str(regime.regime)})")
            return

        # Take the best signal (highest confidence)
        best_signal = max(strategy_signals, key=lambda s: s.confidence)
        logger.info(f"{symbol}: Strategy signal found! {best_signal.strategy_type.value} {best_signal.direction.value} entry={best_signal.entry_price} conf={best_signal.confidence}")

        # Map strategy direction to signal direction
        if best_signal.direction == StrategySignalDirection.BULLISH:
            direction = SignalDirection.BUY_CE
        elif best_signal.direction == StrategySignalDirection.BEARISH:
            direction = SignalDirection.BUY_PE
        else:
            return

        # Skip if same signal already exists for this instrument
        existing_signal_id = self._last_signals.get(symbol)
        if existing_signal_id:
            existing = signal_lifecycle.get_signal(existing_signal_id)
            if existing and existing.status in (SignalStatus.SCANNING, SignalStatus.CONFIRMED, SignalStatus.ACTIVE):
                return  # Already have an active signal for this instrument

        # Create structured signal
        signal = await signal_lifecycle.create_signal(
            index_name=symbol,
            direction=direction,
            underlying_spot=current_price,
            strategy_name=best_signal.strategy_type.value,
            confidence=best_signal.confidence,
            market_regime=regime.regime.value if hasattr(regime.regime, 'value') else str(regime.regime),
            confirmation_indicators=list(best_signal.metadata.keys()) if best_signal.metadata else [],
            explanation=f"{best_signal.strategy_type.value} setup detected on {symbol}",
            entry_price=float(best_signal.entry_price),
            stop_loss=float(best_signal.stop_price),
            target_1=float(best_signal.target_price),
            target_2=None,
            risk_reward=float(best_signal.rr_ratio) if best_signal.rr_ratio else None,
            data_provider=market_data_service.active_provider.value if market_data_service.active_provider else "yahoo",
            data_freshness="live",
        )

        self._last_signals[symbol] = signal.signal_id

        # Emit signal via Socket.io to all connected frontend clients
        from app.main import sio
        await sio.emit("signal", signal.to_dict())
        await sio.emit("signal_generated", signal.to_dict())

        logger.info(
            f"Signal generated: {symbol} {direction.value} "
            f"entry={best_signal.entry_price} sl={best_signal.stop_price} "
            f"target={best_signal.target_price} conf={best_signal.confidence}"
        )

    async def _fetch_historical_data(self, symbol: str, now: datetime) -> List[Dict[str, Any]]:
        """Fetch historical data with retry logic for rate limits."""
        from_date = now - timedelta(days=2)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                hist_result = await market_data_service.get_historical_data(
                    "NSE", symbol, "5m",
                    from_date.strftime("%Y-%m-%d %H:%M:%S"),
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                )
                if hist_result:
                    return hist_result
            except Exception as e:
                if "403" in str(e) or "rate limit" in str(e).lower():
                    wait_time = 5 * (attempt + 1)
                    logger.warning(f"{symbol}: Rate limited, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"{symbol}: Historical fetch error: {e}")
                break
        return []

    @staticmethod
    def _extract_spot_price(ltp_result: Dict[str, Any], symbol: str) -> float:
        """Extract spot price from LTP response."""
        if not ltp_result or not isinstance(ltp_result, dict):
            return 0.0

        data = ltp_result.get("data", ltp_result)

        # Angel One format: {"data": {"fetched": [{"ltp": ...}]}}
        if isinstance(data, dict) and "fetched" in data:
            fetched = data["fetched"]
            if isinstance(fetched, list) and len(fetched) > 0:
                return float(fetched[0].get("ltp", 0))

        # Symbol-keyed dict: {"NIFTY": {"ltp": ...}}
        if isinstance(data, dict):
            if "ltp" in data:
                return float(data["ltp"])
            for quote in data.values():
                if isinstance(quote, dict) and "ltp" in quote:
                    return float(quote["ltp"])

        # List format: [{"ltp": ...}]
        if isinstance(data, list) and len(data) > 0:
            return float(data[0].get("ltp", 0))

        return 0.0


# Singleton instance
signal_scanner = SignalScanner()
