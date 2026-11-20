import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

from app.config.settings import settings
from app.db.models import Instrument, InstrumentType

logger = logging.getLogger(__name__)


@dataclass
class OptionContract:
    instrument: Instrument
    strike: Decimal
    option_type: str  # CE or PE
    premium: Decimal
    bid: Decimal
    ask: Decimal
    spread_pct: Decimal
    oi: int
    volume: int
    iv: Optional[Decimal] = None
    delta: Optional[Decimal] = None


@dataclass
class StrikeSelectionResult:
    selected_contract: Optional[OptionContract]
    alternative_contracts: List[OptionContract]
    is_affordable: bool
    rejection_reason: Optional[str]
    funds_snapshot: Dict[str, Any]
    selection_metadata: Dict[str, Any]


class OptionsSelectionEngine:
    def __init__(self):
        self.config = settings.OPTIONS_CONFIG
        self.risk_config = settings.RISK_CONFIG

    async def select_contract(
        self,
        underlying: str,  # NIFTY or SENSEX
        direction: str,   # bullish -> CE, bearish -> PE
        spot_price: Decimal,
        available_funds: Decimal,
        available_margin: Decimal,
        strategy_risk_budget: Decimal,
        option_chain: Dict[str, Any],
        preferred_strikes: Optional[List[str]] = None,
        expiry: Optional[str] = None,
        lot_size: Optional[int] = None
    ) -> StrikeSelectionResult:
        """Select the best option contract based on capital, liquidity, and strategy."""
        
        # Determine option type
        option_type = "CE" if direction == "bullish" else "PE"
        
        # Get lot size
        if lot_size is None:
            lot_size = self.config["lot_sizes"].get(underlying, 75)
        
        # Parse option chain
        contracts = self._parse_option_chain(option_chain, underlying, option_type, expiry)
        
        if not contracts:
            return StrikeSelectionResult(
                selected_contract=None,
                alternative_contracts=[],
                is_affordable=False,
                rejection_reason="No valid option contracts found in chain",
                funds_snapshot={
                    "available_funds": str(available_funds),
                    "available_margin": str(available_margin),
                },
                selection_metadata={}
            )

        # Filter by liquidity and quality
        filtered = self._filter_contracts(contracts)
        
        if not filtered:
            return StrikeSelectionResult(
                selected_contract=None,
                alternative_contracts=[],
                is_affordable=False,
                rejection_reason="No contracts meet liquidity/spread requirements",
                funds_snapshot={
                    "available_funds": str(available_funds),
                    "available_margin": str(available_margin),
                },
                selection_metadata={"total_contracts": len(contracts), "filtered": 0}
            )

        # Rank by preference (ATM, OTM1, ITM1, etc.)
        ranked = self._rank_contracts(filtered, spot_price, preferred_strikes or self.config["preferred_strikes"])

        # Check affordability for each candidate
        selected = None
        alternatives = []
        
        for contract in ranked:
            # Calculate quantity and cost
            qty, cost, charges = self._calculate_quantity_and_cost(
                contract, available_funds, available_margin, 
                strategy_risk_budget, lot_size
            )
            
            if qty >= lot_size:
                selected = contract
                selected.quantity = qty
                selected.estimated_cost = cost
                selected.estimated_charges = charges
                break
            else:
                alternatives.append({
                    "contract": contract,
                    "max_qty": qty,
                    "reason": "Insufficient funds for minimum lot" if qty < lot_size else "Risk budget exceeded"
                })

        if not selected:
            return StrikeSelectionResult(
                selected_contract=None,
                alternative_contracts=[a["contract"] for a in alternatives],
                is_affordable=False,
                rejection_reason="INSUFFICIENT_ELIGIBLE_CAPITAL: No affordable contract meets risk/funds requirements",
                funds_snapshot={
                    "available_funds": str(available_funds),
                    "available_margin": str(available_margin),
                    "strategy_risk_budget": str(strategy_risk_budget),
                },
                selection_metadata={
                    "total_candidates": len(ranked),
                    "alternatives_considered": len(alternatives),
                    "lot_size": lot_size,
                }
            )

        # Final validation
        final_check = self._final_validation(selected, available_funds, strategy_risk_budget, lot_size)
        if not final_check["valid"]:
            return StrikeSelectionResult(
                selected_contract=None,
                alternative_contracts=[a["contract"] for a in alternatives],
                is_affordable=False,
                rejection_reason=final_check["reason"],
                funds_snapshot={
                    "available_funds": str(available_funds),
                    "available_margin": str(available_margin),
                },
                selection_metadata={}
            )

        return StrikeSelectionResult(
            selected_contract=selected,
            alternative_contracts=[a["contract"] for a in alternatives[:3]],
            is_affordable=True,
            rejection_reason=None,
            funds_snapshot={
                "available_funds": str(available_funds),
                "available_margin": str(available_margin),
                "strategy_risk_budget": str(strategy_risk_budget),
                "selected_qty": selected.quantity,
                "estimated_cost": str(selected.estimated_cost),
                "estimated_charges": str(selected.estimated_charges),
            },
            selection_metadata={
                "spot_price": str(spot_price),
                "selected_strike": str(selected.strike),
                "selected_premium": str(selected.premium),
                "spread_pct": str(selected.spread_pct),
                "oi": selected.oi,
                "volume": selected.volume,
                "lot_size": lot_size,
                "strategy": direction,
            }
        )

    def _parse_option_chain(
        self, chain: Dict[str, Any], underlying: str, option_type: str, expiry: Optional[str]
    ) -> List[OptionContract]:
        """Parse option chain data into contract objects."""
        contracts = []
        
        try:
            # Handle different chain formats (Angel One, Flattrade, NSE)
            records = chain.get("data", chain.get("records", chain.get("optionChain", [])))
            
            for item in records:
                strike = item.get("strikePrice", item.get("strike", 0))
                if not strike:
                    continue
                
                strike_decimal = Decimal(str(strike))
                
                # Get option data
                opt_data = item.get(option_type, item.get(option_type.lower(), {}))
                if not opt_data:
                    continue
                
                premium = Decimal(str(opt_data.get("lastPrice", opt_data.get("ltp", 0))))
                bid = Decimal(str(opt_data.get("bidprice", opt_data.get("bid", opt_data.get("buyPrice", 0)))))
                ask = Decimal(str(opt_data.get("askPrice", opt_data.get("ask", opt_data.get("sellPrice", 0)))))
                oi = int(opt_data.get("openInterest", opt_data.get("oi", 0)))
                volume = int(opt_data.get("totalTradedVolume", opt_data.get("volume", 0)))
                iv = Decimal(str(opt_data.get("impliedVolatility", opt_data.get("iv", 0)))) if opt_data.get("impliedVolatility") else None
                delta = Decimal(str(opt_data.get("delta", 0))) if opt_data.get("delta") else None
                
                # Calculate spread
                if ask > 0 and bid > 0:
                    spread_pct = (ask - bid) / ask * 100
                else:
                    spread_pct = Decimal("100")
                
                # Create mock instrument (in reality, fetch from instrument master)
                instrument = Instrument(
                    symbol=f"{underlying}{int(strike_decimal)}{option_type}",
                    name=f"{underlying} {int(strike_decimal)} {option_type}",
                    instrument_type=InstrumentType.OPTION_CE if option_type == "CE" else InstrumentType.OPTION_PE,
                    token=str(item.get("token", "")),
                    lot_size=self.config["lot_sizes"].get(underlying, 75),
                    tick_size=Decimal("0.05"),
                )
                
                contracts.append(OptionContract(
                    instrument=instrument,
                    strike=strike_decimal,
                    option_type=option_type,
                    premium=premium,
                    bid=bid,
                    ask=ask,
                    spread_pct=spread_pct,
                    oi=oi,
                    volume=volume,
                    iv=iv,
                    delta=delta
                ))
        except Exception as e:
            logger.error(f"Error parsing option chain: {e}")
        
        return contracts

    def _filter_contracts(self, contracts: List[OptionContract]) -> List[OptionContract]:
        """Filter contracts by liquidity, spread, and quality."""
        filtered = []
        
        for c in contracts:
            # Skip zero premium
            if c.premium <= 0:
                continue
            
            # Check spread
            if c.spread_pct > Decimal(str(self.config["max_spread_pct"] * 100)):
                continue
            
            # Check OI
            if c.oi < self.config["min_oi_threshold"]:
                continue
            
            # Check volume
            if c.volume < self.config["min_volume_threshold"]:
                continue
            
            # Check depth (bid/ask qty would be needed)
            # For now, skip if bid or ask is 0
            if c.bid <= 0 or c.ask <= 0:
                continue
            
            filtered.append(c)
        
        return filtered

    def _rank_contracts(
        self, 
        contracts: List[OptionContract], 
        spot_price: Decimal, 
        preferred_order: List[str]
    ) -> List[OptionContract]:
        """Rank contracts by moneyness preference and quality."""
        # Find ATM strike
        atm_strike = min(contracts, key=lambda x: abs(x.strike - spot_price)).strike
        
        # Assign preference scores
        for c in contracts:
            c.preference_score = 0
            
            # Moneyness preference
            if c.strike == atm_strike:
                c.moneyness = "ATM"
                moneyness_rank = preferred_order.index("atm") if "atm" in preferred_order else 0
            elif c.option_type == "CE":
                if c.strike > atm_strike:
                    strikes_above = sorted([x.strike for x in contracts if x.strike > atm_strike])
                    idx = strikes_above.index(c.strike) if c.strike in strikes_above else 99
                    c.moneyness = f"OTM_{idx + 1}"
                    moneyness_rank = preferred_order.index(f"otm_{idx + 1}") if f"otm_{idx + 1}" in preferred_order else 99
                else:
                    c.moneyness = "ITM"
                    moneyness_rank = preferred_order.index("itm_1") if "itm_1" in preferred_order else 99
            else:  # PE
                if c.strike < atm_strike:
                    strikes_below = sorted([x.strike for x in contracts if x.strike < atm_strike], reverse=True)
                    idx = strikes_below.index(c.strike) if c.strike in strikes_below else 99
                    c.moneyness = f"OTM_{idx + 1}"
                    moneyness_rank = preferred_order.index(f"otm_{idx + 1}") if f"otm_{idx + 1}" in preferred_order else 99
                else:
                    c.moneyness = "ITM"
                    moneyness_rank = preferred_order.index("itm_1") if "itm_1" in preferred_order else 99
            
            c.preference_score = (99 - moneyness_rank) * 100
            
            # Quality bonuses
            if c.oi > 10000:
                c.preference_score += 20
            if c.volume > 5000:
                c.preference_score += 15
            if c.spread_pct < 1:
                c.preference_score += 15
            if c.iv and c.iv < 20:
                c.preference_score += 10
        
        # Sort by preference score descending
        return sorted(contracts, key=lambda x: x.preference_score, reverse=True)

    def _calculate_quantity_and_cost(
        self,
        contract: OptionContract,
        available_funds: Decimal,
        available_margin: Decimal,
        risk_budget: Decimal,
        lot_size: int
    ) -> Tuple[int, Decimal, Decimal]:
        """Calculate max affordable quantity and total cost."""
        premium_per_lot = contract.premium * lot_size
        
        # Estimate charges
        turnover = premium_per_lot
        brokerage = min(Decimal("20"), turnover * Decimal("0.0003"))  # 0.03% or 20 per lot
        stt = turnover * Decimal("0.0005")  # 0.05% on sell side (for entry, STT on premium)
        exchange_txn = turnover * Decimal("0.000345")
        gst = (brokerage + exchange_txn) * Decimal("0.18")
        sebi = turnover * Decimal("0.000001")
        stamp_duty = turnover * Decimal("0.00003")
        
        charges_per_lot = brokerage + stt + exchange_txn + gst + sebi + stamp_duty
        
        # Add slippage buffer
        slippage_buffer = premium_per_lot * Decimal(str(self.config["slippage_buffer_pct"]))
        
        total_cost_per_lot = premium_per_lot + charges_per_lot + slippage_buffer
        
        # Cash buffer
        cash_buffer = available_funds * Decimal(str(self.risk_config["cash_buffer_pct"]))
        deployable_funds = available_funds - cash_buffer
        
        # Max lots by funds
        max_lots_by_funds = int(deployable_funds / total_cost_per_lot) if total_cost_per_lot > 0 else 0
        
        # Max lots by risk budget (for options, max loss = premium * qty)
        max_lots_by_risk = int(risk_budget / premium_per_lot) if premium_per_lot > 0 else 0
        
        # Final quantity
        max_lots = min(max_lots_by_funds, max_lots_by_risk)
        quantity = max_lots * lot_size
        
        total_cost = total_cost_per_lot * max_lots
        total_charges = charges_per_lot * max_lots
        
        return quantity, total_cost, total_charges

    def _final_validation(
        self,
        contract: OptionContract,
        available_funds: Decimal,
        risk_budget: Decimal,
        lot_size: int
    ) -> Dict[str, Any]:
        """Final validation before selection."""
        premium_per_lot = contract.premium * lot_size
        
        # Check premium not zero
        if contract.premium <= 0:
            return {"valid": False, "reason": "Selected contract has zero premium"}
        
        # Check spread not too wide
        if contract.spread_pct > Decimal(str(self.config["max_spread_pct"] * 100)):
            return {"valid": False, "reason": f"Spread too wide: {contract.spread_pct}%"}
        
        # Check liquidity
        if contract.oi < self.config["min_oi_threshold"]:
            return {"valid": False, "reason": f"Insufficient OI: {contract.oi}"}
        
        # Check affordability
        if not hasattr(contract, 'quantity') or contract.quantity < lot_size:
            return {"valid": False, "reason": "Insufficient quantity for minimum lot"}
        
        # Check risk budget
        max_loss = premium_per_lot * Decimal(contract.quantity // lot_size)
        if max_loss > risk_budget:
            return {"valid": False, "reason": f"Max loss {max_loss} exceeds risk budget {risk_budget}"}
        
        return {"valid": True, "reason": None}


# Singleton instance
options_selection_engine = OptionsSelectionEngine()