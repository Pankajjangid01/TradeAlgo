import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.config.settings import settings
from app.strategies.engine import StrategySignal, SignalDirection, StrategyType

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    HARD_REJECTION = "hard_rejection"
    SOFT_CONFLICT = "soft_conflict"


class DecisionState(str, Enum):
    WATCHLIST = "watchlist"
    SETUP_FORMING = "setup_forming"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    APPROVED = "approved"
    REJECTED = "rejected"
    ORDER_PENDING = "order_pending"
    POSITION_OPEN = "position_open"
    EXIT_PENDING = "exit_pending"
    CLOSED = "closed"
    ERROR = "error"
    HALTED = "halted"


@dataclass
class ConflictResult:
    decision: DecisionState
    final_signal: Optional[StrategySignal]
    hard_rejections: List[str]
    soft_conflicts: List[str]
    reasoning: str


class ConflictResolutionEngine:
    def __init__(self):
        self.min_rr_ratio = Decimal("1.5")
        self.max_entry_distance_pct = Decimal("0.5")  # Max 0.5% from signal price

    def resolve(
        self,
        signals: List[StrategySignal],
        ml_prediction: Optional[Dict[str, Any]],
        regime: Dict[str, Any],
        data_quality: Dict[str, Any],
        broker_status: Dict[str, Any],
        risk_check: Dict[str, Any],
        current_price: Decimal
    ) -> ConflictResult:
        """Resolve conflicts between multiple signals and checks."""
        hard_rejections = []
        soft_conflicts = []

        # 1. Hard rejection checks
        hard_rejections.extend(self._check_data_quality(data_quality))
        hard_rejections.extend(self._check_broker_status(broker_status))
        hard_rejections.extend(self._check_risk_limits(risk_check))
        hard_rejections.extend(self._check_price_validity(signals, current_price))
        hard_rejections.extend(self._check_ml_confidence(ml_prediction))

        if hard_rejections:
            return ConflictResult(
                decision=DecisionState.REJECTED,
                final_signal=None,
                hard_rejections=hard_rejections,
                soft_conflicts=[],
                reasoning=f"Hard rejections: {'; '.join(hard_rejections)}"
            )

        # 2. If no signals, return watchlist
        if not signals:
            return ConflictResult(
                decision=DecisionState.WATCHLIST,
                final_signal=None,
                hard_rejections=[],
                soft_conflicts=[],
                reasoning="No valid strategy signals generated"
            )

        # 3. Deduplicate signals from same market move
        deduplicated = self._deduplicate_signals(signals)
        if len(deduplicated) < len(signals):
            soft_conflicts.append(f"Deduplicated {len(signals)} signals to {len(deduplicated)}")

        # 4. Soft conflict checks
        soft_conflicts.extend(self._check_momentum_divergence(deduplicated, ml_prediction))
        soft_conflicts.extend(self._check_regime_alignment(deduplicated, regime))
        soft_conflicts.extend(self._check_indicator_alignment(deduplicated))

        # 5. Rank and select best signal
        ranked = self._rank_signals(deduplicated, ml_prediction, regime, soft_conflicts)

        if not ranked:
            return ConflictResult(
                decision=DecisionState.REJECTED,
                final_signal=None,
                hard_rejections=[],
                soft_conflicts=soft_conflicts,
                reasoning="No signals passed ranking criteria"
            )

        best_signal = ranked[0]

        # 6. Final validation
        if best_signal.rr_ratio < self.min_rr_ratio:
            hard_rejections.append(f"R:R ratio {best_signal.rr_ratio} below minimum {self.min_rr_ratio}")
            return ConflictResult(
                decision=DecisionState.REJECTED,
                final_signal=None,
                hard_rejections=hard_rejections,
                soft_conflicts=soft_conflicts,
                reasoning=f"Insufficient R:R: {best_signal.rr_ratio}"
            )

        # 7. Determine decision state
        if soft_conflicts:
            # Soft conflicts -> WAIT_FOR_CONFIRMATION
            decision = DecisionState.WAIT_FOR_CONFIRMATION
            reasoning = f"Soft conflicts detected: {'; '.join(soft_conflicts)}"
        else:
            decision = DecisionState.APPROVED
            reasoning = f"Signal approved: {best_signal.strategy_type.value} {best_signal.direction.value}"

        return ConflictResult(
            decision=decision,
            final_signal=best_signal,
            hard_rejections=hard_rejections,
            soft_conflicts=soft_conflicts,
            reasoning=reasoning
        )

    def _check_data_quality(self, data_quality: Dict[str, Any]) -> List[str]:
        rejections = []
        if data_quality.get("is_stale", False):
            rejections.append("Market data is stale")
        if data_quality.get("missing_candles", False):
            rejections.append("Missing candles in data feed")
        if data_quality.get("abnormal_price_jump", False):
            rejections.append("Abnormal price jump detected")
        if data_quality.get("websocket_disconnected", False):
            rejections.append("WebSocket disconnected")
        return rejections

    def _check_broker_status(self, broker_status: Dict[str, Any]) -> List[str]:
        rejections = []
        if not broker_status.get("connected", False):
            rejections.append("Broker not connected")
        if broker_status.get("api_error", False):
            rejections.append("Broker API error")
        if broker_status.get("rate_limited", False):
            rejections.append("Broker rate limited")
        return rejections

    def _check_risk_limits(self, risk_check: Dict[str, Any]) -> List[str]:
        rejections = []
        if risk_check.get("daily_loss_limit_reached", False):
            rejections.append("Daily loss limit reached")
        if risk_check.get("max_positions_reached", False):
            rejections.append("Maximum positions reached")
        if risk_check.get("consecutive_losses_exceeded", False):
            rejections.append("Consecutive losses limit exceeded")
        if risk_check.get("kill_switch_active", False):
            rejections.append("Kill switch active")
        return rejections

    def _check_price_validity(self, signals: List[StrategySignal], current_price: Decimal) -> List[str]:
        rejections = []
        for signal in signals:
            distance_pct = abs(float(current_price) - float(signal.entry_price)) / float(signal.entry_price) * 100
            if distance_pct > float(self.max_entry_distance_pct):
                rejections.append(f"Price moved {distance_pct:.2f}% from signal entry")
        return rejections

    def _check_ml_confidence(self, ml_prediction: Optional[Dict[str, Any]]) -> List[str]:
        rejections = []
        if ml_prediction:
            confidence = ml_prediction.get("confidence", 0)
            if confidence < 0.5:
                rejections.append(f"ML confidence too low: {confidence:.2f}")
            if ml_prediction.get("is_out_of_distribution", False):
                rejections.append("ML prediction out of distribution")
        return rejections

    def _deduplicate_signals(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Remove duplicate signals from same market move."""
        if len(signals) <= 1:
            return signals

        # Group by direction
        bullish = [s for s in signals if s.direction.value == "bullish"]
        bearish = [s for s in signals if s.direction.value == "bearish"]

        # Keep highest confidence in each direction
        result = []
        if bullish:
            result.append(max(bullish, key=lambda x: float(x.confidence)))
        if bearish:
            result.append(max(bearish, key=lambda x: float(x.confidence)))

        return result

    def _check_momentum_divergence(
        self, signals: List[StrategySignal], ml_prediction: Optional[Dict[str, Any]]
    ) -> List[str]:
        conflicts = []
        if not ml_prediction:
            return conflicts

        ml_class = ml_prediction.get("predicted_class")
        ml_confidence = ml_prediction.get("confidence", 0)

        for signal in signals:
            signal_direction = 1 if signal.direction.value == "bullish" else -1
            ml_direction = 1 if ml_class == 1 else (-1 if ml_class == 2 else 0)

            if signal_direction != ml_direction and ml_confidence > 0.6:
                conflicts.append(f"ML disagrees with {signal.strategy_type.value}: ML={ml_class}, Signal={signal_direction}")

        return conflicts

    def _check_regime_alignment(
        self, signals: List[StrategySignal], regime: Dict[str, Any]
    ) -> List[str]:
        conflicts = []
        regime_type = regime.get("regime", "uncertain")
        trend_strength = regime.get("trend_strength", "weak")

        for signal in signals:
            if signal.strategy_type.value == "orb":
                # ORB works best in breakout transition or trending
                if regime_type == "sideways" and trend_strength == "weak":
                    conflicts.append(f"ORB signal in sideways market with weak trend")
            elif signal.strategy_type.value == "vwap_pullback":
                # VWAP pullback needs trending regime
                if regime_type not in ["strong_bullish", "strong_bearish"]:
                    conflicts.append(f"VWAP pullback signal in non-trending regime: {regime_type}")
            elif signal.strategy_type.value == "sr_breakout":
                # S/R breakout works in transition
                if regime_type == "sideways":
                    conflicts.append(f"S/R breakout in sideways market")

        return conflicts

    def _check_indicator_alignment(self, signals: List[StrategySignal]) -> List[str]:
        conflicts = []
        # This would check metadata for indicator states
        # For now, just a placeholder
        return conflicts

    def _rank_signals(
        self,
        signals: List[StrategySignal],
        ml_prediction: Optional[Dict[str, Any]],
        regime: Dict[str, Any],
        soft_conflicts: List[str]
    ) -> List[StrategySignal]:
        """Rank signals by quality."""
        scored = []

        for signal in signals:
            score = float(signal.confidence) * 100

            # Boost for ML agreement
            if ml_prediction:
                ml_class = ml_prediction.get("predicted_class")
                signal_dir = 1 if signal.direction.value == "bullish" else -1
                ml_dir = 1 if ml_class == 1 else (-1 if ml_class == 2 else 0)
                if signal_dir == ml_dir:
                    score += ml_prediction.get("confidence", 0) * 20

            # Boost for regime alignment
            regime_type = regime.get("regime", "uncertain")
            if signal.strategy_type.value == "orb" and regime_type == "breakout_transition":
                score += 15
            elif signal.strategy_type.value == "vwap_pullback" and regime_type in ["strong_bullish", "strong_bearish"]:
                score += 15
            elif signal.strategy_type.value == "sr_breakout" and regime_type == "breakout_transition":
                score += 15

            # Penalty for soft conflicts
            signal_conflicts = [c for c in soft_conflicts if signal.strategy_type.value in c]
            score -= len(signal_conflicts) * 10

            # Boost for higher R:R
            score += float(signal.rr_ratio) * 5

            scored.append((score, signal))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]


# Singleton instance
conflict_resolution_engine = ConflictResolutionEngine()