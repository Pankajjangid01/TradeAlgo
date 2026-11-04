import logging
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd

from app.config.settings import settings

logger = logging.getLogger(__name__)


class LevelType(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"
    PIVOT = "pivot"
    PDH = "pdh"  # Previous Day High
    PDL = "pdl"  # Previous Day Low
    PDC = "pdc"  # Previous Day Close
    OR_HIGH = "or_high"  # Opening Range High
    OR_LOW = "or_low"   # Opening Range Low
    OR_MID = "or_mid"   # Opening Range Mid
    SWING_HIGH = "swing_high"
    SWING_LOW = "swing_low"


class BreakoutStatus(str, Enum):
    NONE = "none"
    BULLISH_BOS = "bullish_bos"      # Break of Structure - bullish
    BEARISH_BOS = "bearish_bos"      # Break of Structure - bearish
    BULLISH_CHOCH = "bullish_choch"  # Change of Character - bullish
    BEARISH_CHOCH = "bearish_choch"  # Change of Character - bearish
    FALSE_BREAKOUT = "false_breakout"
    FALSE_BREAKDOWN = "false_breakdown"


@dataclass
class SupportResistanceLevel:
    price: Decimal
    level_type: LevelType
    strength: int  # Number of touches
    start_time: pd.Timestamp
    end_time: Optional[pd.Timestamp]
    is_active: bool
    source: str
    metadata: Dict[str, Any]


@dataclass
class MarketStructure:
    swing_highs: List[SupportResistanceLevel]
    swing_lows: List[SupportResistanceLevel]
    support_levels: List[SupportResistanceLevel]
    resistance_levels: List[SupportResistanceLevel]
    current_trend: str  # bullish, bearish, sideways
    breakout_status: BreakoutStatus
    last_bos_price: Optional[Decimal]
    last_bos_time: Optional[pd.Timestamp]
    last_choch_price: Optional[Decimal]
    last_choch_time: Optional[pd.Timestamp]


class MarketStructureEngine:
    def __init__(self):
        self.swing_lookback = 5  # Bars to confirm swing
        self.cluster_distance_pct = settings.STRATEGY_CONFIG["sr_breakout"]["cluster_distance_pct"]
        self.min_touches = settings.STRATEGY_CONFIG["sr_breakout"]["min_touches"]

    def analyze(self, df: pd.DataFrame) -> MarketStructure:
        """Analyze market structure from OHLCV data."""
        if df.empty or len(df) < 20:
            return self._empty_structure()

        # Find swing points
        swing_highs = self._find_swing_highs(df)
        swing_lows = self._find_swing_lows(df)

        # Identify support/resistance levels
        support_levels = self._identify_support_levels(df, swing_lows)
        resistance_levels = self._identify_resistance_levels(df, swing_highs)

        # Determine trend
        current_trend = self._determine_trend(df, swing_highs, swing_lows)

        # Check for BOS/CHoCH
        breakout_status, bos_price, bos_time, choch_price, choch_time = self._check_bos_choch(
            df, swing_highs, swing_lows, current_trend
        )

        return MarketStructure(
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            current_trend=current_trend,
            breakout_status=breakout_status,
            last_bos_price=bos_price,
            last_bos_time=bos_time,
            last_choch_price=choch_price,
            last_choch_time=choch_time,
        )

    def _find_swing_highs(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Find swing highs using fractal pattern."""
        highs = df['high'].values
        times = df.index
        swings = []

        for i in range(self.swing_lookback, len(highs) - self.swing_lookback):
            is_swing = True
            for j in range(1, self.swing_lookback + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing = False
                    break
            
            if is_swing:
                swings.append(SupportResistanceLevel(
                    price=Decimal(str(highs[i])),
                    level_type=LevelType.SWING_HIGH,
                    strength=1,
                    start_time=times[i],
                    end_time=None,
                    is_active=True,
                    source="fractal",
                    metadata={"index": i}
                ))

        return swings

    def _find_swing_lows(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Find swing lows using fractal pattern."""
        lows = df['low'].values
        times = df.index
        swings = []

        for i in range(self.swing_lookback, len(lows) - self.swing_lookback):
            is_swing = True
            for j in range(1, self.swing_lookback + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing = False
                    break
            
            if is_swing:
                swings.append(SupportResistanceLevel(
                    price=Decimal(str(lows[i])),
                    level_type=LevelType.SWING_LOW,
                    strength=1,
                    start_time=times[i],
                    end_time=None,
                    is_active=True,
                    source="fractal",
                    metadata={"index": i}
                ))

        return swings

    def _identify_support_levels(
        self, df: pd.DataFrame, swing_lows: List[SupportResistanceLevel]
    ) -> List[SupportResistanceLevel]:
        """Cluster swing lows into support zones."""
        if not swing_lows:
            return []

        levels = []
        prices = [float(sl.price) for sl in swing_lows]
        
        # Add previous day low
        if len(df) > 1:
            pdl = float(df['low'].iloc[-2])
            prices.append(pdl)
            levels.append(SupportResistanceLevel(
                price=Decimal(str(pdl)),
                level_type=LevelType.PDL,
                strength=1,
                start_time=df.index[-2],
                end_time=None,
                is_active=True,
                source="previous_day",
                metadata={}
            ))

        # Add pivots
        pivots = self._calculate_pivots(df)
        if 'S1' in pivots:
            prices.append(float(pivots['S1']))
            levels.append(SupportResistanceLevel(
                price=Decimal(str(pivots['S1'])),
                level_type=LevelType.PIVOT,
                strength=1,
                start_time=df.index[-1],
                end_time=None,
                is_active=True,
                source="pivot",
                metadata={"pivot_type": "S1"}
            ))
        if 'S2' in pivots:
            prices.append(float(pivots['S2']))
            levels.append(SupportResistanceLevel(
                price=Decimal(str(pivots['S2'])),
                level_type=LevelType.PIVOT,
                strength=1,
                start_time=df.index[-1],
                end_time=None,
                is_active=True,
                source="pivot",
                metadata={"pivot_type": "S2"}
            ))

        # Cluster nearby levels
        clustered = self._cluster_levels(prices, LevelType.SUPPORT, "clustered")
        return clustered

    def _identify_resistance_levels(
        self, df: pd.DataFrame, swing_highs: List[SupportResistanceLevel]
    ) -> List[SupportResistanceLevel]:
        """Cluster swing highs into resistance zones."""
        if not swing_highs:
            return []

        levels = []
        prices = [float(sh.price) for sh in swing_highs]
        
        # Add previous day high
        if len(df) > 1:
            pdh = float(df['high'].iloc[-2])
            prices.append(pdh)
            levels.append(SupportResistanceLevel(
                price=Decimal(str(pdh)),
                level_type=LevelType.PDH,
                strength=1,
                start_time=df.index[-2],
                end_time=None,
                is_active=True,
                source="previous_day",
                metadata={}
            ))

        # Add pivots
        pivots = self._calculate_pivots(df)
        if 'R1' in pivots:
            prices.append(float(pivots['R1']))
            levels.append(SupportResistanceLevel(
                price=Decimal(str(pivots['R1'])),
                level_type=LevelType.PIVOT,
                strength=1,
                start_time=df.index[-1],
                end_time=None,
                is_active=True,
                source="pivot",
                metadata={"pivot_type": "R1"}
            ))
        if 'R2' in pivots:
            prices.append(float(pivots['R2']))
            levels.append(SupportResistanceLevel(
                price=Decimal(str(pivots['R2'])),
                level_type=LevelType.PIVOT,
                strength=1,
                start_time=df.index[-1],
                end_time=None,
                is_active=True,
                source="pivot",
                metadata={"pivot_type": "R2"}
            ))

        # Cluster nearby levels
        clustered = self._cluster_levels(prices, LevelType.RESISTANCE, "clustered")
        return clustered

    def _calculate_pivots(self, df: pd.DataFrame) -> Dict[str, Decimal]:
        """Calculate daily pivot points."""
        if len(df) < 2:
            return {}
        
        prev_high = float(df['high'].iloc[-2])
        prev_low = float(df['low'].iloc[-2])
        prev_close = float(df['close'].iloc[-2])
        
        pivot = (prev_high + prev_low + prev_close) / 3
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)
        
        return {
            'P': Decimal(str(round(pivot, 2))),
            'R1': Decimal(str(round(r1, 2))),
            'S1': Decimal(str(round(s1, 2))),
            'R2': Decimal(str(round(r2, 2))),
            'S2': Decimal(str(round(s2, 2))),
        }

    def _cluster_levels(
        self, prices: List[float], level_type: LevelType, source: str
    ) -> List[SupportResistanceLevel]:
        """Cluster nearby price levels into zones."""
        if not prices:
            return []
        
        prices = sorted(set(prices))
        clusters = []
        current_cluster = [prices[0]]
        
        for price in prices[1:]:
            cluster_center = np.mean(current_cluster)
            if abs(price - cluster_center) / cluster_center * 100 <= self.cluster_distance_pct:
                current_cluster.append(price)
            else:
                clusters.append(current_cluster)
                current_cluster = [price]
        clusters.append(current_cluster)
        
        result = []
        for cluster in clusters:
            if len(cluster) >= self.min_touches:
                result.append(SupportResistanceLevel(
                    price=Decimal(str(round(np.mean(cluster), 2))),
                    level_type=level_type,
                    strength=len(cluster),
                    start_time=pd.Timestamp.now(),
                    end_time=None,
                    is_active=True,
                    source=source,
                    metadata={"prices": [round(p, 2) for p in cluster]}
                ))
        
        return result

    def _determine_trend(
        self, df: pd.DataFrame, swing_highs: List, swing_lows: List
    ) -> str:
        """Determine current trend from swing structure."""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "sideways"
        
        # Higher highs and higher lows = bullish
        # Lower highs and lower lows = bearish
        recent_highs = [float(sh.price) for sh in swing_highs[-3:]]
        recent_lows = [float(sl.price) for sl in swing_lows[-3:]]
        
        hh = all(recent_highs[i] > recent_highs[i-1] for i in range(1, len(recent_highs)))
        hl = all(recent_lows[i] > recent_lows[i-1] for i in range(1, len(recent_lows)))
        lh = all(recent_highs[i] < recent_highs[i-1] for i in range(1, len(recent_highs)))
        ll = all(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows)))
        
        if hh and hl:
            return "bullish"
        elif lh and ll:
            return "bearish"
        return "sideways"

    def _check_bos_choch(
        self, df: pd.DataFrame, swing_highs: List, swing_lows: List, trend: str
    ) -> Tuple[BreakoutStatus, Optional[Decimal], Optional[pd.Timestamp], Optional[Decimal], Optional[pd.Timestamp]]:
        """Check for Break of Structure and Change of Character."""
        if df.empty or len(df) < 2:
            return BreakoutStatus.NONE, None, None, None, None
        
        current_close = float(df['close'].iloc[-1])
        current_time = df.index[-1]
        
        # Check bullish BOS (close above recent swing high)
        if swing_highs:
            last_swing_high = float(swing_highs[-1].price)
            if current_close > last_swing_high:
                if trend == "bullish":
                    return BreakoutStatus.BULLISH_BOS, Decimal(str(last_swing_high)), current_time, None, None
                else:
                    return BreakoutStatus.BULLISH_CHOCH, Decimal(str(last_swing_high)), current_time, None, None
        
        # Check bearish BOS (close below recent swing low)
        if swing_lows:
            last_swing_low = float(swing_lows[-1].price)
            if current_close < last_swing_low:
                if trend == "bearish":
                    return BreakoutStatus.BEARISH_BOS, Decimal(str(last_swing_low)), current_time, None, None
                else:
                    return BreakoutStatus.BEARISH_CHOCH, Decimal(str(last_swing_low)), current_time, None, None
        
        return BreakoutStatus.NONE, None, None, None, None

    def _empty_structure(self) -> MarketStructure:
        return MarketStructure(
            swing_highs=[],
            swing_lows=[],
            support_levels=[],
            resistance_levels=[],
            current_trend="sideways",
            breakout_status=BreakoutStatus.NONE,
            last_bos_price=None,
            last_bos_time=None,
            last_choch_price=None,
            last_choch_time=None,
        )

    def get_nearest_support(self, structure: MarketStructure, price: Decimal) -> Optional[SupportResistanceLevel]:
        """Find nearest support below price."""
        supports = [s for s in structure.support_levels if float(s.price) < float(price)]
        if not supports:
            return None
        return max(supports, key=lambda x: float(x.price))

    def get_nearest_resistance(self, structure: MarketStructure, price: Decimal) -> Optional[SupportResistanceLevel]:
        """Find nearest resistance above price."""
        resistances = [r for r in structure.resistance_levels if float(r.price) > float(price)]
        if not resistances:
            return None
        return min(resistances, key=lambda x: float(x.price))

    def calculate_sr_distance(self, structure: MarketStructure, price: Decimal) -> Dict[str, Decimal]:
        """Calculate distance to nearest support and resistance."""
        support = self.get_nearest_support(structure, price)
        resistance = self.get_nearest_resistance(structure, price)
        
        return {
            "support_distance_pct": Decimal(str(round((float(price) - float(support.price)) / float(price) * 100, 2))) if support else Decimal("0"),
            "resistance_distance_pct": Decimal(str(round((float(resistance.price) - float(price)) / float(price) * 100, 2))) if resistance else Decimal("0"),
            "support_price": support.price if support else Decimal("0"),
            "resistance_price": resistance.price if resistance else Decimal("0"),
        }


# Singleton instance
market_structure_engine = MarketStructureEngine()