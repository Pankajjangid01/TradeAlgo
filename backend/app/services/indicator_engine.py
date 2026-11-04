import logging
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
import numpy as np
import pandas as pd
from collections import deque

from app.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class IndicatorValues:
    ema_9: Optional[Decimal] = None
    ema_20: Optional[Decimal] = None
    ema_50: Optional[Decimal] = None
    vwap: Optional[Decimal] = None
    rsi: Optional[Decimal] = None
    macd: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    macd_histogram: Optional[Decimal] = None
    adx: Optional[Decimal] = None
    plus_di: Optional[Decimal] = None
    minus_di: Optional[Decimal] = None
    atr: Optional[Decimal] = None
    atr_pct: Optional[Decimal] = None
    relative_volume: Optional[Decimal] = None
    bb_upper: Optional[Decimal] = None
    bb_middle: Optional[Decimal] = None
    bb_lower: Optional[Decimal] = None


class IndicatorEngine:
    def __init__(self):
        self.ema_periods = settings.INDICATOR_CONFIG["ema_periods"]
        self.rsi_period = settings.INDICATOR_CONFIG["rsi_period"]
        self.macd_fast = settings.INDICATOR_CONFIG["macd_fast"]
        self.macd_slow = settings.INDICATOR_CONFIG["macd_slow"]
        self.macd_signal = settings.INDICATOR_CONFIG["macd_signal"]
        self.adx_period = settings.INDICATOR_CONFIG["adx_period"]
        self.atr_period = settings.INDICATOR_CONFIG["atr_period"]
        self.bb_period = settings.INDICATOR_CONFIG["bollinger_period"]
        self.bb_std = settings.INDICATOR_CONFIG["bollinger_std"]
        self.rvol_period = settings.INDICATOR_CONFIG["relative_volume_period"]

        # State for incremental calculation
        self._ema_state: Dict[str, Dict[int, Decimal]] = {}
        self._rsi_state: Dict[str, deque] = {}
        self._macd_state: Dict[str, Dict[str, Decimal]] = {}
        self._adx_state: Dict[str, Dict[str, Any]] = {}
        self._atr_state: Dict[str, deque] = {}
        self._vwap_state: Dict[str, Dict[str, Decimal]] = {}
        self._volume_state: Dict[str, deque] = {}
        self._bb_state: Dict[str, deque] = {}

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators for a DataFrame with OHLCV data."""
        if df.empty or len(df) < max(self.ema_periods):
            return df

        result = df.copy()

        # EMA
        for period in self.ema_periods:
            result[f'ema_{period}'] = self._calculate_ema(result['close'], period)

        # VWAP (session-based)
        result['vwap'] = self._calculate_vwap(result)

        # RSI
        result['rsi'] = self._calculate_rsi(result['close'], self.rsi_period)

        # MACD
        macd, signal, histogram = self._calculate_macd(
            result['close'], self.macd_fast, self.macd_slow, self.macd_signal
        )
        result['macd'] = macd
        result['macd_signal'] = signal
        result['macd_histogram'] = histogram

        # ADX/DI
        adx, plus_di, minus_di = self._calculate_adx(
            result['high'], result['low'], result['close'], self.adx_period
        )
        result['adx'] = adx
        result['plus_di'] = plus_di
        result['minus_di'] = minus_di

        # ATR
        result['atr'] = self._calculate_atr(result['high'], result['low'], result['close'], self.atr_period)
        result['atr_pct'] = (result['atr'] / result['close'] * 100).round(4)

        # Relative Volume
        result['relative_volume'] = self._calculate_relative_volume(result['volume'], self.rvol_period)

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(result['close'], self.bb_period, self.bb_std)
        result['bb_upper'] = bb_upper
        result['bb_middle'] = bb_middle
        result['bb_lower'] = bb_lower

        return result

    def calculate_latest(self, df: pd.DataFrame) -> IndicatorValues:
        """Calculate indicators for the latest candle only (incremental)."""
        if df.empty or len(df) < max(self.ema_periods):
            return IndicatorValues()

        # Calculate all and return last row
        result = self.calculate_all(df)
        last = result.iloc[-1]

        return IndicatorValues(
            ema_9=self._to_decimal(last.get('ema_9')),
            ema_20=self._to_decimal(last.get('ema_20')),
            ema_50=self._to_decimal(last.get('ema_50')),
            vwap=self._to_decimal(last.get('vwap')),
            rsi=self._to_decimal(last.get('rsi')),
            macd=self._to_decimal(last.get('macd')),
            macd_signal=self._to_decimal(last.get('macd_signal')),
            macd_histogram=self._to_decimal(last.get('macd_histogram')),
            adx=self._to_decimal(last.get('adx')),
            plus_di=self._to_decimal(last.get('plus_di')),
            minus_di=self._to_decimal(last.get('minus_di')),
            atr=self._to_decimal(last.get('atr')),
            atr_pct=self._to_decimal(last.get('atr_pct')),
            relative_volume=self._to_decimal(last.get('relative_volume')),
            bb_upper=self._to_decimal(last.get('bb_upper')),
            bb_middle=self._to_decimal(last.get('bb_middle')),
            bb_lower=self._to_decimal(last.get('bb_lower')),
        )

    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        pv = typical_price * df['volume']
        cumulative_pv = pv.cumsum()
        cumulative_vol = df['volume'].cumsum()
        vwap = cumulative_pv / cumulative_vol
        return vwap

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(
        self, series: pd.Series, fast: int, slow: int, signal: int
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - macd_signal
        return macd, macd_signal, histogram

    def _calculate_adx(
        self, high: pd.Series, low: pd.Series, close: pd.Series, period: int
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        plus_dm = high.diff()
        minus_dm = low.diff().abs()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        adx = dx.rolling(period).mean()

        return adx, plus_di, minus_di

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _calculate_relative_volume(self, volume: pd.Series, period: int) -> pd.Series:
        avg_volume = volume.rolling(period).mean()
        return volume / avg_volume

    def _calculate_bollinger_bands(
        self, series: pd.Series, period: int, std: float
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = series.rolling(period).mean()
        std_dev = series.rolling(period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        return upper, middle, lower

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None or pd.isna(value):
            return None
        return Decimal(str(round(float(value), 4)))


# Singleton instance
indicator_engine = IndicatorEngine()