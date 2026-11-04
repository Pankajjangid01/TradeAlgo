import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # App
    APP_NAME: str = "TradeIQ"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # API
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://tradeiq:tradeiq@localhost:5432/tradeiq"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10

    # Angel One SmartAPI
    ANGELONE_API_KEY: str = ""
    ANGELONE_CLIENT_CODE: str = ""
    ANGELONE_PASSWORD: str = ""
    ANGELONE_TOTP_SECRET: str = ""
    ANGELONE_SMART_API_URL: str = "https://apiconnect.angelone.in"
    ANGELONE_WEBSOCKET_URL: str = "wss://smartapisocket.angelone.in/smart-stream"

    # Flattrade Pi API
    FLATTRADE_API_KEY: str = ""
    FLATTRADE_API_SECRET: str = ""
    FLATTRADE_CLIENT_ID: str = ""
    FLATTRADE_REDIRECT_URL: str = ""
    FLATTRADE_BASE_URL: str = "https://piconnect.flattrade.in"
    FLATTRADE_WEBSOCKET_URL: str = "wss://piconnect.flattrade.in/ws"

    # Market Data
    MARKET_DATA_PROVIDER: str = "angelone"  # angelone, flattrade
    ENABLE_HISTORICAL_DOWNLOAD: bool = True
    HISTORICAL_DATA_DAYS: int = 365

    # Instruments (NIFTY and SENSEX only per BRD)
    TRADING_INSTRUMENTS: List[str] = ["NIFTY", "SENSEX"]
    INDEX_SYMBOLS: dict = {
        "NIFTY": "NIFTY 50",
        "SENSEX": "SENSEX"
    }

    # Strategy Configuration
    STRATEGY_CONFIG: dict = {
        "orb": {
            "enabled": True,
            "opening_range_minutes": 15,
            "orb_start_time": "09:15",
            "orb_end_time": "09:30",
            "min_relative_volume": 1.5,
            "require_vwap_confirmation": True,
            "require_ema_confirmation": True,
            "require_rsi_confirmation": True,
            "require_macd_confirmation": True,
        },
        "vwap_pullback": {
            "enabled": True,
            "pullback_tolerance_pct": 0.3,
            "require_rejection_candle": True,
            "min_rsi_recovery": 50,
            "require_volume_confirmation": True,
        },
        "sr_breakout": {
            "enabled": True,
            "min_touches": 2,
            "cluster_distance_pct": 0.2,
            "require_retest": True,
            "retest_tolerance_pct": 0.15,
            "require_volume_expansion": True,
        }
    }

    # Indicator Configuration
    INDICATOR_CONFIG: dict = {
        "ema_periods": [9, 20, 50],
        "rsi_period": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "adx_period": 14,
        "atr_period": 14,
        "vwap_session": True,
        "bollinger_period": 20,
        "bollinger_std": 2,
        "relative_volume_period": 20,
    }

    # Market Regime Configuration
    REGIME_CONFIG: dict = {
        "adx_trend_threshold": 25,
        "adx_strong_threshold": 40,
        "atr_high_volatility_multiplier": 1.5,
        "atr_low_volatility_multiplier": 0.5,
        "ema_trend_lookback": 20,
        "hysteresis_bars": 3,
    }

    # ML Configuration
    ML_CONFIG: dict = {
        "model_path": "models/knn_classifier.joblib",
        "scaler_path": "models/scaler.joblib",
        "knn_neighbors": 15,
        "knn_weights": "distance",
        "feature_columns": [
            "ema_9_20_distance",
            "ema_20_50_distance",
            "vwap_distance",
            "rsi",
            "macd_histogram",
            "adx",
            "plus_di",
            "minus_di",
            "atr_pct",
            "relative_volume",
            "body_to_range_ratio",
            "upper_wick_ratio",
            "lower_wick_ratio",
            "sr_distance",
            "breakout_status",
            "market_regime",
            "time_of_day",
            "india_vix",
            "futures_oi_change",
        ],
        "target_labels": {
            1: "bullish",
            2: "bearish",
            3: "no_trade"
        },
        "confidence_threshold": 0.65,
        "retrain_interval_days": 7,
    }

    # Risk Management Configuration
    RISK_CONFIG: dict = {
        "initial_risk_per_trade_pct": 0.0035,  # 0.35%
        "max_daily_loss_pct": 0.0125,  # 1.25%
        "max_simultaneous_positions": 1,
        "max_consecutive_losses": 3,
        "target_r_multiple": 2.0,
        "partial_exit_r_multiple": 1.5,
        "trailing_stop_activation_r": 1.0,
        "trailing_stop_distance_atr": 1.0,
        "max_slippage_pct": 0.002,  # 0.2%
        "cash_buffer_pct": 0.10,  # 10% cash reserve
        "stop_methods": {
            "orb": "or_mid",
            "vwap_pullback": "atr",
            "sr_breakout": "structure",
        },
        "atr_stop_multiplier": 1.5,
        "percent_stop_pct": 0.01,
    }

    # Options Selection Configuration
    OPTIONS_CONFIG: dict = {
        "preferred_strikes": ["atm", "otm_1", "itm_1"],
        "max_spread_pct": 0.05,  # 5% max bid-ask spread
        "min_oi_threshold": 1000,
        "min_volume_threshold": 500,
        "min_depth_threshold": 10,
        "lot_sizes": {
            "NIFTY": 75,
            "SENSEX": 10,
        },
        "expiry_selection": "current_weekly",
        "slippage_buffer_pct": 0.01,
        "charges_buffer_pct": 0.005,
    }

    # Order Management Configuration
    OMS_CONFIG: dict = {
        "idempotency_key_ttl_seconds": 300,
        "order_timeout_seconds": 30,
        "reconciliation_interval_seconds": 60,
        "max_retry_attempts": 3,
        "retry_delay_seconds": 2,
        "bracket_order_enabled": False,  # Use client-side bracket management
    }

    # Backtesting Configuration
    BACKTEST_CONFIG: dict = {
        "default_start_date": "2024-01-01",
        "default_end_date": "2026-11-04",
        "slippage_pct": 0.001,
        "commission_per_lot": 20,
        "stt_pct": 0.0005,
        "exchange_txn_pct": 0.000345,
        "gst_pct": 0.18,
        "sebi_pct": 0.000001,
        "stamp_duty_pct": 0.00003,
    }

    # Monitoring Configuration
    MONITORING_CONFIG: dict = {
        "latency_buckets": [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        "health_check_interval_seconds": 30,
        "metrics_retention_days": 30,
        "alert_on_daily_loss_pct": 0.01,
        "alert_on_consecutive_losses": 2,
    }


settings = Settings()