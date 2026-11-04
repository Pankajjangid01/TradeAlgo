import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    desc,
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TRADER = "trader"


class BrokerType(str, enum.Enum):
    ANGELONE = "angelone"
    FLATTRADE = "flattrade"


class InstrumentType(str, enum.Enum):
    INDEX = "index"
    FUTURES = "futures"
    OPTION_CE = "option_ce"
    OPTION_PE = "option_pe"


class OrderStatus(str, enum.Enum):
    CREATED = "created"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCEL_PENDING = "cancel_pending"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    SL = "sl"
    SL_M = "sl_m"


class PositionSide(str, enum.Enum):
    LONG = "long"
    SHORT = "short"


class SignalStatus(str, enum.Enum):
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


class MarketRegime(str, enum.Enum):
    STRONG_BULLISH = "strong_bullish"
    STRONG_BEARISH = "strong_bearish"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT_TRANSITION = "breakout_transition"
    UNCERTAIN = "uncertain"


class StrategyType(str, enum.Enum):
    ORB = "orb"
    VWAP_PULLBACK = "vwap_pullback"
    SR_BREAKOUT = "sr_breakout"


class MLModelType(str, enum.Enum):
    KNN = "knn"
    RANDOM_FOREST = "random_forest"
    REGIME_CLASSIFIER = "regime_classifier"


class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.TRADER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Broker(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    broker_type: Mapped[BrokerType] = mapped_column(Enum(BrokerType), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_code_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    totp_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Instrument(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    instrument_type: Mapped[InstrumentType] = mapped_column(Enum(InstrumentType), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), default="NSE", nullable=False)
    token: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False)
    freeze_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tick_size: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    strike: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    underlying: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    option_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_instrument_underlying_expiry", "underlying", "expiry"),
        Index("ix_instrument_token_exchange", "token", "exchange"),
    )


class Candle(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    oi: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    vwap: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="live", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("instrument_id", "timeframe", "timestamp", name="uq_candle_instrument_timeframe_timestamp"),
        Index("ix_candle_instrument_timeframe_timestamp_desc", "instrument_id", "timeframe", desc("timestamp")),
    )


class IndicatorSnapshot(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    ema_9: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    ema_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    ema_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    vwap: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    rsi: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    macd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    macd_signal: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    macd_histogram: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    adx: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    plus_di: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    minus_di: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    atr: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    atr_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    relative_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    bb_upper: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    bb_middle: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    bb_lower: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("instrument_id", "timeframe", "timestamp", name="uq_indicator_instrument_timeframe_timestamp"),
        Index("ix_indicator_instrument_timeframe_timestamp_desc", "instrument_id", "timeframe", desc("timestamp")),
    )


class MarketRegimeSnapshot(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    regime: Mapped[MarketRegime] = mapped_column(Enum(MarketRegime), nullable=False)
    adx: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    ema_9_20_state: Mapped[str] = mapped_column(String(20), nullable=False)
    ema_20_50_state: Mapped[str] = mapped_column(String(20), nullable=False)
    vwap_state: Mapped[str] = mapped_column(String(20), nullable=False)
    atr_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    relative_volume: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("instrument_id", "timestamp", name="uq_regime_instrument_timestamp"),
        Index("ix_regime_instrument_timestamp_desc", "instrument_id", desc("timestamp")),
    )


class SupportResistance(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    level_type: Mapped[str] = mapped_column(String(20), nullable=False)  # support, resistance, pivot, pdh, pdl, or_high, or_low
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    strength: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # number of touches
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    sr_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_sr_instrument_active_price", "instrument_id", "is_active", "price"),
    )


class Signal(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # bullish, bearish
    status: Mapped[SignalStatus] = mapped_column(Enum(SignalStatus), default=SignalStatus.WATCHLIST, nullable=False)
    entry_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    stop_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    risk_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    reward_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    rr_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    regime_at_signal: Mapped[Optional[MarketRegime]] = mapped_column(Enum(MarketRegime), nullable=True)
    indicators_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    structure_data: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    ml_prediction: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_signal_instrument_status_created", "instrument_id", "status", desc("created_at")),
    )


