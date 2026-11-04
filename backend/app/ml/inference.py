import logging
import joblib
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MLModelType(str, Enum):
    KNN = "knn"
    RANDOM_FOREST = "random_forest"
    REGIME_CLASSIFIER = "regime_classifier"


class PredictionClass(int, Enum):
    BULLISH = 1
    BEARISH = 2
    NO_TRADE = 3


@dataclass
class MLPrediction:
    predicted_class: PredictionClass
    confidence: Decimal
    probabilities: Dict[int, Decimal]
    is_out_of_distribution: bool
    model_version: str
    features_used: List[str]


class MLInferenceEngine:
    def __init__(self):
        self.model_path = Path(settings.ML_CONFIG["model_path"])
        self.scaler_path = Path(settings.ML_CONFIG["scaler_path"])
        self.knn_neighbors = settings.ML_CONFIG["knn_neighbors"]
        self.knn_weights = settings.ML_CONFIG["knn_weights"]
        self.feature_columns = settings.ML_CONFIG["feature_columns"]
        self.confidence_threshold = settings.ML_CONFIG["confidence_threshold"]
        
        self._model = None
        self._scaler = None
        self._model_version = "1.0.0"
        self._is_loaded = False

    def load_model(self) -> bool:
        """Load the trained model and scaler."""
        try:
            if self.model_path.exists() and self.scaler_path.exists():
                self._model = joblib.load(self.model_path)
                self._scaler = joblib.load(self.scaler_path)
                self._is_loaded = True
                logger.info(f"Model loaded from {self.model_path}")
                return True
            else:
                logger.warning("Model files not found. Using rule-based fallback.")
                return False
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def predict(self, features: Dict[str, float]) -> MLPrediction:
        """Make prediction using the loaded model."""
        if not self._is_loaded:
            return self._rule_based_prediction(features)

        try:
            # Prepare feature vector
            feature_vector = self._prepare_features(features)
            if feature_vector is None:
                return self._rule_based_prediction(features)

            # Scale features
            feature_scaled = self._scaler.transform([feature_vector])

            # Predict
            prediction = self._model.predict(feature_scaled)[0]
            probabilities = self._model.predict_proba(feature_scaled)[0]

            # Get class probabilities
            prob_dict = {i+1: Decimal(str(round(float(p), 4))) for i, p in enumerate(probabilities)}
            confidence = Decimal(str(round(float(max(probabilities)), 3)))

            # Check out-of-distribution (low confidence or unusual feature values)
            is_ood = self._check_out_of_distribution(feature_vector, confidence)

            return MLPrediction(
                predicted_class=PredictionClass(prediction),
                confidence=confidence,
                probabilities=prob_dict,
                is_out_of_distribution=is_ood,
                model_version=self._model_version,
                features_used=self.feature_columns
            )

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._rule_based_prediction(features)

    def _prepare_features(self, features: Dict[str, float]) -> Optional[np.ndarray]:
        """Prepare feature vector in correct order."""
        try:
            vector = []
            for col in self.feature_columns:
                if col not in features:
                    logger.warning(f"Missing feature: {col}")
                    return None
                vector.append(features[col])
            return np.array(vector, dtype=np.float32)
        except Exception as e:
            logger.error(f"Feature preparation error: {e}")
            return None

    def _check_out_of_distribution(self, feature_vector: np.ndarray, confidence: Decimal) -> bool:
        """Check if input is out of distribution."""
        # Low confidence threshold
        if confidence < Decimal("0.5"):
            return True
        
        # Check for extreme feature values (beyond training range)
        # This would ideally use training statistics
        # For now, just check for NaN/inf
        if np.any(np.isnan(feature_vector)) or np.any(np.isinf(feature_vector)):
            return True
        
        return False

    def _rule_based_prediction(self, features: Dict[str, float]) -> MLPrediction:
        """Fallback rule-based prediction when model unavailable."""
        # Extract key features
        ema_9_20_dist = features.get("ema_9_20_distance", 0)
        ema_20_50_dist = features.get("ema_20_50_distance", 0)
        vwap_dist = features.get("vwap_distance", 0)
        rsi = features.get("rsi", 50)
        macd_hist = features.get("macd_histogram", 0)
        adx = features.get("adx", 0)
        plus_di = features.get("plus_di", 0)
        minus_di = features.get("minus_di", 0)
        rvol = features.get("relative_volume", 1)
        breakout_status = features.get("breakout_status", 0)
        regime = features.get("market_regime", 0)

        # Simple scoring
        bullish_score = 0
        bearish_score = 0

        # EMA alignment
        if ema_9_20_dist > 0 and ema_20_50_dist > 0:
            bullish_score += 2
        elif ema_9_20_dist < 0 and ema_20_50_dist < 0:
            bearish_score += 2

        # VWAP
        if vwap_dist > 0:
            bullish_score += 1
        elif vwap_dist < 0:
            bearish_score += 1

        # RSI
        if rsi > 55:
            bullish_score += 1
        elif rsi < 45:
            bearish_score += 1

        # MACD
        if macd_hist > 0:
            bullish_score += 1
        elif macd_hist < 0:
            bearish_score += 1

        # ADX + DI
        if adx > 25:
            if plus_di > minus_di:
                bullish_score += 2
            else:
                bearish_score += 2

        # Volume
        if rvol > 1.5:
            if bullish_score > bearish_score:
                bullish_score += 1
            elif bearish_score > bullish_score:
                bearish_score += 1

        # Breakout
        if breakout_status == 1:  # bullish breakout
            bullish_score += 2
        elif breakout_status == -1:  # bearish breakout
            bearish_score += 2

        # Regime
        if regime == 1:  # strong bullish
            bullish_score += 2
        elif regime == 2:  # strong bearish
            bearish_score += 2

        # Determine class
        if bullish_score > bearish_score and bullish_score >= 4:
            pred_class = PredictionClass.BULLISH
            confidence = min(0.5 + (bullish_score - bearish_score) * 0.05, 0.85)
        elif bearish_score > bullish_score and bearish_score >= 4:
            pred_class = PredictionClass.BEARISH
            confidence = min(0.5 + (bearish_score - bullish_score) * 0.05, 0.85)
        else:
            pred_class = PredictionClass.NO_TRADE
            confidence = 0.6

        prob_dict = {
            1: Decimal(str(round(confidence if pred_class == PredictionClass.BULLISH else (1-confidence)/2, 3))),
            2: Decimal(str(round(confidence if pred_class == PredictionClass.BEARISH else (1-confidence)/2, 3))),
            3: Decimal(str(round(confidence if pred_class == PredictionClass.NO_TRADE else (1-confidence)/2, 3))),
        }

        return MLPrediction(
            predicted_class=pred_class,
            confidence=Decimal(str(round(confidence, 3))),
            probabilities=prob_dict,
            is_out_of_distribution=False,
            model_version="rule_based_v1",
            features_used=list(features.keys())
        )

    def extract_features(
        self,
        indicators: Dict[str, Any],
        structure: Dict[str, Any],
        regime: Dict[str, Any],
        current_price: float
    ) -> Dict[str, float]:
        """Extract ML features from current market state."""
        features = {}

        # EMA distances
        ema_9 = indicators.get("ema_9", 0)
        ema_20 = indicators.get("ema_20", 0)
        ema_50 = indicators.get("ema_50", 0)
        
        if ema_9 and ema_20:
            features["ema_9_20_distance"] = (ema_9 - ema_20) / ema_20 * 100
        else:
            features["ema_9_20_distance"] = 0
            
        if ema_20 and ema_50:
            features["ema_20_50_distance"] = (ema_20 - ema_50) / ema_50 * 100
        else:
            features["ema_20_50_distance"] = 0

        # VWAP distance
        vwap = indicators.get("vwap", 0)
        if vwap:
            features["vwap_distance"] = (current_price - vwap) / vwap * 100
        else:
            features["vwap_distance"] = 0

        # RSI
        features["rsi"] = indicators.get("rsi", 50)

        # MACD histogram
        features["macd_histogram"] = indicators.get("macd_histogram", 0)

        # ADX
        features["adx"] = indicators.get("adx", 0)

        # DI
        features["plus_di"] = indicators.get("plus_di", 0)
        features["minus_di"] = indicators.get("minus_di", 0)

        # ATR %
        features["atr_pct"] = indicators.get("atr_pct", 0)

        # Relative Volume
        features["relative_volume"] = indicators.get("relative_volume", 1)

        # Candle ratios
        features["body_to_range_ratio"] = 0  # Would need current candle
        features["upper_wick_ratio"] = 0
        features["lower_wick_ratio"] = 0

        # S/R distance
        sr_dist = structure.get("sr_distance", {})
        features["sr_distance"] = sr_dist.get("resistance_distance_pct", 0) - sr_dist.get("support_distance_pct", 0)

        # Breakout status
        breakout_map = {
            "bullish_bos": 1,
            "bearish_bos": -1,
            "bullish_choch": 1,
            "bearish_choch": -1,
            "none": 0
        }
        features["breakout_status"] = breakout_map.get(structure.get("breakout_status", "none"), 0)

        # Market regime
        regime_map = {
            "strong_bullish": 1,
            "strong_bearish": 2,
            "sideways": 3,
            "high_volatility": 4,
            "low_volatility": 5,
            "breakout_transition": 6,
            "uncertain": 0
        }
        features["market_regime"] = regime_map.get(regime.get("regime", "uncertain"), 0)

        # Time of day (normalized 0-1)
        from datetime import datetime
        now = datetime.now()
        minutes_from_open = (now.hour - 9) * 60 + now.minute - 15
        features["time_of_day"] = max(0, min(1, minutes_from_open / (6.5 * 60)))

        # India VIX (placeholder)
        features["india_vix"] = 15.0

        # Futures OI change (placeholder)
        features["futures_oi_change"] = 0.0

        return features


# Singleton instance
ml_inference_engine = MLInferenceEngine()