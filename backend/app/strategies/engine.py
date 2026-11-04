import logging
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

from app.config.settings import settings
from app.services.indicator_engine import IndicatorValues
from app.services.market_structure import MarketStructure, SupportResistanceLevel, LevelType, BreakoutStatus
from app.services.regime_detection import MarketRegime, RegimeAnalysis

logger = logging.getLogger(__name__)


class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class StrategyType(str, Enum):
    ORB = "orb"
    VWAP_PULLBACK = "vwap_pullback"
    SR_BREAKOUT = "sr_breakout"


@dataclass
class StrategySignal:
    strategy_type: StrategyType
    direction: SignalDirection
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    risk_per_share: Decimal
    reward_per_share: Decimal
    rr_ratio: Decimal
    confidence: Decimal
    metadata: Dict[str, Any]


class StrategyEngine:
    def __init__(self):
        self.orb_config = settings.STRATEGY_CONFIG["orb"]
        self.vwap_config = settings.STRATEGY_CONFIG["vwap_pullback"]
        self.sr_config = settings.STRATEGY_CONFIG["sr_breakout"]

    def evaluate_all(
        self,
        df: pd.DataFrame,
        indicators: IndicatorValues,
        structure: MarketStructure,
        regime: RegimeAnalysis,
        current_price: Decimal,
        current_time: pd.Timestamp
    ) -> List[StrategySignal]:
        """Evaluate all enabled strategies and return valid signals."""
        signals = []

        # Check regime compatibility first
        if not self._is_regime_favorable(regime):
            logger.info(f"Regime {regime.regime} not favorable for new entries")
            return signals

        # Strategy A: Opening Range Breakout
        if self.orb_config["enabled"]:
            orb_signal = self._evaluate_orb(df, indicators, structure, regime, current_price, current_time)
            if orb_signal:
                signals.append(orb_signal)

        # Strategy B: VWAP Trend Pullback
        if self.vwap_config["enabled"]:
            vwap_signal = self._evaluate_vwap_pullback(df, indicators, structure, regime, current_price, current_time)
            if vwap_signal:
                signals.append(vwap_signal)

        # Strategy C: Support/Resistance Breakout & Retest
        if self.sr_config["enabled"]:
            sr_signal = self._evaluate_sr_breakout(df, indicators, structure, regime, current_price, current_time)
            if sr_signal:
                signals.append(sr_signal)

        return signals

    def _is_regime_favorable(self, regime: RegimeAnalysis) -> bool:
        """Check if current regime allows trading."""
        unfavorable_regimes = [
            MarketRegime.SIDEWAYS,
            MarketRegime.UNCERTAIN,
        ]
        return regime.regime not in unfavorable_regimes

    # ==================== ORB Strategy ====================
    def _evaluate_orb(
        self,
        df: pd.DataFrame,
        indicators: IndicatorValues,
        structure: MarketStructure,
        regime: RegimeAnalysis,
        current_price: Decimal,
        current_time: pd.Timestamp
    ) -> Optional[StrategySignal]:
        """Evaluate Opening Range Breakout strategy."""
        # Check if we're in ORB window
        if not self._is_orb_window(current_time):
            return None

        # Get opening range levels
        or_high, or_low, or_mid = self._get_opening_range(df)
        if not or_high or not or_low:
            return None

        # Check for breakout
        breakout_direction = None
        if current_price > or_high:
            breakout_direction = SignalDirection.BULLISH
        elif current_price < or_low:
            breakout_direction = SignalDirection.BEARISH
        else:
            return None

        # Validate with volume
        if not self._validate_volume(df, indicators):
            return None

        # Validate trend confirmation
        if not self._validate_trend_confirmation(indicators, breakout_direction):
            return None

        # Validate momentum
        if not self._validate_momentum(indicators, breakout_direction):
            return None

        # Check resistance/support proximity
        if not self._check_sr_proximity(structure, current_price, breakout_direction):
            return None

        # Calculate stops and targets
        stop_price, target_price = self._calculate_orb_stops_targets(
            current_price, or_high, or_low, or_mid, breakout_direction
        )

        risk = abs(current_price - stop_price)
        reward = abs(target_price - current_price)
        
        if risk <= 0:
            return None

        rr_ratio = reward / risk
        if rr_ratio < 1.5:  # Minimum R:R
            return None

        return StrategySignal(
            strategy_type=StrategyType.ORB,
            direction=breakout_direction,
            entry_price=current_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_per_share=risk,
            reward_per_share=reward,
            rr_ratio=Decimal(str(round(float(rr_ratio), 2))),
            confidence=Decimal("0.75"),
            metadata={
                "or_high": str(or_high),
                "or_low": str(or_low),
                "or_mid": str(or_mid),
                "breakout_pct": str(round(abs(float(current_price) - float(or_high if breakout_direction == SignalDirection.BULLISH else or_low)) / float(or_high if breakout_direction == SignalDirection.BULLISH else or_low) * 100, 2)),
            }
        )

    def _is_orb_window(self, current_time: pd.Timestamp) -> bool:
        """Check if current time is within ORB evaluation window."""
        # ORB window: 9:30 - 10:30 (configurable)
        hour = current_time.hour
        minute = current_time.minute
        return (hour == 9 and minute >= 30) or (hour == 10)

    def _get_opening_range(self, df: pd.DataFrame) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Calculate opening range high, low, mid from first 15 minutes."""
        or_minutes = self.orb_config["opening_range_minutes"]
        range_bars = or_minutes // 5  # Assuming 5-min bars
        
        if len(df) < range_bars:
            return None, None, None
        
        # Get first N bars of the day
        day_start = df.index[0].normalize()
        morning_bars = df[(df.index >= day_start) & (df.index < day_start + pd.Timedelta(minutes=or_minutes))]
        
        if len(morning_bars) < range_bars // 2:  # At least half the bars
            return None, None, None
        
        or_high = Decimal(str(round(morning_bars['high'].max(), 2)))
        or_low = Decimal(str(round(morning_bars['low'].min(), 2)))
        or_mid = Decimal(str(round((float(or_high) + float(or_low)) / 2, 2)))
        
        return or_high, or_low, or_mid

    def _validate_volume(self, df: pd.DataFrame, indicators: IndicatorValues) -> bool:
        """Validate relative volume for breakout."""
        min_rvol = self.orb_config["min_relative_volume"]
        rvol = float(indicators.relative_volume) if indicators.relative_volume else 0
        return rvol >= min_rvol

    def _validate_trend_confirmation(self, indicators: IndicatorValues, direction: SignalDirection) -> bool:
        """Validate EMA and VWAP trend confirmation."""
        if not self.orb_config["require_ema_confirmation"] and not self.orb_config["require_vwap_confirmation"]:
            return True

        ema_9 = float(indicators.ema_9) if indicators.ema_9 else 0
        ema_20 = float(indicators.ema_20) if indicators.ema_20 else 0
        ema_50 = float(indicators.ema_50) if indicators.ema_50 else 0
        vwap = float(indicators.vwap) if indicators.vwap else 0
        close = float(indicators.ema_9) if indicators.ema_9 else 0  # Approximate

        if direction == SignalDirection.BULLISH:
            checks = []
            if self.orb_config["require_ema_confirmation"]:
                checks.append(ema_9 > ema_20)
                checks.append(ema_20 >= ema_50 * 0.999)  # Allow slight deviation
            if self.orb_config["require_vwap_confirmation"]:
                checks.append(close > vwap)
            return all(checks) if checks else True
        else:
            checks = []
            if self.orb_config["require_ema_confirmation"]:
                checks.append(ema_9 < ema_20)
                checks.append(ema_20 <= ema_50 * 1.001)
            if self.orb_config["require_vwap_confirmation"]:
                checks.append(close < vwap)
            return all(checks) if checks else True

    def _validate_momentum(self, indicators: IndicatorValues, direction: SignalDirection) -> bool:
        """Validate RSI and MACD momentum."""
        rsi = float(indicators.rsi) if indicators.rsi else 50
        macd_hist = float(indicators.macd_histogram) if indicators.macd_histogram else 0

        if direction == SignalDirection.BULLISH:
            checks = []
            if self.orb_config["require_rsi_confirmation"]:
                checks.append(rsi > 50)  # Not oversold, showing momentum
            if self.orb_config["require_macd_confirmation"]:
                checks.append(macd_hist > 0)
            return all(checks) if checks else True
        else:
            checks = []
            if self.orb_config["require_rsi_confirmation"]:
                checks.append(rsi < 50)
            if self.orb_config["require_macd_confirmation"]:
                checks.append(macd_hist < 0)
            return all(checks) if checks else True

    def _check_sr_proximity(self, structure: MarketStructure, price: Decimal, direction: SignalDirection) -> bool:
        """Check if there's nearby S/R that would ruin R:R."""
        if direction == SignalDirection.BULLISH:
            resistance = min(
                [float(r.price) for r in structure.resistance_levels if float(r.price) > float(price)],
                default=float('inf')
            )
            if resistance != float('inf'):
                distance_pct = (resistance - float(price)) / float(price) * 100
                return distance_pct > 1.0  # At least 1% to resistance
        else:
            support = max(
                [float(s.price) for s in structure.support_levels if float(s.price) < float(price)],
                default=0
            )
            if support > 0:
                distance_pct = (float(price) - support) / float(price) * 100
                return distance_pct > 1.0
        return True

    def _calculate_orb_stops_targets(
        self, entry: Decimal, or_high: Decimal, or_low: Decimal, or_mid: Decimal, direction: SignalDirection
    ) -> Tuple[Decimal, Decimal]:
        """Calculate stop loss and target for ORB."""
        entry_f = float(entry)
        or_high_f = float(or_high)
        or_low_f = float(or_low)
        or_mid_f = float(or_mid)

        if direction == SignalDirection.BULLISH:
            # Stop at OR mid
            stop = or_mid
            risk = entry_f - float(stop)
            target = entry_f + (risk * 2.0)  # 2R target
        else:
            # Stop at OR mid
            stop = or_mid
            risk = float(stop) - entry_f
            target = entry_f - (risk * 2.0)

        return Decimal(str(round(float(stop), 2))), Decimal(str(round(target, 2)))

    # ==================== VWAP Pullback Strategy ====================
    def _evaluate_vwap_pullback(
        self,
        df: pd.DataFrame,
        indicators: IndicatorValues,
        structure: MarketStructure,
        regime: RegimeAnalysis,
        current_price: Decimal,
        current_time: pd.Timestamp
    ) -> Optional[StrategySignal]:
        """Evaluate VWAP Trend Pullback strategy."""
        # Must be in trending regime
        if regime.regime not in [MarketRegime.STRONG_BULLISH, MarketRegime.STRONG_BEARISH]:
            return None

        # Check VWAP alignment
        vwap = float(indicators.vwap) if indicators.vwap else 0
        close = float(current_price)
        
        if regime.regime == MarketRegime.STRONG_BULLISH:
            if close < vwap:
                return None  # Price must be above VWAP in bullish regime
            direction = SignalDirection.BULLISH
            # Check pullback to EMA 20 or support
            ema_20 = float(indicators.ema_20) if indicators.ema_20 else 0
            support = self._find_pullback_support(structure, current_price)
            
            pullback_level = ema_20 if ema_20 > 0 else (float(support.price) if support else 0)
            if pullback_level <= 0:
                return None
            
            # Price should be near pullback level
            distance_pct = abs(close - pullback_level) / close * 100
            if distance_pct > self.vwap_config["pullback_tolerance_pct"]:
                return None
            
            # Check for rejection/bounce
            if not self._check_rejection_candle(df, direction):
                return None
            
            # RSI recovery
            rsi = float(indicators.rsi) if indicators.rsi else 50
            if rsi < self.vwap_config["min_rsi_recovery"]:
                return None
            
        else:  # STRONG_BEARISH
            if close > vwap:
                return None
            direction = SignalDirection.BEARISH
            ema_20 = float(indicators.ema_20) if indicators.ema_20 else 0
            resistance = self._find_pullback_resistance(structure, current_price)
            
            pullback_level = ema_20 if ema_20 > 0 else (float(resistance.price) if resistance else 0)
            if pullback_level <= 0:
                return None
            
            distance_pct = abs(close - pullback_level) / close * 100
            if distance_pct > self.vwap_config["pullback_tolerance_pct"]:
                return None
            
            if not self._check_rejection_candle(df, direction):
                return None
            
            rsi = float(indicators.rsi) if indicators.rsi else 50
            if rsi > 100 - self.vwap_config["min_rsi_recovery"]:
                return None

        # Volume confirmation
        if self.vwap_config["require_volume_confirmation"]:
            rvol = float(indicators.relative_volume) if indicators.relative_volume else 0
            if rvol < 1.0:
                return None

        # Calculate stops and targets (ATR-based)
        atr = float(indicators.atr) if indicators.atr else 0
        if atr <= 0:
            return None

        stop_price, target_price = self._calculate_vwap_stops_targets(current_price, atr, direction)
        risk = abs(float(current_price) - float(stop_price))
        reward = abs(float(target_price) - float(current_price))

        if risk <= 0:
            return None

        rr_ratio = reward / risk
        if rr_ratio < 1.5:
            return None

        return StrategySignal(
            strategy_type=StrategyType.VWAP_PULLBACK,
            direction=direction,
            entry_price=current_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_per_share=Decimal(str(round(risk, 2))),
            reward_per_share=Decimal(str(round(reward, 2))),
            rr_ratio=Decimal(str(round(rr_ratio, 2))),
            confidence=Decimal("0.70"),
            metadata={
                "vwap": str(indicators.vwap),
                "pullback_level": str(pullback_level),
                "rsi": str(indicators.rsi),
            }
        )

    def _find_pullback_support(self, structure: MarketStructure, price: Decimal) -> Optional[SupportResistanceLevel]:
        supports = [s for s in structure.support_levels if float(s.price) < float(price)]
        if not supports:
            return None
        return max(supports, key=lambda x: float(x.price))

    def _find_pullback_resistance(self, structure: MarketStructure, price: Decimal) -> Optional[SupportResistanceLevel]:
        resistances = [r for r in structure.resistance_levels if float(r.price) > float(price)]
        if not resistances:
            return None
        return min(resistances, key=lambda x: float(x.price))

    def _check_rejection_candle(self, df: pd.DataFrame, direction: SignalDirection) -> bool:
        """Check for bullish/bearish rejection candle."""
        if len(df) < 2:
            return False
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        body_size = abs(last['close'] - last['open'])
        total_range = last['high'] - last['low']
        
        if total_range == 0:
            return False
        
        lower_wick = min(last['open'], last['close']) - last['low']
        upper_wick = last['high'] - max(last['open'], last['close'])
        
        if direction == SignalDirection.BULLISH:
            # Bullish rejection: long lower wick, small body, close near high
            return (lower_wick > body_size * 2 and 
                    upper_wick < body_size and
                    last['close'] > last['open'])
        else:
            # Bearish rejection: long upper wick, small body, close near low
            return (upper_wick > body_size * 2 and
                    lower_wick < body_size and
                    last['close'] < last['open'])

    def _calculate_vwap_stops_targets(
        self, entry: Decimal, atr: float, direction: SignalDirection
    ) -> Tuple[Decimal, Decimal]:
        """Calculate ATR-based stops and targets for VWAP pullback."""
        entry_f = float(entry)
        multiplier = 1.5  # ATR multiplier for stop
        
        if direction == SignalDirection.BULLISH:
            stop = entry_f - (atr * multiplier)
            risk = entry_f - stop
            target = entry_f + (risk * 2.0)
        else:
            stop = entry_f + (atr * multiplier)
            risk = stop - entry_f
            target = entry_f - (risk * 2.0)
        
        return Decimal(str(round(stop, 2))), Decimal(str(round(target, 2)))

    # ==================== S/R Breakout Strategy ====================
    def _evaluate_sr_breakout(
        self,
        df: pd.DataFrame,
        indicators: IndicatorValues,
        structure: MarketStructure,
        regime: RegimeAnalysis,
        current_price: Decimal,
        current_time: pd.Timestamp
    ) -> Optional[StrategySignal]:
        """Evaluate Support/Resistance Breakout and Retest strategy."""
        # Check for breakout with retest
        breakout = structure.breakout_status
        
        if breakout == BreakoutStatus.BULLISH_BOS:
            direction = SignalDirection.BULLISH
            # Verify retest
            if self.sr_config["require_retest"]:
                if not self._verify_retest(df, structure, direction):
                    return None
            
            # Volume expansion on breakout
            if self.sr_config["require_volume_expansion"]:
                if not self._check_volume_expansion(df, indicators):
                    return None
            
            # Trend alignment
            if not self._check_trend_alignment(indicators, direction):
                return None
            
            # Calculate stops and targets
            stop_price = self._get_structure_stop(structure, direction, current_price)
            if not stop_price:
                return None
            
            target_price = self._get_structure_target(structure, direction, current_price, stop_price)
            
        elif breakout == BreakoutStatus.BEARISH_BOS:
            direction = SignalDirection.BEARISH
            if self.sr_config["require_retest"]:
                if not self._verify_retest(df, structure, direction):
                    return None
            
            if self.sr_config["require_volume_expansion"]:
                if not self._check_volume_expansion(df, indicators):
                    return None
            
            if not self._check_trend_alignment(indicators, direction):
                return None
            
            stop_price = self._get_structure_stop(structure, direction, current_price)
            if not stop_price:
                return None
            
            target_price = self._get_structure_target(structure, direction, current_price, stop_price)
            
        else:
            return None

        risk = abs(float(current_price) - float(stop_price))
        reward = abs(float(target_price) - float(current_price))
        
        if risk <= 0:
            return None

        rr_ratio = reward / risk
        if rr_ratio < 1.5:
            return None

        return StrategySignal(
            strategy_type=StrategyType.SR_BREAKOUT,
            direction=direction,
            entry_price=current_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_per_share=Decimal(str(round(risk, 2))),
            reward_per_share=Decimal(str(round(reward, 2))),
            rr_ratio=Decimal(str(round(rr_ratio, 2))),
            confidence=Decimal("0.75"),
            metadata={
                "breakout_type": breakout.value,
                "breakout_level": str(structure.last_bos_price),
            }
        )

    def _verify_retest(self, df: pd.DataFrame, structure: MarketStructure, direction: SignalDirection) -> bool:
        """Verify retest of broken level."""
        if len(df) < 3:
            return False
        
        tolerance = self.sr_config["retest_tolerance_pct"] / 100
        breakout_level = float(structure.last_bos_price) if structure.last_bos_price else 0
        
        if breakout_level == 0:
            return False
        
        # Check recent candles for retest
        for i in range(-3, 0):
            candle = df.iloc[i]
            if direction == SignalDirection.BULLISH:
                # Retest: price comes back to broken resistance (now support)
                low = float(candle['low'])
                if abs(low - breakout_level) / breakout_level <= tolerance:
                    return True
            else:
                # Retest: price comes back to broken support (now resistance)
                high = float(candle['high'])
                if abs(high - breakout_level) / breakout_level <= tolerance:
                    return True
        
        return False

    def _check_volume_expansion(self, df: pd.DataFrame, indicators: IndicatorValues) -> bool:
        """Check for volume expansion on breakout."""
        rvol = float(indicators.relative_volume) if indicators.relative_volume else 0
        return rvol >= 1.5

    def _check_trend_alignment(self, indicators: IndicatorValues, direction: SignalDirection) -> bool:
        """Check EMA/VWAP trend alignment."""
        ema_9 = float(indicators.ema_9) if indicators.ema_9 else 0
        ema_20 = float(indicators.ema_20) if indicators.ema_20 else 0
        vwap = float(indicators.vwap) if indicators.vwap else 0
        
        if direction == SignalDirection.BULLISH:
            return ema_9 >= ema_20 and ema_9 > vwap
        else:
            return ema_9 <= ema_20 and ema_9 < vwap

    def _get_structure_stop(
        self, structure: MarketStructure, direction: SignalDirection, entry: Decimal
    ) -> Optional[Decimal]:
        """Get structure-based stop loss."""
        if direction == SignalDirection.BULLISH:
            # Stop below the retest low or broken level
            supports = [s for s in structure.support_levels if float(s.price) < float(entry)]
            if supports:
                return max(supports, key=lambda x: float(x.price)).price
            return Decimal(str(round(float(entry) * 0.99, 2)))  # 1% fallback
        else:
            resistances = [r for r in structure.resistance_levels if float(r.price) > float(entry)]
            if resistances:
                return min(resistances, key=lambda x: float(x.price)).price
            return Decimal(str(round(float(entry) * 1.01, 2)))

    def _get_structure_target(
        self, structure: MarketStructure, direction: SignalDirection, entry: Decimal, stop: Decimal
    ) -> Decimal:
        """Get structure-based target (next S/R level or 2R)."""
        risk = abs(float(entry) - float(stop))
        
        if direction == SignalDirection.BULLISH:
            # Target at next resistance or 2R
            resistances = [r for r in structure.resistance_levels if float(r.price) > float(entry)]
            if resistances:
                next_resistance = min(resistances, key=lambda x: float(x.price)).price
                target_2r = float(entry) + (risk * 2)
                return min(next_resistance, Decimal(str(round(target_2r, 2))))
            return Decimal(str(round(float(entry) + risk * 2, 2)))
        else:
            supports = [s for s in structure.support_levels if float(s.price) < float(entry)]
            if supports:
                next_support = max(supports, key=lambda x: float(x.price)).price
                target_2r = float(entry) - (risk * 2)
                return max(next_support, Decimal(str(round(target_2r, 2))))
            return Decimal(str(round(float(entry) - risk * 2, 2)))


# Singleton instance
strategy_engine = StrategyEngine()