class SignalDecision(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("signal.id", ondelete="CASCADE"), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # approved, rejected, wait
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    component: Mapped[str] = mapped_column(String(50), nullable=False)  # regime, structure, trend, momentum, volume, ml, risk
    details: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MLPrediction(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("signal.id", ondelete="CASCADE"), index=True, nullable=False)
    model_type: Mapped[MLModelType] = mapped_column(Enum(MLModelType), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_class: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=bullish, 2=bearish, 3=no_trade
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    probabilities: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)  # {"1": 0.7, "2": 0.2, "3": 0.1}
    features: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    is_out_of_distribution: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StrategyConfig(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RiskConfig(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Order(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    internal_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # UUID
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    signal_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("signal.id", ondelete="SET NULL"), nullable=True, index=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    broker_id: Mapped[int] = mapped_column(Integer, ForeignKey("broker.id", ondelete="CASCADE"), nullable=False)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    parent_order_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # for bracket orders
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    trigger_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    average_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.CREATED, nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(20), default="MIS", nullable=False)  # MIS, NRML, CNC
    validity: Mapped[str] = mapped_column(String(20), default="DAY", nullable=False)
    tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_order_instrument_status_created", "instrument_id", "status", desc("created_at")),
        Index("ix_order_broker_status_created", "broker_id", "status", desc("created_at")),
    )


class OrderEvent(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)  # created, submitted, acknowledged, partial_fill, filled, rejected, cancelled, expired
    old_status: Mapped[Optional[OrderStatus]] = mapped_column(Enum(OrderStatus), nullable=True)
    new_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    broker_response: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Trade(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order.id", ondelete="CASCADE"), index=True, nullable=False)
    signal_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("signal.id", ondelete="SET NULL"), nullable=True, index=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    broker_id: Mapped[int] = mapped_column(Integer, ForeignKey("broker.id", ondelete="CASCADE"), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    trade_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    broker_trade_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    stt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    exchange_txn: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    sebi: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    stamp_duty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    net_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Position(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), index=True, nullable=False)
    broker_id: Mapped[int] = mapped_column(Integer, ForeignKey("broker.id", ondelete="CASCADE"), nullable=False)
    signal_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("signal.id", ondelete="SET NULL"), nullable=True)
    side: Mapped[PositionSide] = mapped_column(Enum(PositionSide), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    stop_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    trailing_stop: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PnLSnapshot(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    total_unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_realized_pnl: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    open_positions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    margin_used: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    margin_available: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestRun(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    final_capital: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    profit_factor: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    expectancy: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), nullable=True)
    sortino_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class BacktestTrade(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    backtest_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("backtestrun.id", ondelete="CASCADE"), index=True, nullable=False)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(Enum(StrategyType), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    pnl_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    r_multiple: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    max_adverse_excursion: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    max_favorable_excursion: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    regime_at_entry: Mapped[Optional[MarketRegime]] = mapped_column(Enum(MarketRegime), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MLModel(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    model_type: Mapped[MLModelType] = mapped_column(Enum(MLModelType), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    scaler_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    training_start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class SystemHealth(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # healthy, degraded, down
    latency_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class FundsSnapshot(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    broker_id: Mapped[int] = mapped_column(Integer, ForeignKey("broker.id", ondelete="CASCADE"), nullable=False)
    available_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    available_margin: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    used_margin: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_collateral: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    unsettled_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="api", nullable=False)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON, default={}, nullable=True)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContractSelectionLog(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    signal_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("signal.id", ondelete="SET NULL"), nullable=True, index=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    preferred_strike: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    selected_strike: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    selected_instrument_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("instrument.id", ondelete="SET NULL"), nullable=True)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    spot_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    premium: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    available_funds: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_affordable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternatives_considered: Mapped[Optional[list]] = mapped_column(JSON, default=[], nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)