import pytest
from decimal import Decimal
from app.ml.inference import ml_inference_engine, MLPrediction, PredictionClass


class TestMLInferenceEngine:
    """Test ML inference engine."""

    def test_rule_based_prediction_bullish(self):
        """Test rule-based prediction for bullish setup."""
        features = {
            "ema_9_20_distance": 0.5,
            "ema_20_50_distance": 0.3,
            "vwap_distance": 0.2,
            "rsi": 65,
            "macd_histogram": 5.0,
            "adx": 30,
            "plus_di": 25,
            "minus_di": 15,
            "atr_pct": 0.7,
            "relative_volume": 1.5,
            "body_to_range_ratio": 0.6,
            "upper_wick_ratio": 0.1,
            "lower_wick_ratio": 0.2,
            "sr_distance": 0.5,
            "breakout_status": 1,
            "market_regime": 1,
            "time_of_day": 0.3,
            "india_vix": 15,
            "futures_oi_change": 0.02,
        }
        
        prediction = ml_inference_engine._rule_based_prediction(features)
        
        assert isinstance(prediction, MLPrediction)
        assert prediction.predicted_class in [PredictionClass.BULLISH, PredictionClass.BEARISH, PredictionClass.NO_TRADE]
        assert 0 <= prediction.confidence <= 1
        assert len(prediction.probabilities) == 3
        assert sum(prediction.probabilities.values()) > 0

    def test_rule_based_prediction_bearish(self):
        """Test rule-based prediction for bearish setup."""
        features = {
            "ema_9_20_distance": -0.5,
            "ema_20_50_distance": -0.3,
            "vwap_distance": -0.2,
            "rsi": 35,
            "macd_histogram": -5.0,
            "adx": 30,
            "plus_di": 15,
            "minus_di": 25,
            "atr_pct": 0.7,
            "relative_volume": 1.5,
            "body_to_range_ratio": 0.6,
            "upper_wick_ratio": 0.2,
            "lower_wick_ratio": 0.1,
            "sr_distance": -0.5,
            "breakout_status": -1,
            "market_regime": 2,
            "time_of_day": 0.3,
            "india_vix": 15,
            "futures_oi_change": -0.02,
        }
        
        prediction = ml_inference_engine._rule_based_prediction(features)
        
        assert prediction.predicted_class == PredictionClass.BEARISH
        assert prediction.confidence > 0.5

    def test_rule_based_prediction_no_trade(self):
        """Test rule-based prediction for no-trade setup."""
        features = {
            "ema_9_20_distance": 0.0,
            "ema_20_50_distance": 0.0,
            "vwap_distance": 0.0,
            "rsi": 50,
            "macd_histogram": 0.0,
            "adx": 15,
            "plus_di": 20,
            "minus_di": 20,
            "atr_pct": 0.5,
            "relative_volume": 0.8,
            "body_to_range_ratio": 0.5,
            "upper_wick_ratio": 0.15,
            "lower_wick_ratio": 0.15,
            "sr_distance": 0.0,
            "breakout_status": 0,
            "market_regime": 3,
            "time_of_day": 0.5,
            "india_vix": 12,
            "futures_oi_change": 0.0,
        }
        
        prediction = ml_inference_engine._rule_based_prediction(features)
        
        assert prediction.predicted_class == PredictionClass.NO_TRADE

    def test_extract_features(self):
        """Test feature extraction from market state."""
        indicators = {
            "ema_9": 19850,
            "ema_20": 19820,
            "ema_50": 19750,
            "vwap": 19830,
            "rsi": 60,
            "macd_histogram": 3.5,
            "adx": 28,
            "plus_di": 22,
            "minus_di": 18,
            "atr_pct": 0.007,
            "relative_volume": 1.3,
        }
        
        structure = {
            "sr_distance": {
                "support_distance_pct": 0.3,
                "resistance_distance_pct": 0.5,
            },
            "breakout_status": "bullish_bos",
        }
        
        regime = {
            "regime": "strong_bullish",
            "trend_strength": "moderate",
        }
        
        current_price = 19855.0
        
        features = ml_inference_engine.extract_features(
            indicators, structure, regime, current_price
        )
        
        # Check all expected features present
        expected_features = [
            "ema_9_20_distance", "ema_20_50_distance", "vwap_distance", "rsi",
            "macd_histogram", "adx", "plus_di", "minus_di", "atr_pct",
            "relative_volume", "body_to_range_ratio", "upper_wick_ratio",
            "lower_wick_ratio", "sr_distance", "breakout_status",
            "market_regime", "time_of_day", "india_vix", "futures_oi_change"
        ]
        
        for feat in expected_features:
            assert feat in features, f"Missing feature: {feat}"
        
        # Check specific values
        assert features["ema_9_20_distance"] > 0  # EMA 9 > EMA 20
        assert features["ema_20_50_distance"] > 0  # EMA 20 > EMA 50
        assert features["vwap_distance"] > 0  # Price > VWAP
        assert features["breakout_status"] == 1  # Bullish BOS
        assert features["market_regime"] == 1  # Strong bullish

    def test_predict_without_model(self):
        """Test prediction falls back to rule-based when no model loaded."""
        # Ensure model is not loaded
        ml_inference_engine._is_loaded = False
        ml_inference_engine._model = None
        ml_inference_engine._scaler = None
        
        features = {
            "ema_9_20_distance": 0.5,
            "ema_20_50_distance": 0.3,
            "vwap_distance": 0.2,
            "rsi": 65,
            "macd_histogram": 5.0,
            "adx": 30,
            "plus_di": 25,
            "minus_di": 15,
            "atr_pct": 0.7,
            "relative_volume": 1.5,
            "body_to_range_ratio": 0.6,
            "upper_wick_ratio": 0.1,
            "lower_wick_ratio": 0.2,
            "sr_distance": 0.5,
            "breakout_status": 1,
            "market_regime": 1,
            "time_of_day": 0.3,
            "india_vix": 15,
            "futures_oi_change": 0.02,
        }
        
        prediction = ml_inference_engine.predict(features)
        
        assert isinstance(prediction, MLPrediction)
        assert prediction.model_version == "rule_based_v1"


class TestMLPrediction:
    """Test MLPrediction dataclass."""

    def test_prediction_creation(self):
        """Test creating prediction object."""
        pred = MLPrediction(
            predicted_class=PredictionClass.BULLISH,
            confidence=Decimal('0.75'),
            probabilities={1: Decimal('0.75'), 2: Decimal('0.15'), 3: Decimal('0.10')},
            is_out_of_distribution=False,
            model_version="knn_v1.2",
            features_used=["ema_9_20_distance", "rsi", "adx"]
        )
        
        assert pred.predicted_class == PredictionClass.BULLISH
        assert pred.confidence == Decimal('0.75')
        assert len(pred.probabilities) == 3

    def test_probability_sum(self):
        """Test probability distribution sums to ~1."""
        pred = MLPrediction(
            predicted_class=PredictionClass.BULLISH,
            confidence=Decimal('0.75'),
            probabilities={1: Decimal('0.75'), 2: Decimal('0.15'), 3: Decimal('0.10')},
            is_out_of_distribution=False,
            model_version="test",
            features_used=[]
        )
        
        total = sum(pred.probabilities.values())
        assert abs(total - Decimal('1.0')) < Decimal('0.01')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])