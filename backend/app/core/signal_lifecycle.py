"""
Signal lifecycle manager and structured signal output.

Signal lifecycle:
    SCANNING → CONFIRMED → ACTIVE → {TARGET_HIT | STOP_LOSS | EXPIRED | CANCELLED}

Structured signal output contains all fields required by the dashboard:
- Index name, direction, spot price, option symbol, strike, expiry, LTP
- Entry, stop-loss, targets, R:R ratio, confidence score, timestamp
- Market regime, strategy name, confirmation indicators, explanation
- Data provider, data freshness status
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from decimal import Decimal

from decimal import Decimal

IST = timezone(timedelta(hours=5, minutes=30))

logger = logging.getLogger(__name__)


class SignalStatus(str, Enum):
    SCANNING = "scanning"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    TARGET_HIT = "target_hit"
    STOP_LOSS = "stop_loss"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignalDirection(str, Enum):
    BUY_CE = "BUY CE"
    BUY_PE = "BUY PE"
    WAIT = "WAIT"


@dataclass
class StructuredSignal:
    """Complete structured signal output for the dashboard."""

    # Core identification
    signal_id: str
    status: SignalStatus
    index_name: str  # NIFTY, BANKNIFTY, SENSEX

    # Direction and underlying
    direction: SignalDirection
    underlying_spot_price: Decimal
    option_symbol: Optional[str] = None
    strike_price: Optional[Decimal] = None
    expiry: Optional[str] = None
    option_ltp: Optional[Decimal] = None

    # Trade levels
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    target_1: Optional[Decimal] = None
    target_2: Optional[Decimal] = None
    risk_reward_ratio: Optional[Decimal] = None

    # Quality metrics
    confidence_score: Decimal = Decimal("0.0")
    signal_timestamp: str = ""

    # Context
    market_regime: str = "uncertain"
    strategy_name: str = ""
    confirmation_indicators: List[str] = field(default_factory=list)
    signal_explanation: str = ""

    # Data provenance
    data_provider: str = "angelone"
    data_freshness: str = "live"  # live, delayed, cached

    # Risk
    max_risk_per_trade_pct: Optional[float] = None
    position_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = asdict(self)
        # Convert Decimals to strings
        for key in [
            "underlying_spot_price", "strike_price", "option_ltp",
            "entry_price", "stop_loss", "target_1", "target_2",
            "risk_reward_ratio", "confidence_score",
        ]:
            val = result.get(key)
            if isinstance(val, Decimal):
                result[key] = str(val)
            elif val is None:
                result[key] = None
        # Convert enums
        result["status"] = self.status.value
        result["direction"] = self.direction.value
        return result


@dataclass
class SignalState:
    """Internal state tracking for a signal."""
    signal: StructuredSignal
    created_at: float
    confirmed_at: Optional[float] = None
    activated_at: Optional[float] = None
    terminal_at: Optional[float] = None
    price_history: List[Dict[str, Any]] = field(default_factory=list)


class SignalLifecycleManager:
    """
    Manages signal lifecycle states and prevents duplicate signals.

    States: SCANNING → CONFIRMED → ACTIVE → terminal
    """

    def __init__(self, signal_ttl_seconds: int = 3600):
        self.signal_ttl = signal_ttl_seconds
        self._signals: Dict[str, SignalState] = {}
        self._active_signals: Dict[str, SignalState] = {}  # index_name -> active signal
        self._lock = asyncio.Lock()
        self._signal_counter = 0

    def _generate_id(self) -> str:
        self._signal_counter += 1
        return f"sig_{int(time.time())}_{self._signal_counter}"

    def _signal_key(self, index_name: str, direction: SignalDirection) -> str:
        """Key for duplicate detection: one active signal per index+direction."""
        return f"{index_name}:{direction.value}"

    async def create_signal(
        self,
        index_name: str,
        direction: SignalDirection,
        underlying_spot: Decimal,
        strategy_name: str,
        confidence: Decimal,
        market_regime: str,
        confirmation_indicators: List[str],
        explanation: str,
        entry_price: Optional[Decimal] = None,
        stop_loss: Optional[Decimal] = None,
        target_1: Optional[Decimal] = None,
        target_2: Optional[Decimal] = None,
        risk_reward: Optional[Decimal] = None,
        option_symbol: Optional[str] = None,
        strike: Optional[Decimal] = None,
        expiry: Optional[str] = None,
        option_ltp: Optional[Decimal] = None,
        data_provider: str = "angelone",
        data_freshness: str = "live",
    ) -> StructuredSignal:
        """Create a new signal in SCANNING state. Prevents duplicates."""
        async with self._lock:
            key = self._signal_key(index_name, direction)

            # Check for existing signal for same index+direction
            existing = self._signals.get(key)
            if existing:
                if existing.signal.status in (SignalStatus.CONFIRMED, SignalStatus.ACTIVE):
                    logger.info(
                        f"Duplicate signal blocked: {index_name} {direction.value} "
                        f"already {existing.signal.status.value}"
                    )
                    return existing.signal
                elif existing.signal.status == SignalStatus.SCANNING:
                    # Return existing SCANNING signal instead of creating new one
                    logger.info(
                        f"Duplicate SCANNING signal returned: {index_name} {direction.value}"
                    )
                    return existing.signal
                # Terminal states - fall through to create new

            signal_id = self._generate_id()
            now_ist = datetime.now(IST)
            signal = StructuredSignal(
                signal_id=signal_id,
                status=SignalStatus.SCANNING,
                index_name=index_name,
                direction=direction,
                underlying_spot_price=underlying_spot,
                option_symbol=option_symbol,
                strike_price=strike,
                expiry=expiry,
                option_ltp=option_ltp,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_1=target_1,
                target_2=target_2,
                risk_reward_ratio=risk_reward,
                confidence_score=confidence,
                signal_timestamp=now_ist.isoformat(),
                market_regime=market_regime,
                strategy_name=strategy_name,
                confirmation_indicators=confirmation_indicators,
                signal_explanation=explanation,
                data_provider=data_provider,
                data_freshness=data_freshness,
            )

            state = SignalState(signal=signal, created_at=time.monotonic())
            self._signals[key] = state

            logger.info(
                f"Signal created: {signal_id} {index_name} {direction.value} "
                f"status=SCANNING confidence={confidence}"
            )
            return signal

    async def confirm_signal(self, signal_id: str) -> Optional[StructuredSignal]:
        """Move signal from SCANNING to CONFIRMED."""
        async with self._lock:
            for state in self._signals.values():
                if state.signal.signal_id == signal_id:
                    if state.signal.status == SignalStatus.SCANNING:
                        state.signal.status = SignalStatus.CONFIRMED
                        state.confirmed_at = time.monotonic()
                        logger.info(f"Signal {signal_id} confirmed")
                        return state.signal
                    return state.signal
        return None

    async def activate_signal(self, signal_id: str) -> Optional[StructuredSignal]:
        """Move signal from CONFIRMED to ACTIVE."""
        async with self._lock:
            for key, state in self._signals.items():
                if state.signal.signal_id == signal_id:
                    if state.signal.status == SignalStatus.CONFIRMED:
                        state.signal.status = SignalStatus.ACTIVE
                        state.activated_at = time.monotonic()
                        # Track as active signal for this index
                        self._active_signals[self._signal_key(state.signal.index_name, state.signal.direction)] = state
                        logger.info(f"Signal {signal_id} activated")
                    return state.signal
        return None

    async def close_signal(
        self,
        signal_id: str,
        final_status: SignalStatus,
        exit_price: Optional[Decimal] = None,
    ) -> Optional[StructuredSignal]:
        """Move signal to terminal state."""
        async with self._lock:
            for key, state in list(self._signals.items()):
                if state.signal.signal_id == signal_id:
                    state.signal.status = final_status
                    state.terminal_at = time.monotonic()
                    # Remove from active tracking
                    active_key = self._signal_key(state.signal.index_name, state.signal.direction)
                    if active_key in self._active_signals:
                        del self._active_signals[active_key]
                    logger.info(f"Signal {signal_id} → {final_status.value}")
                    return state.signal
        return None

    def get_signal(self, signal_id: str) -> Optional[StructuredSignal]:
        for state in self._signals.values():
            if state.signal.signal_id == signal_id:
                return state.signal
        return None

    def get_active_signals(self) -> List[StructuredSignal]:
        return [s.signal for s in self._active_signals.values()]

    def get_signals_by_index(self, index_name: str) -> List[StructuredSignal]:
        return [
            s.signal for s in self._signals.values()
            if s.signal.index_name == index_name
            and s.signal.status in (SignalStatus.CONFIRMED, SignalStatus.ACTIVE)
        ]

    def get_all_signals(self) -> List[StructuredSignal]:
        return [s.signal for s in self._signals.values()]

    def cleanup_expired(self) -> int:
        """Expire SCANNING signals older than TTL. Returns count expired."""
        now = time.monotonic()
        expired = 0
        for state in self._signals.values():
            if state.signal.status == SignalStatus.SCANNING:
                if now - state.created_at > self.signal_ttl:
                    state.signal.status = SignalStatus.EXPIRED
                    state.terminal_at = now
                    expired += 1
        return expired

    def get_stats(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
        for state in self._signals.values():
            st = state.signal.status.value
            status_counts[st] = status_counts.get(st, 0) + 1
        return {
            "total_signals": len(self._signals),
            "active_signals": len(self._active_signals),
            "status_breakdown": status_counts,
            "signal_ttl_seconds": self.signal_ttl,
        }


# Singleton instance
signal_lifecycle = SignalLifecycleManager()
