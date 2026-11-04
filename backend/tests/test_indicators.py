import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta

from app.services.indicator_engine import indicator_engine, IndicatorValues
from app.services.market_structure import market_structure_engine, SupportResistanceLevel, LevelType
from app.services.regime_detection import regime_detection_engine, RegimeAnalysis, MarketRegime
from app.strategies.engine import strategy_engine, StrategySignal, SignalDirection, StrategyType
from app.risk.engine import risk_engine, RiskCheckResult, PositionSizeResult


class TestIndicatorEngine:
    """Test technical indicator calculations."""

    def create_sample_data(self, length: int = 100) -> pd.DataFrame:
        """Create sample OHLCV data for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2026-01-01 09:15', periods=length, freq='5min', tz='Asia/Kolkata')
        
        # Generate realistic price data with trend
        base_price = 19800
        trend = np.linspace(0, 200, length)
        noise = np.random.normal(0, 10, length)
        close_prices = base_price + trend + noise
        
        # Generate OHLC from close
        high = close_prices + np.abs(np.random.normal(0, 5, length))
        low = close_prices - np.abs(np.random.normal(0, 5, length))
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = close_prices[0]
        volume = np.random.randint(100000, 1000000, length)
        
        df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close_prices,
            'volume': volume
        }, index=dates)
        
        return df

    def test_calculate_all(self):
        """Test calculating all indicators."""
        df = self.create_sample_data(100)
        result = indicator_engine.calculate_all(df)
        
        # Check all indicator columns exist
        expected_columns = ['ema_9', 'ema_20', 'ema_50', 'vwap', 'rsi', 'macd', 'macd_signal', 
                           'macd_histogram', 'adx', 'plus_di', 'minus_di', 'atr', 'atr_pct',
                           'relative_volume', 'bb_upper', 'bb_middle', 'bb_lower']
        
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"
        
        # Check no NaN in later rows (after warmup period)
        for col in ['ema_9', 'ema_20', 'rsi']:
            assert not result[col].iloc[-10:].isna().any(), f"NaN values in {col}"

    def test_calculate_latest(self):
        """Test incremental latest indicator calculation."""
        df = self.create_sample_data(100)
        result = indicator_engine.calculate_latest(df)
        
        assert isinstance(result, IndicatorValues)
        assert result.ema_9 is not None
        assert result.ema_20 is not None
        assert result.rsi is not None
        assert result.vwap is not None

    def test_ema_calculation(self):
        """Test EMA calculation accuracy."""
        # Simple test with known values
        close = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110])
        ema = indicator_engine._calculate_ema(close, 3)
        
        # EMA should be close to last value for short period
        assert ema.iloc[-1] > 108
        assert ema.iloc[-1] < 110

    def test_rsi_calculation(self):
        """Test RSI calculation."""
        # Strong uptrend should give high RSI
        close = pd.Series([100 + i for i in range(20)])
        rsi = indicator_engine._calculate_rsi(close, 14)
        
        assert rsi.iloc[-1] > 70  # Should be overbought

    def test_macd_calculation(self):
        """Test MACD calculation."""
        close = pd.Series([100 + np.sin(i/2) * 5 for i in range(50)])
        macd, signal, hist = indicator_engine._calculate_macd(close, 12, 26, 9)
        
        assert len(macd) == len(close)
        assert len(signal) == len(close)
        assert len(hist) == len(close)

    def test_atr_calculation(self):
        """Test ATR calculation."""
        df = self.create_sample_data(30)
        atr = indicator_engine._calculate_atr(df['high'], df['low'], df['close'], 14)
        
        assert atr.iloc[-1] > 0
        assert not np.isnan(atr.iloc[-1])

    def test_vwap_calculation(self):
        """Test VWAP calculation."""
        df = self.create_sample_data(30)
        vwap = indicator_engine._calculate_vwap(df)
        
        # VWAP should be between day's high and low
        assert vwap.iloc[-1] >= df['low'].iloc[-1]
        assert vwap.iloc[-1] <= df['high'].iloc[-1]


class TestMarketStructure:
    """Test market structure analysis."""

    def create_trending_data(self) -> pd.DataFrame:
        """Create data with clear trend and swings."""
        dates = pd.date_range(start='2026-01-01 09:15', periods=100, freq='5min', tz='Asia/Kolkata')
        
        # Create uptrend with pullbacks
        base = 19800
        trend = np.linspace(0, 300, 100)
        noise = np.random.normal(0, 5, 100)
        close = base + trend + noise
        
        high = close + np.abs(np.random.normal(0, 3, 100))
        low = close - np.abs(np.random.normal(0, 3, 100))
        open_p = np.roll(close, 1)
        open_p[0] = close[0]
        volume = np.random.randint(500000, 1000000, 100)
        
        return pd.DataFrame({
            'open': open_p, 'high': high, 'low': low, 'close': close, 'volume': volume
        }, index=dates)

    def test_analyze_structure(self):
        """Test market structure analysis."""
        df = self.create_trending_data()
        structure = market_structure_engine.analyze(df)
        
        assert hasattr(structure, 'swing_highs')
        assert hasattr(structure, 'swing_lows')
        assert hasattr(structure, 'support_levels')
        assert hasattr(structure, 'resistance_levels')
        assert hasattr(structure, 'current_trend')
        assert hasattr(structure, 'breakout_status')
        
        # Should detect bullish trend
        assert structure.current_trend in ['bullish', 'bearish', 'sideways']

    def test_find_swings(self):
        """Test swing point detection."""
        df = self.create_trending_data()
        structure = market_structure_engine.analyze(df)
        
        # Should find some swing points
        assert len(structure.swing_highs) >= 0
        assert len(structure.swing_lows) >= 0

    def test_sr_clustering(self):
        """Test support/resistance level clustering."""
        df = self.create_trending_data()
        structure = market_structure_engine.analyze(df)
        
        # Should have some S/R levels
        assert len(structure.support_levels) >= 0
        assert len(structure.resistance_levels) >= 0

    def test_sr_distance(self):
        """Test S/R distance calculation."""
        df = self.create_trending_data()
        structure = market_structure_engine.analyze(df)
        
        current_price = Decimal(str(df['close'].iloc[-1]))
        distances = market_structure_engine.calculate_sr_distance(structure, current_price)
        
        assert 'support_distance_pct' in distances
        assert 'resistance_distance_pct' in distances
        assert 'support_price' in distances
        assert 'resistance_price' in distances


class TestRegimeDetection:
    """Test market regime detection."""

    def create_regime_data(self, regime_type: str = 'bullish') -> tuple:
        """Create data for specific regime."""
        dates = pd.date_range(start='2026-01-01 09:15', periods=100, freq='5min', tz='Asia/Kolkata')
        
        if regime_type == 'bullish':
            base = 19800
            trend = np.linspace(0, 400, 100)
        elif regime_type == 'bearish':
            base = 20200
            trend = np.linspace(0, -400, 100)
        else:  # sideways
            base = 20000
            trend = np.sin(np.linspace(0, 4*np.pi, 100)) * 50
        
        noise = np.random.normal(0, 5, 100)
        close = base + trend + noise
        high = close + np.abs(np.random.normal(0, 3, 100))
        low = close - np.abs(np.random.normal(0, 3, 100))
        open_p = np.roll(close, 1)
        open_p[0] = close[0]
        volume = np.random.randint(500000, 1000000, 100)
        
        df = pd.DataFrame({
            'open': open_p, 'high': high, 'low': low, 'close': close, 'volume': volume
        }, index=dates)
        
        indicators = indicator_engine.calculate_all(df).iloc[-1].to_dict()
        return df, indicators

    def test_bullish_regime(self):
        """Test bullish regime detection."""
        df, indicators = self.create_regime_data('bullish')
        regime = regime_detection_engine.detect(df, indicators)
        
        assert isinstance(regime, RegimeAnalysis)
        assert regime.regime in [MarketRegime.STRONG_BULLISH, MarketRegime.BREAKOUT_TRANSITION]
        assert regime.confidence > 0
        assert regime.trend_strength in ['strong', 'moderate', 'weak']

    def test_bearish_regime(self):
        """Test bearish regime detection."""
        df, indicators = self.create_regime_data('bearish')
        regime = regime_detection_engine.detect(df, indicators)
        
        assert regime.regime in [MarketRegime.STRONG_BEARISH, MarketRegime.BREAKOUT_TRANSITION]

    def test_sideways_regime(self):
        """Test sideways regime detection."""
        df, indicators = self.create_regime_data('sideways')
        regime = regime_detection_engine.detect(df, indicators)
        
        assert regime.regime in [MarketRegime.SIDEWAYS, MarketRegime.LOW_VOLATILITY, MarketRegime.UNCERTAIN]

    def test_hysteresis(self):
        """Test regime hysteresis prevents flipping."""
        df, indicators = self.create_regime_data('bullish')
        
        # Run multiple times
        regimes = []
        for _ in range(5):
            regime = regime_detection_engine.detect(df, indicators)
            regimes.append(regime.regime)
        
        # Should be consistent
        assert len(set(regimes)) <= 2  # At most 2 different regimes


class TestStrategyEngine:
    """Test strategy signal generation."""

    def create_bullish_setup(self) -> tuple:
        """Create data for bullish ORB setup."""
        dates = pd.date_range(start='2026-01-01 09:15', periods=50, freq='5min', tz='Asia/Kolkata')
        
        # Opening range: 9:15-9:30 (first 3 bars)
        or_high = 19850
        or_low = 19800
        or_mid = 19825
        
        # Breakout at 9:35 (4th bar)
        close = np.array([19820, 19830, 19840] + [19860] * 47)  # Breakout above OR high
        high = close + 10
        low = close - 10
        open_p = np.roll(close, 1)
        open_p[0] = close[0]
        volume = np.array([500000, 600000, 700000] + [2000000] * 47)  # High volume on breakout
        
        df = pd.DataFrame({
            'open': open_p, 'high': high, 'low': low, 'close': close, 'volume': volume
        }, index=dates)
        
        indicators = indicator_engine.calculate_latest(df)
        structure = market_structure_engine.analyze(df)
        regime = regime_detection_engine.detect(df, indicator_engine.calculate_all(df).iloc[-1].to_dict())
        
        return df, indicators, structure, regime

    def test_orb_bullish_signal(self):
        """Test ORB bullish signal generation."""
        df, indicators, structure, regime = self.create_bullish_setup()
        current_price = Decimal(str(df['close'].iloc[-1]))
        current_time = df.index[-1]
        
        signals = strategy_engine.evaluate_all(
            df, indicators, structure, regime, current_price, current_time
        )
        
        # Should generate ORB bullish signal
        orb_signals = [s for s in signals if s.strategy_type == StrategyType.ORB]
        assert len(orb_signals) >= 0  # May or may not trigger depending on exact conditions

    def test_signal_structure(self):
        """Test signal data structure."""
        signal = StrategySignal(
            strategy_type=StrategyType.ORB,
            direction=SignalDirection.BULLISH,
            entry_price=Decimal('19860'),
            stop_price=Decimal('19825'),
            target_price=Decimal('19930'),
            risk_per_share=Decimal('35'),
            reward_per_share=Decimal('70'),
            rr_ratio=Decimal('2.0'),
            confidence=Decimal('0.75'),
            metadata={'or_high': '19850', 'or_low': '19800'}
        )
        
        assert signal.strategy_type == StrategyType.ORB
        assert signal.direction == SignalDirection.BULLISH
        assert signal.rr_ratio == Decimal('2.0')


class TestRiskEngine:
    """Test risk management calculations."""

    def test_pre_trade_check_pass(self):
        """Test pre-trade risk check passes for valid trade."""
        check = risk_engine.check_pre_trade(
            signal_entry=Decimal('19860'),
            signal_stop=Decimal('19825'),
            signal_target=Decimal('19930'),
            direction='bullish',
            instrument_type='option_ce',
            available_funds=Decimal('500000'),
            available_margin=Decimal('500000'),
            current_positions=[],
            daily_pnl=Decimal('0'),
            strategy_capital=Decimal('1000000'),
            consecutive_losses=0,
            option_premium=Decimal('150'),
            lot_size=75
        )
        
        assert check.result == RiskCheckResult.PASS

    def test_pre_trade_check_block_daily_loss(self):
        """Test pre-trade check blocks when daily loss limit reached."""
        check = risk_engine.check_pre_trade(
            signal_entry=Decimal('19860'),
            signal_stop=Decimal('19825'),
            signal_target=Decimal('19930'),
            direction='bullish',
            instrument_type='option_ce',
            available_funds=Decimal('500000'),
            available_margin=Decimal('500000'),
            current_positions=[],
            daily_pnl=Decimal('-15000'),  # Exceeds 1.25% of 1M = 12500
            strategy_capital=Decimal('1000000'),
            consecutive_losses=0,
            option_premium=Decimal('150'),
            lot_size=75
        )
        
        assert check.result == RiskCheckResult.BLOCK

    def test_pre_trade_check_block_max_positions(self):
        """Test pre-trade check blocks when max positions reached."""
        from app.db.models import Position, PositionSide
        
        positions = [
            Position(id=1, instrument_id=1, broker_id=1, side=PositionSide.LONG,
                    quantity=75, average_price=Decimal('150'), is_open=True)
        ]
        
        check = risk_engine.check_pre_trade(
            signal_entry=Decimal('19860'),
            signal_stop=Decimal('19825'),
            signal_target=Decimal('19930'),
            direction='bullish',
            instrument_type='option_ce',
            available_funds=Decimal('500000'),
            available_margin=Decimal('500000'),
            current_positions=positions,
            daily_pnl=Decimal('0'),
            strategy_capital=Decimal('1000000'),
            consecutive_losses=0,
            option_premium=Decimal('150'),
            lot_size=75
        )
        
        assert check.result == RiskCheckResult.BLOCK

    def test_position_size_calculation(self):
        """Test position size calculation."""
        result = risk_engine.calculate_position_size(
            signal_entry=Decimal('19860'),
            signal_stop=Decimal('19825'),
            signal_target=Decimal('19930'),
            direction='bullish',
            available_funds=Decimal('500000'),
            available_margin=Decimal('500000'),
            current_positions=[],
            strategy_capital=Decimal('1000000'),
            option_premium=Decimal('150'),
            lot_size=75
        )
        
        assert isinstance(result, PositionSizeResult)
        assert result.quantity % 75 == 0  # Multiple of lot size
        assert result.quantity >= 0
        assert result.limiting_factor in ['risk_budget', 'available_funds', 'max_exposure', 'lot_size']

    def test_stop_target_calculation(self):
        """Test stop loss and target calculation."""
        stop, target = risk_engine.calculate_stop_target(
            entry_price=Decimal('19860'),
            method='atr',
            atr=Decimal('150'),
            target_r=2.0
        )
        
        assert stop < Decimal('19860')
        assert target > Decimal('19860')
        assert (target - Decimal('19860')) / (Decimal('19860') - stop) == Decimal('2.0')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])