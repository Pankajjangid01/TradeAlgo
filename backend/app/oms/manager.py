import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.config.settings import settings
from app.db.models import Order, OrderEvent, OrderStatus, OrderSide, OrderType, Trade, Position, PositionSide

logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    instrument_token: str
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[Decimal] = None
    trigger_price: Optional[Decimal] = None
    product_type: str = "MIS"
    validity: str = "DAY"
    tag: Optional[str] = None
    signal_id: Optional[int] = None


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class OMSManager:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.broker_adapters: Dict[str, Any] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.idempotency_keys: Dict[str, datetime] = {}

    def register_broker_adapter(self, broker_name: str, adapter: Any) -> None:
        self.broker_adapters[broker_name] = adapter

    def get_broker_adapter(self, broker_name: str) -> Any:
        return self.broker_adapters.get(broker_name)

    async def create_order(self, request: OrderRequest, broker_name: str = "angelone") -> OrderResult:
        """Create and submit a new order with idempotency."""
        idempotency_key = f"{request.symbol}_{request.side.value}_{request.quantity}_{request.price}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Check idempotency
        if idempotency_key in self.idempotency_keys:
            last_used = self.idempotency_keys[idempotency_key]
            if datetime.now() - last_used < timedelta(seconds=settings.OMS_CONFIG["idempotency_key_ttl_seconds"]):
                return OrderResult(
                    success=False,
                    error=f"Duplicate order detected (idempotency): {idempotency_key}"
                )
        
        self.idempotency_keys[idempotency_key] = datetime.now()

        # Create internal order record
        internal_id = str(uuid.uuid4())
        order = Order(
            internal_id=internal_id,
            idempotency_key=idempotency_key,
            instrument_id=0,  # Will be set after instrument lookup
            broker_id=0,  # Will be set after broker lookup
            order_type=request.order_type,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            trigger_price=request.trigger_price,
            status=OrderStatus.CREATED,
            product_type=request.product_type,
            validity=request.validity,
            tag=request.tag,
            signal_id=request.signal_id,
        )

        # Save to database
        async with self.db_session_factory() as session:
            session.add(order)
            await session.commit()
            await session.refresh(order)

        # Submit to broker
        result = await self.submit_order(order, broker_name)
        
        return OrderResult(
            success=result.success,
            order_id=order.internal_id,
            broker_order_id=result.broker_order_id,
            error=result.error,
            details=result.details
        )

    async def submit_order(self, order: Order, broker_name: str) -> OrderResult:
        """Submit order to broker."""
        adapter = self.get_broker_adapter(broker_name)
        if not adapter:
            return OrderResult(success=False, error=f"Broker adapter not found: {broker_name}")

        try:
            # Update status
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.now()
            await self._save_order_event(order, OrderStatus.CREATED, OrderStatus.SUBMITTED)

            # Prepare broker order params
            broker_params = self._prepare_broker_params(order, broker_name)
            
            # Submit
            response = await adapter.place_order(broker_params)
            
            if response.get("status") == "success":
                broker_order_id = response.get("data", {}).get("order_id", response.get("order_id"))
                
                order.broker_order_id = broker_order_id
                order.status = OrderStatus.ACKNOWLEDGED
                order.acknowledged_at = datetime.now()
                await self._save_order_event(order, OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED)
                
                # Track for fill updates
                self.pending_orders[broker_order_id] = order
                
                async with self.db_session_factory() as session:
                    session.add(order)
                    await session.commit()
                
                return OrderResult(
                    success=True,
                    order_id=order.internal_id,
                    broker_order_id=broker_order_id
                )
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = response.get("message", "Unknown error")
                await self._save_order_event(order, OrderStatus.SUBMITTED, OrderStatus.REJECTED)
                
                async with self.db_session_factory() as session:
                    session.add(order)
                    await session.commit()
                
                return OrderResult(
                    success=False,
                    error=order.error_message,
                    details=response
                )

        except Exception as e:
            logger.error(f"Order submission error: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
            await self._save_order_event(order, OrderStatus.SUBMITTED, OrderStatus.REJECTED)
            
            async with self.db_session_factory() as session:
                session.add(order)
                await session.commit()
            
            return OrderResult(success=False, error=str(e))

    def _prepare_broker_params(self, order: Order, broker_name: str) -> Dict[str, Any]:
        """Convert internal order to broker-specific parameters."""
        if broker_name == "angelone":
            return {
                "variety": "NORMAL",
                "tradingsymbol": order.instrument.symbol if hasattr(order, 'instrument') else "",
                "symboltoken": order.instrument.token if hasattr(order, 'instrument') else "",
                "transactiontype": order.side.value.upper(),
                "exchange": order.instrument.exchange if hasattr(order, 'instrument') else "NSE",
                "ordertype": order.order_type.value.upper(),
                "producttype": order.product_type,
                "duration": order.validity,
                "price": str(order.price) if order.price else "0",
                "triggerprice": str(order.trigger_price) if order.trigger_price else "0",
                "quantity": order.quantity,
            }
        elif broker_name == "flattrade":
            return {
                "symbol": order.instrument.symbol if hasattr(order, 'instrument') else "",
                "exchange": order.instrument.exchange if hasattr(order, 'instrument') else "NSE",
                "side": order.side.value.upper(),
                "order_type": order.order_type.value.upper(),
                "quantity": order.quantity,
                "price": str(order.price) if order.price else "0",
                "trigger_price": str(order.trigger_price) if order.trigger_price else "0",
                "product": order.product_type,
                "validity": order.validity,
            }
        return {}

    async def modify_order(self, order_id: str, new_price: Optional[Decimal] = None, 
                          new_quantity: Optional[int] = None, new_trigger_price: Optional[Decimal] = None) -> OrderResult:
        """Modify an existing order."""
        async with self.db_session_factory() as session:
            order = await session.get(Order, order_id)
            if not order:
                return OrderResult(success=False, error="Order not found")
            
            if order.status not in [OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED]:
                return OrderResult(success=False, error=f"Cannot modify order in status: {order.status}")
            
            adapter = self.get_broker_adapter("angelone")  # Default
            if not adapter:
                return OrderResult(success=False, error="No broker adapter")
            
            try:
                old_status = order.status
                order.status = OrderStatus.SUBMITTED  # Temporary
                
                params = {
                    "order_id": order.broker_order_id,
                    "price": str(new_price) if new_price else "0",
                    "quantity": new_quantity or order.quantity,
                    "trigger_price": str(new_trigger_price) if new_trigger_price else "0",
                }
                
                response = await adapter.modify_order(params)
                
                if response.get("status") == "success":
                    order.price = new_price or order.price
                    order.quantity = new_quantity or order.quantity
                    order.trigger_price = new_trigger_price or order.trigger_price
                    order.status = OrderStatus.ACKNOWLEDGED
                    await self._save_order_event(order, old_status, OrderStatus.ACKNOWLEDGED)
                    
                    await session.commit()
                    return OrderResult(success=True, order_id=order.internal_id)
                else:
                    order.status = old_status
                    return OrderResult(success=False, error=response.get("message"))
            except Exception as e:
                order.status = old_status
                return OrderResult(success=False, error=str(e))

    async def cancel_order(self, order_id: str) -> OrderResult:
        """Cancel an order."""
        async with self.db_session_factory() as session:
            order = await session.get(Order, order_id)
            if not order:
                return OrderResult(success=False, error="Order not found")
            
            if order.status not in [OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED, OrderStatus.SUBMITTED]:
                return OrderResult(success=False, error=f"Cannot cancel order in status: {order.status}")
            
            adapter = self.get_broker_adapter("angelone")
            if not adapter:
                return OrderResult(success=False, error="No broker adapter")
            
            try:
                old_status = order.status
                order.status = OrderStatus.CANCEL_PENDING
                await self._save_order_event(order, old_status, OrderStatus.CANCEL_PENDING)
                
                response = await adapter.cancel_order(order.broker_order_id)
                
                if response.get("status") == "success":
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = datetime.now()
                    await self._save_order_event(order, OrderStatus.CANCEL_PENDING, OrderStatus.CANCELLED)
                    
                    # Remove from pending
                    if order.broker_order_id in self.pending_orders:
                        del self.pending_orders[order.broker_order_id]
                    
                    await session.commit()
                    return OrderResult(success=True, order_id=order.internal_id)
                else:
                    order.status = old_status
                    return OrderResult(success=False, error=response.get("message"))
            except Exception as e:
                order.status = old_status
                return OrderResult(success=False, error=str(e))

    async def process_order_update(self, broker_order_id: str, update: Dict[str, Any]) -> None:
        """Process order update from broker websocket."""
        if broker_order_id not in self.pending_orders:
            return
        
        order = self.pending_orders[broker_order_id]
        async with self.db_session_factory() as session:
            order = await session.get(Order, order.id)
            if not order:
                return
            
            old_status = order.status
            
            # Parse broker update
            new_status = self._parse_broker_status(update.get("status", ""))
            filled_qty = update.get("filled_quantity", 0)
            avg_price = Decimal(str(update.get("average_price", 0))) if update.get("average_price") else None
            
            if new_status == OrderStatus.PARTIALLY_FILLED:
                order.filled_quantity = filled_qty
                order.average_price = avg_price
                order.status = OrderStatus.PARTIALLY_FILLED
                
                # Create trade record for partial fill
                if filled_qty > 0 and avg_price:
                    await self._create_trade_record(order, filled_qty, avg_price, update)
                
            elif new_status == OrderStatus.FILLED:
                order.filled_quantity = order.quantity
                order.average_price = avg_price
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now()
                
                # Create trade record
                if avg_price:
                    await self._create_trade_record(order, order.quantity, avg_price, update)
                
                # Create/update position
                await self._update_position(order)
                
                # Remove from pending
                del self.pending_orders[broker_order_id]
                
            elif new_status in [OrderStatus.REJECTED, OrderStatus.CANCELLED]:
                order.status = new_status
                if new_status == OrderStatus.CANCELLED:
                    order.cancelled_at = datetime.now()
                
                if broker_order_id in self.pending_orders:
                    del self.pending_orders[broker_order_id]
            
            await self._save_order_event(order, old_status, new_status)
            await session.commit()

    def _parse_broker_status(self, broker_status: str) -> OrderStatus:
        """Convert broker status to internal status."""
        status_map = {
            "OPEN": OrderStatus.ACKNOWLEDGED,
            "PENDING": OrderStatus.ACKNOWLEDGED,
            "PARTIAL": OrderStatus.PARTIALLY_FILLED,
            "COMPLETE": OrderStatus.FILLED,
            "REJECTED": OrderStatus.REJECTED,
            "CANCELLED": OrderStatus.CANCELLED,
            "EXPIRED": OrderStatus.EXPIRED,
        }
        return status_map.get(broker_status.upper(), OrderStatus.UNKNOWN)

    async def _create_trade_record(self, order: Order, quantity: int, price: Decimal, broker_data: Dict[str, Any]) -> None:
        """Create trade record from fill."""
        async with self.db_session_factory() as session:
            trade = Trade(
                order_id=order.id,
                signal_id=order.signal_id,
                instrument_id=order.instrument_id,
                broker_id=order.broker_id,
                side=order.side,
                quantity=quantity,
                price=price,
                trade_time=datetime.now(),
                broker_trade_id=broker_data.get("trade_id", f"{order.broker_order_id}_{quantity}"),
                commission=Decimal(str(broker_data.get("commission", 0))),
                stt=Decimal(str(broker_data.get("stt", 0))),
                exchange_txn=Decimal(str(broker_data.get("exchange_txn", 0))),
                gst=Decimal(str(broker_data.get("gst", 0))),
                sebi=Decimal(str(broker_data.get("sebi", 0))),
                stamp_duty=Decimal(str(broker_data.get("stamp_duty", 0))),
            )
            session.add(trade)
            await session.commit()

    async def _update_position(self, order: Order) -> None:
        """Update position after fill."""
        async with self.db_session_factory() as session:
            # Find existing position
            from sqlalchemy import select
            result = await session.execute(
                select(Position).where(
                    Position.instrument_id == order.instrument_id,
                    Position.is_open == True
                )
            )
            position = result.scalar_one_or_none()
            
            if position:
                # Update existing
                if position.side == PositionSide.LONG and order.side == OrderSide.BUY:
                    # Adding to long
                    total_qty = position.quantity + order.filled_quantity
                    position.average_price = (
                        (position.average_price * position.quantity) + 
                        (order.average_price * order.filled_quantity)
                    ) / total_qty
                    position.quantity = total_qty
                elif position.side == PositionSide.SHORT and order.side == OrderSide.SELL:
                    # Adding to short
                    total_qty = position.quantity + order.filled_quantity
                    position.average_price = (
                        (position.average_price * position.quantity) + 
                        (order.average_price * order.filled_quantity)
                    ) / total_qty
                    position.quantity = total_qty
                else:
                    # Reducing/closing
                    if order.filled_quantity >= position.quantity:
                        # Fully closed
                        position.is_open = False
                        position.closed_at = datetime.now()
                    else:
                        # Partially closed
                        position.quantity -= order.filled_quantity
            else:
                # New position
                position = Position(
                    instrument_id=order.instrument_id,
                    broker_id=order.broker_id,
                    signal_id=order.signal_id,
                    side=PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT,
                    quantity=order.filled_quantity,
                    average_price=order.average_price,
                    is_open=True,
                )
                session.add(position)
            
            position.updated_at = datetime.now()
            await session.commit()

    async def _save_order_event(self, order: Order, old_status: OrderStatus, new_status: OrderStatus) -> None:
        """Save order event to database."""
        async with self.db_session_factory() as session:
            event = OrderEvent(
                order_id=order.id,
                event_type=f"{old_status.value}_to_{new_status.value}",
                old_status=old_status,
                new_status=new_status,
                quantity=order.filled_quantity,
                price=order.average_price,
            )
            session.add(event)
            await session.commit()

    async def reconcile_positions(self, broker_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Reconcile internal positions with broker positions."""
        async with self.db_session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Position).where(Position.is_open == True)
            )
            internal_positions = {f"{p.instrument_id}_{p.side.value}": p for p in result.scalars().all()}
            
            discrepancies = []
            
            for bp in broker_positions:
                key = f"{bp['instrument_token']}_{bp['side']}"
                if key in internal_positions:
                    internal = internal_positions[key]
                    broker_qty = bp['quantity']
                    if internal.quantity != broker_qty:
                        discrepancies.append({
                            "type": "quantity_mismatch",
                            "instrument": key,
                            "internal_qty": internal.quantity,
                            "broker_qty": broker_qty,
                        })
                        # Update internal to match broker
                        internal.quantity = broker_qty
                        internal.updated_at = datetime.now()
                else:
                    discrepancies.append({
                        "type": "missing_in_internal",
                        "instrument": key,
                        "broker_qty": bp['quantity'],
                    })
            
            # Check for positions in internal but not in broker
            for key, pos in internal_positions.items():
                found = any(f"{bp['instrument_token']}_{bp['side']}" == key for bp in broker_positions)
                if not found:
                    discrepancies.append({
                        "type": "missing_in_broker",
                        "instrument": key,
                        "internal_qty": pos.quantity,
                    })
            
            await session.commit()
            
            return {
                "reconciled": True,
                "discrepancies": discrepancies,
                "internal_count": len(internal_positions),
                "broker_count": len(broker_positions),
            }


# Global instance (will be initialized in main.py)
oms_manager = None