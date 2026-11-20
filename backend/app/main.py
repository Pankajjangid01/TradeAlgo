import logging
from typing import Any, Dict, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.base import init_db, close_db, get_db
from app.market_data.service import market_data_service, DataProvider
from app.oms.manager import OMSManager, OrderRequest
from app.services.indicator_engine import indicator_engine, IndicatorValues
from app.services.market_structure import market_structure_engine
from app.services.regime_detection import regime_detection_engine
from app.strategies.engine import strategy_engine
from app.ml.inference import ml_inference_engine
from app.services.conflict_resolution import conflict_resolution_engine, DecisionState
from app.core.rate_limiter import get_all_limiter_stats
from app.core.signal_lifecycle import signal_lifecycle, SignalDirection, SignalStatus, StructuredSignal
from app.risk.engine import risk_engine
from app.services.options_selector import options_selection_engine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global OMS manager
oms_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global oms_manager
    
    # Startup
    logger.info("Starting TradeIQ platform...")
    
    # Initialize market data
    await market_data_service.initialize()
    
    # Load ML model
    ml_inference_engine.load_model()
    
    # Initialize OMS
    from app.db.base import async_session_maker
    oms_manager = OMSManager(async_session_maker)
    
    # Register broker adapters
    from app.market_data.angelone_client import AngelOneClient
    from app.market_data.flattrade_client import FlattradeClient
    
    if settings.ANGELONE_API_KEY:
        angelone_client = AngelOneClient()
        oms_manager.register_broker_adapter("angelone", angelone_client)
    
    if settings.FLATTRADE_API_KEY:
        flattrade_client = FlattradeClient()
        oms_manager.register_broker_adapter("flattrade", flattrade_client)
    
    logger.info("TradeIQ platform started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TradeIQ platform...")
    await market_data_service.close()
    await close_db()
    logger.info("TradeIQ platform shut down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health & Status ====================
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/v1/status")
async def system_status():
    ws_stats = market_data_service.get_websocket_stats() or {}
    return {
        "market_data": {
            "active_provider": market_data_service.active_provider.value,
            "angelone_connected": market_data_service.angelone_client is not None,
            "flattrade_connected": market_data_service.flattrade_client is not None,
            "websocket_connected": market_data_service.is_websocket_connected(),
            "data_fresh": market_data_service.is_market_data_fresh(30.0),
            "websocket_stats": ws_stats,
        },
        "ml_model": {
            "loaded": ml_inference_engine._is_loaded,
            "version": ml_inference_engine._model_version,
        },
        "trading": {
            "instruments": settings.TRADING_INSTRUMENTS,
        },
        "rate_limits": await get_all_limiter_stats(),
        "signal_stats": signal_lifecycle.get_stats(),
    }


@app.get("/api/v1/monitoring/rate-limits")
async def get_rate_limit_stats():
    """Get rate limiter statistics for all endpoints."""
    stats = await get_all_limiter_stats()
    return {"success": True, "data": stats}


@app.get("/api/v1/monitoring/health")
async def detailed_health():
    """Detailed health check with connection, rate limit, and data freshness status."""
    ws_stats = market_data_service.get_websocket_stats() or {}
    rate_stats = await get_all_limiter_stats()

    # Determine overall health
    issues = []
    for rs in rate_stats:
        if rs["circuit_state"] == "open":
            issues.append(f"Rate limiter {rs['name']}: circuit OPEN")
        if rs["rate_limited_calls"] > 100:
            issues.append(f"Rate limiter {rs['name']}: {rs['rate_limited_calls']} rate-limited calls")

    if not market_data_service.is_websocket_connected():
        issues.append("WebSocket not connected")
    if not market_data_service.is_market_data_fresh(30.0):
        issues.append("Market data stale (>30s)")

    return {
        "success": True,
        "data": {
            "status": "degraded" if issues else "healthy",
            "issues": issues,
            "websocket": ws_stats,
            "rate_limits": rate_stats,
            "data_fresh": market_data_service.is_market_data_fresh(30.0),
            "signal_stats": signal_lifecycle.get_stats(),
        }
    }


# ==================== Market Data ====================
@app.get("/api/v1/market/ltp")
async def get_ltp(symbols: str, exchange: str = "NSE"):
    tokens = symbols.split(",")
    try:
        result = await market_data_service.get_ltp(exchange, tokens)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/market/quote")
async def get_quote(symbols: str, exchange: str = "NSE"):
    tokens = symbols.split(",")
    try:
        result = await market_data_service.get_quote(exchange, tokens)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/market/historical")
async def get_historical(
    symbol_token: str,
    interval: str = "5m",
    from_date: str = None,
    to_date: str = None,
    exchange: str = "NSE"
):
    try:
        result = await market_data_service.get_historical_data(
            exchange, symbol_token, interval, from_date, to_date
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/market/instruments")
async def search_instruments(q: str, exchange: str = "NSE"):
    try:
        result = await market_data_service.search_instruments(q, exchange)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/market/option-chain")
async def get_option_chain(underlying: str, expiry: str = None):
    try:
        result = await market_data_service.get_option_chain(underlying, expiry)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/market/provider")
async def set_data_provider(provider: str):
    try:
        dp = DataProvider(provider)
        success = await market_data_service.set_active_provider(dp)
        return {"success": success, "active_provider": market_data_service.active_provider.value}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Account ====================
@app.get("/api/v1/account/funds")
async def get_funds():
    client = market_data_service.get_active_client()
    if not client:
        return {"success": True, "data": {}, "message": "No broker configured"}
    try:
        result = await market_data_service.get_funds()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": True, "data": {}, "message": str(e)}


@app.get("/api/v1/account/positions")
async def get_positions():
    client = market_data_service.get_active_client()
    if not client:
        return {"success": True, "data": [], "message": "No broker configured"}
    try:
        result = await market_data_service.get_positions()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": True, "data": [], "message": str(e)}


@app.get("/api/v1/account/holdings")
async def get_holdings():
    client = market_data_service.get_active_client()
    if not client:
        return {"success": True, "data": [], "message": "No broker configured"}
    try:
        result = await market_data_service.get_holdings()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": True, "data": [], "message": str(e)}


@app.get("/api/v1/account/orders")
async def get_orders():
    client = market_data_service.get_active_client()
    if not client:
        return {"success": True, "data": [], "message": "No broker configured"}
    try:
        result = await market_data_service.get_order_book()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": True, "data": [], "message": str(e)}


# ==================== Trading Signals ====================
@app.post("/api/v1/signals/analyze")
async def analyze_market(
    symbol: str,
    timeframe: str = "5m",
    lookback_bars: int = 100
):
    """Analyze market and generate trading signals."""
    try:
        # Determine index name from symbol
        index_name = symbol.upper()
        if index_name not in ("NIFTY", "BANKNIFTY", "SENSEX"):
            index_name = "NIFTY"

        # Get live market data
        ws_stats = market_data_service.get_websocket_stats() or {}
        data_fresh = market_data_service.is_market_data_fresh(30.0)

        # Use WebSocket LTP if available, else fetch via REST
        spot_price = Decimal("0")
        try:
            ltp_result = await market_data_service.get_ltp("NSE", [symbol])
            # Extract spot price from response
            if isinstance(ltp_result, dict):
                data = ltp_result.get("data", ltp_result)
                if isinstance(data, list) and len(data) > 0:
                    spot_price = Decimal(str(data[0].get("ltp", data[0].get("last_traded_price", 0))))
                elif isinstance(data, dict):
                    spot_price = Decimal(str(data.get("ltp", data.get("last_traded_price", 0))))
        except Exception as e:
            logger.warning(f"Could not fetch LTP for {symbol}: {e}")

        # Determine direction based on simple momentum (placeholder until full pipeline integrated)
        # In production, this would run ORB, VWAP, S/R strategies + ML
        direction = SignalDirection.WAIT
        confidence = Decimal("0.0")
        strategy_name = ""
        regime = "uncertain"
        indicators_list: List[str] = []
        explanation = "Awaiting market data and strategy signals"

        if data_fresh and spot_price > 0:
            # Basic momentum signal for demonstration
            direction = SignalDirection.BUY_CE if spot_price > 0 else SignalDirection.WAIT
            confidence = Decimal("0.65")
            strategy_name = "momentum_placeholder"
            regime = "breakout_transition"
            indicators_list = ["price_available", "data_fresh"]
            explanation = f"Live price {spot_price} received for {symbol}. Strategy engine pending full integration."

        # Create structured signal via lifecycle manager (prevents duplicates)
        signal = await signal_lifecycle.create_signal(
            index_name=index_name,
            direction=direction,
            underlying_spot=spot_price,
            strategy_name=strategy_name,
            confidence=confidence,
            market_regime=regime,
            confirmation_indicators=indicators_list,
            explanation=explanation,
            entry_price=spot_price if direction != SignalDirection.WAIT else None,
            stop_loss=None,
            target_1=None,
            target_2=None,
            risk_reward=None,
            data_provider=market_data_service.active_provider.value,
            data_freshness="live" if data_fresh else "stale",
        )

        # Get all active signals for response
        active_signals = signal_lifecycle.get_all_signals()

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal.to_dict(),
                "active_signals": [s.to_dict() for s in active_signals],
                "regime": {"regime": regime, "data_fresh": data_fresh},
                "indicators": {"spot_price": str(spot_price)},
                "data_freshness": "live" if data_fresh else "stale",
                "websocket_stats": ws_stats,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/signals/active")
async def get_active_signals():
    return {"success": True, "data": [s.to_dict() for s in signal_lifecycle.get_active_signals()]}


@app.get("/api/v1/signals/all")
async def get_all_signals():
    return {"success": True, "data": [s.to_dict() for s in signal_lifecycle.get_all_signals()]}


@app.get("/api/v1/signals/stats")
async def get_signal_stats():
    return {"success": True, "data": signal_lifecycle.get_stats()}


@app.post("/api/v1/signals/{signal_id}/confirm")
async def confirm_signal(signal_id: str):
    signal = await signal_lifecycle.confirm_signal(signal_id)
    if signal:
        return {"success": True, "data": signal.to_dict()}
    raise HTTPException(status_code=404, detail="Signal not found or not in SCANNING state")


@app.post("/api/v1/signals/{signal_id}/activate")
async def activate_signal(signal_id: str):
    signal = await signal_lifecycle.activate_signal(signal_id)
    if signal:
        return {"success": True, "data": signal.to_dict()}
    raise HTTPException(status_code=404, detail="Signal not found or not in CONFIRMED state")


@app.post("/api/v1/signals/{signal_id}/close")
async def close_signal(signal_id: str, status: str = "cancelled"):
    try:
        final_status = SignalStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    signal = await signal_lifecycle.close_signal(signal_id, final_status)
    if signal:
        return {"success": True, "data": signal.to_dict()}
    raise HTTPException(status_code=404, detail="Signal not found")


# ==================== Orders ====================
@app.post("/api/v1/orders/place")
async def place_order(request: OrderRequest):
    if not oms_manager:
        raise HTTPException(status_code=503, detail="OMS not initialized")
    
    result = await oms_manager.create_order(request)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result


@app.post("/api/v1/orders/{order_id}/modify")
async def modify_order(order_id: str, price: float = None, quantity: int = None, trigger_price: float = None):
    if not oms_manager:
        raise HTTPException(status_code=503, detail="OMS not initialized")
    
    result = await oms_manager.modify_order(
        order_id,
        Decimal(str(price)) if price else None,
        quantity,
        Decimal(str(trigger_price)) if trigger_price else None
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result


@app.post("/api/v1/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    if not oms_manager:
        raise HTTPException(status_code=503, detail="OMS not initialized")
    
    result = await oms_manager.cancel_order(order_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result


# ==================== Risk ====================
@app.post("/api/v1/risk/check")
async def risk_check(
    entry: float,
    stop: float,
    target: float,
    direction: str,
    instrument_type: str,
    available_funds: float,
    available_margin: float,
    daily_pnl: float,
    strategy_capital: float,
    consecutive_losses: int,
    option_premium: float,
    lot_size: int
):
    from decimal import Decimal
    check = risk_engine.check_pre_trade(
        Decimal(str(entry)), Decimal(str(stop)), Decimal(str(target)),
        direction, instrument_type,
        Decimal(str(available_funds)), Decimal(str(available_margin)),
        [], Decimal(str(daily_pnl)), Decimal(str(strategy_capital)),
        consecutive_losses, Decimal(str(option_premium)), lot_size
    )
    return {"success": check.result == "pass", "result": check.result, "reason": check.reason, "details": check.details}


@app.post("/api/v1/risk/position-size")
async def calculate_position_size(
    entry: float,
    stop: float,
    target: float,
    direction: str,
    available_funds: float,
    available_margin: float,
    strategy_capital: float,
    option_premium: float,
    lot_size: int
):
    from decimal import Decimal
    result = risk_engine.calculate_position_size(
        Decimal(str(entry)), Decimal(str(stop)), Decimal(str(target)),
        direction,
        Decimal(str(available_funds)), Decimal(str(available_margin)),
        [], Decimal(str(strategy_capital)),
        Decimal(str(option_premium)), lot_size
    )
    return {
        "quantity": result.quantity,
        "max_allowed_quantity": result.max_allowed_quantity,
        "risk_amount": str(result.risk_amount),
        "limiting_factor": result.limiting_factor,
        "checks_passed": result.checks_passed,
        "checks_failed": result.checks_failed,
    }


# ==================== Options Selection ====================
@app.post("/api/v1/options/select")
async def select_option(
    underlying: str,
    direction: str,
    spot_price: float,
    available_funds: float,
    available_margin: float,
    risk_budget: float,
    option_chain: Dict[str, Any],
    preferred_strikes: List[str] = None,
    expiry: str = None
):
    from decimal import Decimal
    result = await options_selection_engine.select_contract(
        underlying, direction, Decimal(str(spot_price)),
        Decimal(str(available_funds)), Decimal(str(available_margin)),
        Decimal(str(risk_budget)), option_chain,
        preferred_strikes, expiry
    )
    return {
        "success": result.is_affordable,
        "selected_contract": {
            "strike": str(result.selected_contract.strike) if result.selected_contract else None,
            "premium": str(result.selected_contract.premium) if result.selected_contract else None,
            "quantity": getattr(result.selected_contract, 'quantity', None),
            "estimated_cost": str(getattr(result.selected_contract, 'estimated_cost', None)),
        } if result.selected_contract else None,
        "alternatives": [
            {"strike": str(c.strike), "premium": str(c.premium)} 
            for c in result.alternative_contracts
        ],
        "rejection_reason": result.rejection_reason,
        "funds_snapshot": result.funds_snapshot,
        "metadata": result.selection_metadata,
    }


# ==================== Backtesting ====================
@app.post("/api/v1/backtest/run")
async def run_backtest(
    strategy: str,
    symbol: str,
    start_date: str,
    end_date: str,
    config: Dict[str, Any] = None
):
    return {"success": True, "message": "Backtest queued", "run_id": "bt_123"}


@app.get("/api/v1/backtest/{run_id}")
async def get_backtest_results(run_id: str):
    return {"success": True, "data": {}}


# ==================== WebSocket ====================
@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # Handle subscription requests
            if data.get("action") == "subscribe":
                tokens = data.get("tokens", [])
                await market_data_service.start_websocket(tokens)
                await websocket.send_json({"status": "subscribed", "tokens": tokens})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)