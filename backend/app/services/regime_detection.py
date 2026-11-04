import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    STRONG_BULLISH = "strong_bullish"
    STRONG_BEARISH = "strong_bearish"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT_TRANSITION = "breakout_transition"
    UNCERTAIN = "uncertain"


@dataclass
class RegimeAnalysis:
    regime: MarketRegime
    confidence: Decimal
    adx: Decimal
    ema_9_20_state: str  # bullish, bearish, neutral
    ema_20_50_state: str
    vwap_state: str  # above, below, at
    atr_pct: Decimal
    relative_volume: Decimal
    trend_strength: str  # strong, moderate, weak
    volatility_state: str  # high, normal, low
    details: Dict[str, Any]


class RegimeDetectionEngine:
    def __init__(self):
        self.adx_trend_threshold = settings.REGIME_CONFIG["adx_trend_threshold"]
        self.adx_strong_threshold = settings.REGIME_CONFIG["adx_strong_threshold"]
        self.atr_high_vol_multiplier = settings.REGIME_CONFIG["atr_high_volatility_multiplier"]
        self.atr_low_vol_multiplier = settings.REGIME_CONFIG["atr_low_volatility_multiplier"]
        self.ema_lookback = settings.REGIME_CONFIG["ema_trend_lookback"]
        self.hysteresis_bars = settings.REGIME_CONFIG["hysteresis_bars"]
        
        # State for hysteresis
        self._previous_regime: Optional[MarketRegime] = None
        self._regime_count = 0

    def detect(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> RegimeAnalysis:
        """Detect market regime from indicators."""
        if df.empty or len(df) < 20:
            return self._default_analysis()

        # Extract indicator values
        adx = float(indicators.get('adx', 0))
        ema_9 = float(indicators.get('ema_9', 0))
        ema_20 = float(indicators.get('ema_20', 0))
        ema_50 = float(indicators.get('ema_50', 0))
        vwap = float(indicators.get('vwap', 0))
        close = float(df['close'].iloc[-1])
        atr_pct = float(indicators.get('atr_pct', 0))
        relative_volume = float(indicators.get('relative_volume', 1))
        plus_di = float(indicators.get('plus_di', 0))
        minus_di = float(indicators.get('minus_di', 0))

        # EMA states
        ema_9_20_state = self._get_ema_state(ema_9, ema_20)
        ema_20_50_state = self._get_ema_state(ema_20, ema_50)

        # VWAP state
        vwap_state = "above" if close > vwap else ("below" if close < vwap else "at")

        # Volatility state
        volatility_state = self._get_volatility_state(atr_pct)

        # Trend strength
        trend_strength = self._get_trend_strength(adx)

        # Determine regime
        regime = self._determine_regime(
            adx, ema_9_20_state, ema_20_50_state, vwap_state,
            plus_di, minus_di, trend_strength, volatility_state, relative_volume
        )

        # Apply hysteresis
        regime = self._apply_hysteresis(regime)

        # Calculate confidence
        confidence = self._calculate_confidence(
            adx, ema_9_20_state, ema_20_50_state, vwap_state,
            plus_di, minus_di, relative_volume
        )

        return RegimeAnalysis(
            regime=regime,
            confidence=Decimal(str(round(confidence, 3))),
            adx=Decimal(str(round(adx, 2))),
            ema_9_20_state=ema_9_20_state,
            ema_20_50_state=ema_20_50_state,
            vwap_state=vwap_state,
            atr_pct=Decimal(str(round(atr_pct, 4))),
            relative_volume=Decimal(str(round(relative_volume, 2))),
            trend_strength=trend_strength,
            volatility_state=volatility_state,
            details={
                "plus_di": round(plus_di, 2),
                "minus_di": round(minus_di, 2),
                "close_vs_vwap_pct": round((close - vwap) / vwap * 100, 2) if vwap > 0 else 0,
            }
        )

    def _get_ema_state(self, ema_fast: float, ema_slow: float) -> str:
        if ema_fast > ema_slow * 1.001:
            return "bullish"
        elif ema_fast < ema_slow * 0.999:
            return "bearish"
        return "neutral"

    def _get_volatility_state(self, atr_pct: float) -> str:
        # This would ideally use historical ATR percentile
        # For now, use simple thresholds
        if atr_pct > 1.5:
            return "high"
        elif atr_pct < 0.5:
            return "low"
        return "normal"

    def _get_trend_strength(self, adx: float) -> str:
        if adx >= self.adx_strong_threshold:
            return "strong"
        elif adx >= self.adx_trend_threshold:
            return "moderate"
        return "weak"

    def _determine_regime(
        self,
        adx: float,
        ema_9_20: str,
        ema_20_50: str,
        vwap_state: str,
        plus_di: float,
        minus_di: float,
        trend_strength: str,
        volatility_state: str,
        relative_volume: float
    ) -> MarketRegime:
        # Strong bullish trend
        if (trend_strength in ["strong", "moderate"] and 
            ema_9_20 == "bullish" and 
            ema_20_50 == "bullish" and
            vwap_state == "above" and
            plus_di > minus_di):
            return MarketRegime.STRONG_BULLISH

        # Strong bearish trend
        if (trend_strength in ["strong", "moderate"] and
            ema_9_20 == "bearish" and
            ema_20_50 == "bearish" and
            vwap_state == "below" and
            minus_di > plus_di):
            return MarketRegime.STRONG_BEARISH

        # High volatility
        if volatility_state == "high" and relative_volume > 1.5:
            return MarketRegime.HIGH_VOLATILITY

        # Low volatility
        if volatility_state == "low" and trend_strength == "weak":
            return MarketRegime.LOW_VOLATILITY

        # Breakout transition
        if trend_strength == "weak" and relative_volume > 2.0:
            return MarketRegime.BREAKOUT_TRANSITION

        # Sideways
        if trend_strength == "weak" and volatility_state == "normal":
            return MarketRegime.SIDEWAYS

        return MarketRegime.UNCERTAIN

    def _apply_hysteresis(self, regime: MarketRegime) -> MarketRegime:
        """Apply hysteresis to prevent regime flipping."""
        if self._previous_regime == regime:
            self._regime_count += 1
        else:
            self._regime_count = 1
            self._previous_regime = regime
        
        # Require N consecutive bars before confirming regime change
        if self._regime_count < self.hysteresis_bars and self._previous_regime != regime:
            return self._previous_regime or regime
        
        return regime

    def _calculate_confidence(
        self,
        adx: float,
        ema_9_20: str,
        ema_20_50: str,
        vwap_state: str,
        plus_di: float,
        minus_di: float,
        relative_volume: float
    ) -> float:
        """Calculate confidence score for regime detection."""
        score = 0.0
        
        # ADX contribution (0-30)
        if adx >= self.adx_strong_threshold:
            score += 30
        elif adx >= self.adx_trend_threshold:
            score += 20
        elif adx > 15:
            score += 10
        
        # EMA alignment (0-25)
        if ema_9_20 == ema_20_50 and ema_9_20 != "neutral":
            score += 25
        elif ema_9_20 != "neutral" or ema_20_50 != "neutral":
            score += 15
        
        # VWAP alignment (0-15)
        if (ema_9_20 == "bullish" and vwap_state == "above") or \
           (ema_9_20 == "bearish" and vwap_state == "below"):
            score += 15
        elif vwap_state != "at":
            score += 10
        
        # DI alignment (0-15)
        if ema_9_20 == "bullish" and plus_di > minus_di:
            score += 15
        elif ema_9_20 == "bearish" and minus_di > plus_di:
            score += 15
        elif abs(plus_di - minus_di) < 5:
            score += 5
        
        # Volume confirmation (0-15)
        if relative_volume > 1.5:
            score += 15
        elif relative_volume > 1.0:
            score += 10
        else:
            score += 5
        
        return min(score / 100, 1.0)

    def _default_analysis(self) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=MarketRegime.UNCERTAIN,
            confidence=Decimal("0"),
            adx=Decimal("0"),
            ema_9_20_state="neutral",
            ema_20_50_state="neutral",
            vwap_state="at",
            atr_pct=Decimal("0"),
            relative_volume=Decimal("1"),
            trend_strength="weak",
            volatility_state="normal",
            details={}
        )


# Singleton instance
regime_detection_engine = RegimeDetectionEngine()