"""
Tests for signal lifecycle manager.
"""
import pytest
import asyncio
from decimal import Decimal

from app.core.signal_lifecycle import (
    SignalLifecycleManager,
    SignalStatus,
    SignalDirection,
    signal_lifecycle,
)


class TestSignalLifecycle:
    """Test signal state machine and duplicate prevention."""

    @pytest.fixture
    def lifecycle(self):
        return SignalLifecycleManager(signal_ttl_seconds=3600)

    @pytest.mark.asyncio
    async def test_create_signal_scanning(self, lifecycle):
        """New signal should be in SCANNING state."""
        signal = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22000"),
            strategy_name="ORB",
            confidence=Decimal("0.75"),
            market_regime="breakout_transition",
            confirmation_indicators=["ema_9_above_20", "volume_confirmed"],
            explanation="ORB breakout above opening range high",
            entry_price=Decimal("22050"),
            stop_loss=Decimal("21950"),
            target_1=Decimal("22250"),
            target_2=Decimal("22450"),
            risk_reward=Decimal("2.0"),
        )

        assert signal.status == SignalStatus.SCANNING
        assert signal.index_name == "NIFTY"
        assert signal.direction == SignalDirection.BUY_CE
        assert signal.confidence_score == Decimal("0.75")

    @pytest.mark.asyncio
    async def test_duplicate_signal_blocked(self, lifecycle):
        """Creating same index+direction signal should return existing one."""
        signal1 = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22000"),
            strategy_name="ORB",
            confidence=Decimal("0.75"),
            market_regime="breakout_transition",
            confirmation_indicators=[],
            explanation="Test signal",
        )

        signal2 = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22100"),
            strategy_name="VWAP",
            confidence=Decimal("0.80"),
            market_regime="strong_bullish",
            confirmation_indicators=[],
            explanation="Second signal same direction",
        )

        # Should return the first signal (duplicate blocked)
        assert signal2.signal_id == signal1.signal_id
        assert signal2.status == SignalStatus.SCANNING  # First signal still scanning

    @pytest.mark.asyncio
    async def test_signal_lifecycle_transitions(self, lifecycle):
        """Signal should flow SCANNING → CONFIRMED → ACTIVE → terminal."""
        signal = await lifecycle.create_signal(
            index_name="SENSEX",
            direction=SignalDirection.BUY_PE,
            underlying_spot=Decimal("72000"),
            strategy_name="S/R Breakout",
            confidence=Decimal("0.70"),
            market_regime="strong_bearish",
            confirmation_indicators=["adx_above_25"],
            explanation="S/R breakdown",
            entry_price=Decimal("71950"),
            stop_loss=Decimal("72100"),
            target_1=Decimal("71700"),
        )

        # SCANNING → CONFIRMED
        confirmed = await lifecycle.confirm_signal(signal.signal_id)
        assert confirmed is not None
        assert confirmed.status == SignalStatus.CONFIRMED

        # CONFIRMED → ACTIVE
        activated = await lifecycle.activate_signal(signal.signal_id)
        assert activated is not None
        assert activated.status == SignalStatus.ACTIVE

        # ACTIVE → TARGET_HIT
        closed = await lifecycle.close_signal(signal.signal_id, SignalStatus.TARGET_HIT)
        assert closed is not None
        assert closed.status == SignalStatus.TARGET_HIT

    @pytest.mark.asyncio
    async def test_signal_expiry_on_duplicate(self, lifecycle):
        """Creating same index+direction while SCANNING returns existing signal (no new signal)."""
        signal1 = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22000"),
            strategy_name="ORB",
            confidence=Decimal("0.70"),
            market_regime="breakout_transition",
            confirmation_indicators=[],
            explanation="First signal",
        )

        # Create new signal for same index+direction while first is SCANNING
        signal2 = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22100"),
            strategy_name="VWAP",
            confidence=Decimal("0.80"),
            market_regime="strong_bullish",
            confirmation_indicators=[],
            explanation="Second signal",
        )

        # Should return the SAME signal (duplicate blocked, not expired)
        assert signal2.signal_id == signal1.signal_id
        assert signal2.status == SignalStatus.SCANNING

        # Terminal state signals can be replaced
        await lifecycle.close_signal(signal1.signal_id, SignalStatus.TARGET_HIT)
        signal3 = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22200"),
            strategy_name="S/R",
            confidence=Decimal("0.85"),
            market_regime="strong_bullish",
            confirmation_indicators=[],
            explanation="Third signal after terminal",
        )
        assert signal3.signal_id != signal1.signal_id
        assert signal3.status == SignalStatus.SCANNING

    @pytest.mark.asyncio
    async def test_different_directions_allowed(self, lifecycle):
        """BUY_CE and BUY_PE for same index should both be allowed."""
        signal_ce = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22000"),
            strategy_name="ORB",
            confidence=Decimal("0.70"),
            market_regime="bullish",
            confirmation_indicators=[],
            explanation="CE signal",
        )

        signal_pe = await lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_PE,
            underlying_spot=Decimal("22000"),
            strategy_name="ORB",
            confidence=Decimal("0.70"),
            market_regime="bullish",
            confirmation_indicators=[],
            explanation="PE signal",
        )

        assert signal_ce.signal_id != signal_pe.signal_id

    @pytest.mark.asyncio
    async def test_get_active_signals(self, lifecycle):
        """get_active_signals should return only ACTIVE signals."""
        signal = await lifecycle.create_signal(
            index_name="BANKNIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("48000"),
            strategy_name="ORB",
            confidence=Decimal("0.75"),
            market_regime="breakout_transition",
            confirmation_indicators=[],
            explanation="Test",
        )

        await lifecycle.confirm_signal(signal.signal_id)
        await lifecycle.activate_signal(signal.signal_id)

        active = lifecycle.get_active_signals()
        assert len(active) == 1
        assert active[0].signal_id == signal.signal_id

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, lifecycle):
        """Old SCANNING signals should be expired by cleanup."""
        # Create signal with very short TTL
        short_lifecycle = SignalLifecycleManager(signal_ttl_seconds=0)
        signal = await short_lifecycle.create_signal(
            index_name="NIFTY",
            direction=SignalDirection.BUY_CE,
            underlying_spot=Decimal("22000"),
            strategy_name="ORB",
            confidence=Decimal("0.70"),
            market_regime="bullish",
            confirmation_indicators=[],
            explanation="Test",
        )

        # Manually age the signal
        for state in short_lifecycle._signals.values():
            state.created_at = 0  # Very old

        expired_count = short_lifecycle.cleanup_expired()
        assert expired_count == 1

        signal_after = short_lifecycle.get_signal(signal.signal_id)
        assert signal_after.status == SignalStatus.EXPIRED

    def test_stats(self, lifecycle):
        """Stats should return signal counts."""
        stats = lifecycle.get_stats()
        assert "total_signals" in stats
        assert "active_signals" in stats
        assert "status_breakdown" in stats
