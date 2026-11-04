"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2026-11-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('admin', 'trader', name='userrole'), nullable=False, server_default='trader'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create brokers table
    op.create_table(
        'brokers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('broker_type', sa.Enum('angelone', 'flattrade', name='brokertype'), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('api_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('client_code_encrypted', sa.Text(), nullable=True),
        sa.Column('totp_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create instruments table
    op.create_table(
        'instruments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('instrument_type', sa.Enum('index', 'futures', 'option_ce', 'option_pe', name='instrumenttype'), nullable=False),
        sa.Column('exchange', sa.String(length=20), nullable=False, server_default='NSE'),
        sa.Column('token', sa.String(length=50), nullable=False),
        sa.Column('lot_size', sa.Integer(), nullable=False),
        sa.Column('freeze_qty', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tick_size', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('strike', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('underlying', sa.String(length=50), nullable=True),
        sa.Column('option_type', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index('ix_instrument_token_exchange', 'instruments', ['token', 'exchange'])
    op.create_index('ix_instrument_underlying_expiry', 'instruments', ['underlying', 'expiry'])

    # Create candles table
    op.create_table(
        'candles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('high', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('low', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('oi', sa.BigInteger(), nullable=True),
        sa.Column('vwap', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='live'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'timeframe', 'timestamp', name='uq_candle_instrument_timeframe_timestamp')
    )
    op.create_index('ix_candle_instrument_timeframe_timestamp_desc', 'candles', ['instrument_id', 'timeframe', sa.text('timestamp DESC')])

    # Create indicator_snapshots table
    op.create_table(
        'indicator_snapshots',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ema_9', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('ema_20', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('ema_50', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('vwap', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('rsi', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('macd', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('macd_signal', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('macd_histogram', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('adx', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('plus_di', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('minus_di', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('atr', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('atr_pct', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('relative_volume', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('bb_upper', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('bb_middle', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('bb_lower', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'timeframe', 'timestamp', name='uq_indicator_instrument_timeframe_timestamp')
    )
    op.create_index('ix_indicator_instrument_timeframe_timestamp_desc', 'indicator_snapshots', ['instrument_id', 'timeframe', sa.text('timestamp DESC')])

    # Create market_regimes table
    op.create_table(
        'market_regimes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('regime', sa.Enum('strong_bullish', 'strong_bearish', 'sideways', 'high_volatility', 'low_volatility', 'breakout_transition', 'uncertain', name='marketregime'), nullable=False),
        sa.Column('adx', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('ema_9_20_state', sa.String(length=20), nullable=False),
        sa.Column('ema_20_50_state', sa.String(length=20), nullable=False),
        sa.Column('vwap_state', sa.String(length=20), nullable=False),
        sa.Column('atr_pct', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('relative_volume', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'timestamp', name='uq_regime_instrument_timestamp')
    )
    op.create_index('ix_regime_instrument_timestamp_desc', 'market_regimes', ['instrument_id', sa.text('timestamp DESC')])

    # Create support_resistance table
    op.create_table(
        'support_resistance',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('level_type', sa.String(length=20), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('strength', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sr_instrument_active_price', 'support_resistance', ['instrument_id', 'is_active', 'price'])

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('strategy_type', sa.Enum('orb', 'vwap_pullback', 'sr_breakout', name='strategytype'), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('status', sa.Enum('watchlist', 'setup_forming', 'wait_for_confirmation', 'approved', 'rejected', 'order_pending', 'position_open', 'exit_pending', 'closed', 'error', 'halted', name='signalstatus'), nullable=False, server_default='watchlist'),
        sa.Column('entry_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('stop_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('target_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('risk_per_share', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('reward_per_share', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('rr_ratio', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('regime_at_signal', sa.Enum('strong_bullish', 'strong_bearish', 'sideways', 'high_volatility', 'low_volatility', 'breakout_transition', 'uncertain', name='marketregime'), nullable=True),
        sa.Column('indicators_snapshot', sa.JSON(), nullable=True),
        sa.Column('structure_data', sa.JSON(), nullable=True),
        sa.Column('ml_prediction', sa.JSON(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_signal_instrument_status_created', 'signals', ['instrument_id', 'status', sa.text('created_at DESC')])

    # Create signal_decisions table
    op.create_table(
        'signal_decisions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('signal_id', sa.BigInteger(), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('component', sa.String(length=50), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ml_predictions table
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('signal_id', sa.BigInteger(), nullable=False),
        sa.Column('model_type', sa.Enum('knn', 'random_forest', 'regime_classifier', name='mlmodeltype'), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('predicted_class', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column('probabilities', sa.JSON(), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('is_out_of_distribution', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create strategy_configs table
    op.create_table(
        'strategy_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('strategy_type', sa.Enum('orb', 'vwap_pullback', 'sr_breakout', name='strategytype'), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create risk_configs table
    op.create_table(
        'risk_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('internal_id', sa.String(length=64), nullable=False),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('signal_id', sa.BigInteger(), nullable=True),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('broker_id', sa.Integer(), nullable=False),
        sa.Column('broker_order_id', sa.String(length=50), nullable=True),
        sa.Column('parent_order_id', sa.String(length=50), nullable=True),
        sa.Column('order_type', sa.Enum('market', 'limit', 'sl', 'sl_m', name='ordertype'), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='orderside'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('filled_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('trigger_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('average_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('status', sa.Enum('created', 'validated', 'submitted', 'acknowledged', 'partially_filled', 'filled', 'rejected', 'cancel_pending', 'cancelled', 'expired', 'unknown', name='orderstatus'), nullable=False, server_default='created'),
        sa.Column('product_type', sa.String(length=20), nullable=False, server_default='MIS'),
        sa.Column('validity', sa.String(length=20), nullable=False, server_default='DAY'),
        sa.Column('tag', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('internal_id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_order_instrument_status_created', 'orders', ['instrument_id', 'status', sa.text('created_at DESC')])
    op.create_index('ix_order_broker_status_created', 'orders', ['broker_id', 'status', sa.text('created_at DESC')])

    # Create order_events table
    op.create_table(
        'order_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('old_status', sa.Enum('created', 'validated', 'submitted', 'acknowledged', 'partially_filled', 'filled', 'rejected', 'cancel_pending', 'cancelled', 'expired', 'unknown', name='orderstatus'), nullable=True),
        sa.Column('new_status', sa.Enum('created', 'validated', 'submitted', 'acknowledged', 'partially_filled', 'filled', 'rejected', 'cancel_pending', 'cancelled', 'expired', 'unknown', name='orderstatus'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('broker_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_order_event_order_id_created', 'order_events', ['order_id', sa.text('created_at DESC')])

    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=False),
        sa.Column('signal_id', sa.BigInteger(), nullable=True),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('broker_id', sa.Integer(), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='orderside'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('trade_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('broker_trade_id', sa.String(length=50), nullable=False),
        sa.Column('commission', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('stt', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('exchange_txn', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('gst', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('sebi', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('stamp_duty', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('net_pnl', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('broker_trade_id')
    )

    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('broker_id', sa.Integer(), nullable=False),
        sa.Column('signal_id', sa.BigInteger(), nullable=True),
        sa.Column('side', sa.Enum('long', 'short', name='positionside'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('average_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('unrealized_pnl', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('stop_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('target_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('trailing_stop', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('is_open', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_position_instrument_opened', 'positions', ['instrument_id', sa.text('opened_at DESC')])

    # Create pnl_snapshots table
    op.create_table(
        'pnl_snapshots',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('total_unrealized_pnl', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('total_realized_pnl', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('daily_pnl', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('open_positions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('margin_used', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('margin_available', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('snapshot_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pnl_snapshot_time', 'pnl_snapshots', [sa.text('snapshot_time DESC')])

    # Create backtest_runs table
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('strategy_type', sa.Enum('orb', 'vwap_pullback', 'sr_breakout', name='strategytype'), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('initial_capital', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('final_capital', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('winning_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('losing_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('win_rate', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0'),
        sa.Column('profit_factor', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0'),
        sa.Column('expectancy', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('max_drawdown', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('sharpe_ratio', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='running'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create backtest_trades table
    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('backtest_run_id', sa.Integer(), nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('strategy_type', sa.Enum('orb', 'vwap_pullback', 'sr_breakout', name='strategytype'), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('stop_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('target_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('pnl', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('pnl_pct', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('r_multiple', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('max_adverse_excursion', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_favorable_excursion', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('exit_reason', sa.String(length=50), nullable=True),
        sa.Column('regime_at_entry', sa.Enum('strong_bullish', 'strong_bearish', 'sideways', 'high_volatility', 'low_volatility', 'breakout_transition', 'uncertain', name='marketregime'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_backtest_trade_run_id', 'backtest_trades', ['backtest_run_id'])

    # Create ml_models table
    op.create_table(
        'ml_models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('model_type', sa.Enum('knn', 'random_forest', 'regime_classifier', name='mlmodeltype'), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('scaler_path', sa.String(length=255), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('training_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('training_end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_log_action_created', 'audit_logs', ['action', sa.text('created_at DESC')])
    op.create_index('ix_audit_log_entity', 'audit_logs', ['entity_type', 'entity_id'])

    # Create system_health table
    op.create_table(
        'system_health',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('service_name', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_system_health_service_checked', 'system_health', ['service_name', sa.text('checked_at DESC')])

    # Create funds_snapshots table
    op.create_table(
        'funds_snapshots',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('broker_id', sa.Integer(), nullable=False),
        sa.Column('available_cash', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('available_margin', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('used_margin', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
        sa.Column('total_collateral', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('unsettled_amount', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='api'),
        sa.Column('raw_response', sa.JSON(), nullable=True),
        sa.Column('snapshot_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_funds_snapshot_broker_time', 'funds_snapshots', ['broker_id', sa.text('snapshot_time DESC')])

    # Create contract_selection_logs table
    op.create_table(
        'contract_selection_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('signal_id', sa.BigInteger(), nullable=True),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('preferred_strike', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('selected_strike', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('selected_instrument_id', sa.Integer(), nullable=True),
        sa.Column('strategy', sa.String(length=20), nullable=False),
        sa.Column('spot_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('premium', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('available_funds', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('is_affordable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('alternatives_considered', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['selected_instrument_id'], ['instruments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contract_selection_signal_created', 'contract_selection_logs', ['signal_id', sa.text('created_at DESC')])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('contract_selection_logs')
    op.drop_table('funds_snapshots')
    op.drop_table('system_health')
    op.drop_table('audit_logs')
    op.drop_table('ml_models')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_runs')
    op.drop_table('pnl_snapshots')
    op.drop_table('positions')
    op.drop_table('trades')
    op.drop_table('order_events')
    op.drop_table('orders')
    op.drop_table('risk_configs')
    op.drop_table('strategy_configs')
    op.drop_table('ml_predictions')
    op.drop_table('signal_decisions')
    op.drop_table('signals')
    op.drop_table('support_resistance')
    op.drop_table('market_regimes')
    op.drop_table('indicator_snapshots')
    op.drop_table('candles')
    op.drop_table('instruments')
    op.drop_table('brokers')
    op.drop_table('users')