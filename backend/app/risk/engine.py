import logging
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta, timezone

from app.config.settings import settings
from app.db.models import Position, Order, OrderStatus, PositionSide

IST = timezone(timedelta(hours=5, minutes=30))

logger = logging.getLogger(__name__)


class RiskCheckResult(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    WARNING = "warning"


@dataclass
class RiskCheck:
    result: RiskCheckResult
    reason: str
    details: Dict[str, Any]


@dataclass
class PositionSizeResult:
    quantity: int
    max_allowed_quantity: int
    risk_amount: Decimal
    limiting_factor: str  # "risk_budget", "available_funds", "lot_size", "max_exposure"
    checks_passed: List[str]
    checks_failed: List[str]


class RiskEngine:
    def __init__(self):
        self.config = settings.RISK_CONFIG
        self.options_config = settings.OPTIONS_CONFIG

    def check_pre_trade(
        self,
        signal_entry: Decimal,
        signal_stop: Decimal,
        signal_target: Decimal,
        direction: str,
        instrument_type: str,
        available_funds: Decimal,
        available_margin: Decimal,
        current_positions: List[Position],
        daily_pnl: Decimal,
        strategy_capital: Decimal,
        consecutive_losses: int,
        option_premium: Decimal,
        lot_size: int
    ) -> RiskCheck:
        """Comprehensive pre-trade risk check."""
        checks = []

        # 1. Daily loss limit
        max_daily_loss = strategy_capital * Decimal(str(self.config["max_daily_loss_pct"]))
        if daily_pnl <= -max_daily_loss:
            return RiskCheck(
                result=RiskCheckResult.BLOCK,
                reason=f"Daily loss limit reached: {daily_pnl} <= -{max_daily_loss}",
                details={"daily_pnl": str(daily_pnl), "max_daily_loss": str(max_daily_loss)}
            )
        checks.append("daily_loss_limit")

        # 2. Max positions
        open_positions = [p for p in current_positions if p.is_open]
        if len(open_positions) >= self.config["max_simultaneous_positions"]:
            return RiskCheck(
                result=RiskCheckResult.BLOCK,
                reason=f"Max positions reached: {len(open_positions)} >= {self.config['max_simultaneous_positions']}",
                details={"open_positions": len(open_positions), "max": self.config["max_simultaneous_positions"]}
            )
        checks.append("max_positions")

        # 3. Consecutive losses
        if consecutive_losses >= self.config["max_consecutive_losses"]:
            return RiskCheck(
                result=RiskCheckResult.BLOCK,
                reason=f"Consecutive losses limit: {consecutive_losses} >= {self.config['max_consecutive_losses']}",
                details={"consecutive_losses": consecutive_losses}
            )
        checks.append("consecutive_losses")

        # 4. Kill switch
        # This would come from system state
        checks.append("kill_switch")

        # 5. Risk per trade
        risk_per_trade_limit = strategy_capital * Decimal(str(self.config["initial_risk_per_trade_pct"]))
        risk_per_share = abs(signal_entry - signal_stop)
        if risk_per_share <= 0:
            return RiskCheck(
                result=RiskCheckResult.BLOCK,
                reason="Invalid risk per share (stop >= entry)",
                details={"entry": str(signal_entry), "stop": str(signal_stop)}
            )
        checks.append("risk_per_trade")

        # 6. Minimum R:R
        reward_per_share = abs(signal_target - signal_entry)
        rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else Decimal("0")
        if rr_ratio < Decimal("1.5"):
            return RiskCheck(
                result=RiskCheckResult.BLOCK,
                reason=f"Insufficient R:R ratio: {rr_ratio:.2f} < 1.5",
                details={"rr_ratio": str(rr_ratio)}
            )
        checks.append("rr_ratio")

        # 7. Spread check (minimum risk vs spread)
        min_spread = max(Decimal("0.50"), signal_entry * Decimal("0.001"))
        if risk_per_share < min_spread:
            return RiskCheck(
                result=RiskCheckResult.BLOCK,
                reason=f"Stop too tight: risk {risk_per_share} < min spread {min_spread}",
                details={"risk_per_share": str(risk_per_share), "min_spread": str(min_spread)}
            )
        checks.append("spread_check")

        return RiskCheck(
            result=RiskCheckResult.PASS,
            reason="All pre-trade risk checks passed",
            details={"checks": checks}
        )

    def calculate_position_size(
        self,
        signal_entry: Decimal,
        signal_stop: Decimal,
        signal_target: Decimal,
        direction: str,
        instrument_type: str,
        available_funds: Decimal,
        available_margin: Decimal,
        current_positions: List[Position],
        strategy_capital: Decimal,
        option_premium: Decimal,
        lot_size: int,
        estimated_charges: Decimal = Decimal("0")
    ) -> PositionSizeResult:
        """Calculate position size respecting all constraints."""
        checks_passed = []
        checks_failed = []

        # 1. Risk budget calculation
        risk_budget = strategy_capital * Decimal(str(self.config["initial_risk_per_trade_pct"]))
        risk_per_unit = abs(signal_entry - signal_stop)
        
        if risk_per_unit <= 0:
            return PositionSizeResult(
                quantity=0,
                max_allowed_quantity=0,
                risk_amount=Decimal("0"),
                limiting_factor="invalid_risk",
                checks_passed=[],
                checks_failed=["risk_per_unit <= 0"]
            )

        qty_by_risk = int(risk_budget / risk_per_unit)
        qty_by_risk = (qty_by_risk // lot_size) * lot_size
        checks_passed.append("risk_budget")

        # 2. Available funds (for options, premium * qty + charges)
        if instrument_type in ["option_ce", "option_pe"]:
            # For options buying, need premium * quantity + charges
            total_cost_per_lot = option_premium * lot_size + estimated_charges
            max_lots_by_funds = int(available_funds / total_cost_per_lot) if total_cost_per_lot > 0 else 0
            qty_by_funds = max_lots_by_funds * lot_size
        else:
            # For futures/stocks, use margin
            qty_by_funds = int(available_margin / (signal_entry * lot_size * Decimal("0.1"))) * lot_size  # ~10% margin
        
        qty_by_funds = max(0, qty_by_funds)
        checks_passed.append("available_funds")

        # 3. Max exposure (total position value)
        max_exposure = strategy_capital * Decimal("0.2")  # 20% max single position
        current_exposure = sum(
            float(p.quantity) * float(p.average_price) for p in current_positions if p.is_open
        )
        remaining_exposure = max_exposure - Decimal(str(current_exposure))
        qty_by_exposure = int(remaining_exposure / signal_entry / lot_size) * lot_size if signal_entry > 0 else 0
        qty_by_exposure = max(0, qty_by_exposure)
        checks_passed.append("max_exposure")

        # 4. Lot size constraint
        min_qty = lot_size
        checks_passed.append("lot_size")

        # Determine final quantity (minimum of all constraints)
        quantities = {
            "risk_budget": qty_by_risk,
            "available_funds": qty_by_funds,
            "max_exposure": qty_by_exposure,
        }

        # Filter valid quantities
        valid_quantities = {k: v for k, v in quantities.items() if v >= min_qty}
        
        if not valid_quantities:
            return PositionSizeResult(
                quantity=0,
                max_allowed_quantity=0,
                risk_amount=Decimal("0"),
                limiting_factor="insufficient_funds_or_risk",
                checks_passed=checks_passed,
                checks_failed=["all constraints resulted in qty < lot_size"]
            )

        final_qty = min(valid_quantities.values())
        limiting_factor = min(valid_quantities, key=valid_quantities.get)
        risk_amount = risk_per_unit * final_qty

        return PositionSizeResult(
            quantity=final_qty,
            max_allowed_quantity=final_qty,
            risk_amount=risk_amount,
            limiting_factor=limiting_factor,
            checks_passed=checks_passed,
            checks_failed=checks_failed
        )

    def calculate_stop_target(
        self,
        entry_price: Decimal,
        method: str,
        atr: Decimal,
        range_low: Optional[Decimal] = None,
        range_mid: Optional[Decimal] = None,
        range_high: Optional[Decimal] = None,
        custom_stop: Optional[Decimal] = None,
        target_r: float = 2.0
    ) -> Tuple[Decimal, Decimal]:
        """Calculate stop loss and target based on method."""
        entry_f = float(entry_price)
        atr_f = float(atr) if atr else 0

        if method == "or_mid" and range_mid:
            stop = float(range_mid)
        elif method == "or_low" and range_low:
            stop = float(range_low)
        elif method == "atr" and atr_f > 0:
            stop = entry_f - (1.5 * atr_f)
        elif method == "percent":
            stop = entry_f * 0.99
        elif method == "custom" and custom_stop:
            stop = float(custom_stop)
        else:
            stop = entry_f * 0.99  # Default 1%

        stop = round(stop, 2)

        # Validate stop
        if stop >= entry_f:
            stop = entry_f * 0.99

        risk_per_share = entry_f - stop
        if risk_per_share <= 0:
            risk_per_share = entry_f * 0.01
            stop = entry_f - risk_per_share

        # Check minimum spread
        min_spread = max(0.50, entry_f * 0.001)
        if risk_per_share < min_spread:
            risk_per_share = min_spread
            stop = entry_f - risk_per_share

        target = round(entry_f + (target_r * risk_per_share), 2)

        return Decimal(str(stop)), Decimal(str(target))

    def check_emergency_conditions(
        self,
        daily_pnl: Decimal,
        strategy_capital: Decimal,
        open_positions: List[Position],
        broker_connected: bool,
        data_fresh: bool,
        kill_switch: bool
    ) -> Dict[str, Any]:
        """Check emergency conditions and return actions needed."""
        actions = []
        triggered = False

        max_daily_loss = strategy_capital * Decimal(str(self.config["max_daily_loss_pct"]))
        
        if daily_pnl <= -max_daily_loss:
            actions.append("BLOCK_NEW_ENTRIES")
            actions.append("CANCEL_PENDING_ORDERS")
            triggered = True

        if not broker_connected:
            actions.append("EMERGENCY_MONITORING")
            triggered = True

        if not data_fresh:
            actions.append("BLOCK_NEW_ENTRIES")
            triggered = True

        if kill_switch:
            actions.append("BLOCK_NEW_ENTRIES")
            actions.append("CANCEL_PENDING_ORDERS")
            actions.append("FLATTEN_POSITIONS")
            triggered = True

        # Check position mismatch
        # This would compare internal positions with broker positions

        return {
            "triggered": triggered,
            "actions": actions,
            "daily_pnl": str(daily_pnl),
            "max_daily_loss": str(max_daily_loss),
            "broker_connected": broker_connected,
            "data_fresh": data_fresh,
            "kill_switch": kill_switch
        }

    def validate_exit_order(
        self,
        position: Position,
        exit_price: Decimal,
        exit_reason: str
    ) -> RiskCheck:
        """Validate exit order before submission."""
        if not position.is_open:
            return RiskCheck(
                result=RiskCheckResult.BLOCK,
                reason="Position not open",
                details={"position_id": position.id}
            )

        # Check if exit price is reasonable
        if position.side == PositionSide.LONG:
            if exit_price > position.average_price * Decimal("1.1"):  # 10% above avg
                return RiskCheck(
                    result=RiskCheckResult.WARNING,
                    reason="Exit price significantly above average",
                    details={"exit_price": str(exit_price), "avg_price": str(position.average_price)}
                )
        else:
            if exit_price < position.average_price * Decimal("0.9"):
                return RiskCheck(
                    result=RiskCheckResult.WARNING,
                    reason="Exit price significantly below average",
                    details={"exit_price": str(exit_price), "avg_price": str(position.average_price)}
                )

        return RiskCheck(
            result=RiskCheckResult.PASS,
            reason="Exit order validated",
            details={"exit_reason": exit_reason}
        )

    # ------------------------------------------------------------------
    # Trailing stop-loss (reference repo pattern: trail below high-water mark)
    # ------------------------------------------------------------------

    def calculate_trailing_stop(
        self,
        position: Position,
        current_price: Decimal,
        trailing_pct: Optional[float] = None,
    ) -> Tuple[Optional[Decimal], bool]:
        """
        Calculate trailing stop-loss for a position.

        Returns (new_stop_price, should_trigger).
        - Trails below the position's high-water mark by trailing_pct.
        - Only moves the stop UP (for longs) or DOWN (for shorts), never against the position.
        - Returns should_trigger=True if current price breaches the trailing stop.
        """
        pct = trailing_pct if trailing_pct is not None else self.config.get("trailing_stop_pct", 0.15)

        # Get high-water mark from position metadata
        high_water = position.metadata.get("high_water_mark") if position.metadata else None
        if high_water is None:
            high_water = position.average_price
        else:
            high_water = Decimal(str(high_water))

        # Update high-water mark if current price is better
        if position.side == PositionSide.LONG:
            if current_price > high_water:
                high_water = current_price
            # Trailing stop below high-water mark
            new_stop = high_water * (1 - Decimal(str(pct)))
            # Stop should never move down
            if position.stop_loss and new_stop < position.stop_loss:
                new_stop = position.stop_loss
            # Trigger if price hits the stop
            should_trigger = current_price <= new_stop
        else:  # SHORT
            if current_price < high_water:
                high_water = current_price
            new_stop = high_water * (1 + Decimal(str(pct)))
            if position.stop_loss and new_stop > position.stop_loss:
                new_stop = position.stop_loss
            should_trigger = current_price >= new_stop

        return Decimal(str(round(float(new_stop), 2))), should_trigger

    def update_high_water_mark(self, position: Position, current_price: Decimal) -> Decimal:
        """Update and return the high-water mark for a position."""
        high_water = position.metadata.get("high_water_mark") if position.metadata else None
        if high_water is None:
            high_water = position.average_price
        else:
            high_water = Decimal(str(high_water))

        if position.side == PositionSide.LONG:
            high_water = max(high_water, current_price)
        else:
            high_water = min(high_water, current_price)

        if position.metadata is None:
            position.metadata = {}
        position.metadata["high_water_mark"] = str(high_water)
        return high_water

    # ------------------------------------------------------------------
    # Intraday square-off (SEBI-compliant: close before market close)
    # ------------------------------------------------------------------

    def check_square_off(
        self,
        current_time_ist: datetime,
        square_off_hour: int = 15,
        square_off_minute: int = 15,
        no_new_entry_hour: int = 15,
        no_new_entry_minute: int = 0,
    ) -> Dict[str, Any]:
        """
        Check if intraday square-off is due.

        Returns:
            square_off: True if positions should be squared off
            no_new_entry: True if no new entries should be taken
            minutes_until_close: Minutes until square-off time
        """
        now = current_time_ist if current_time_ist.tzinfo else current_time_ist.replace(tzinfo=IST)
        square_off_time = now.replace(hour=square_off_hour, minute=square_off_minute, second=0, microsecond=0)
        no_new_entry_time = now.replace(hour=no_new_entry_hour, minute=no_new_entry_minute, second=0, microsecond=0)

        square_off = now >= square_off_time
        no_new_entry = now >= no_new_entry_time

        if square_off_time > now:
            minutes_until_close = int((square_off_time - now).total_seconds() / 60)
        else:
            minutes_until_close = 0

        return {
            "square_off": square_off,
            "no_new_entry": no_new_entry,
            "minutes_until_square_off": minutes_until_close,
            "square_off_time": square_off_time.isoformat(),
            "current_time": now.isoformat(),
        }

    def check_daily_drawdown_halt(
        self,
        daily_pnl: Decimal,
        start_of_day_equity: Decimal,
        max_drawdown_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Check if daily drawdown limit has been breached.

        Returns:
            halted: True if new entries should be halted
            drawdown_pct: Current drawdown as percentage
        """
        pct = max_drawdown_pct if max_drawdown_pct is not None else self.config.get("max_daily_loss_pct", 0.03)
        max_loss = start_of_day_equity * Decimal(str(pct))
        drawdown_pct = (abs(daily_pnl) / start_of_day_equity * 100) if start_of_day_equity > 0 else Decimal("0")
        halted = daily_pnl <= -max_loss

        return {
            "halted": halted,
            "drawdown_pct": float(drawdown_pct),
            "max_drawdown_pct": pct,
            "daily_pnl": str(daily_pnl),
            "max_loss_allowed": str(max_loss),
        }


# Singleton instance
risk_engine = RiskEngine()