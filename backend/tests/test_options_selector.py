import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.options_selector import options_selection_engine, OptionContract, StrikeSelectionResult
from app.db.models import Instrument, InstrumentType


class TestOptionsSelector:
    """Test capital-aware options selection engine."""

    @pytest.fixture
    def mock_instrument(self):
        """Create mock instrument."""
        return Instrument(
            id=1,
            symbol="NIFTY19850CE",
            name="NIFTY 19850 CE",
            instrument_type=InstrumentType.OPTION_CE,
            exchange="NSE",
            token="12345",
            lot_size=75,
            tick_size=Decimal("0.05"),
            strike=Decimal("19850"),
            underlying="NIFTY",
            option_type="CE",
            is_active=True
        )

    @pytest.fixture
    def sample_option_chain(self):
        """Sample option chain data."""
        return {
            "data": [
                {
                    "strikePrice": 19800,
                    "CE": {"lastPrice": 180, "bidprice": 178, "askPrice": 182, "openInterest": 50000, "totalTradedVolume": 100000, "impliedVolatility": 15.5},
                    "PE": {"lastPrice": 120, "bidprice": 118, "askPrice": 122, "openInterest": 45000, "totalTradedVolume": 80000, "impliedVolatility": 14.8}
                },
                {
                    "strikePrice": 19850,
                    "CE": {"lastPrice": 150, "bidprice": 148, "askPrice": 152, "openInterest": 60000, "totalTradedVolume": 120000, "impliedVolatility": 15.2},
                    "PE": {"lastPrice": 140, "bidprice": 138, "askPrice": 142, "openInterest": 55000, "totalTradedVolume": 90000, "impliedVolatility": 15.0}
                },
                {
                    "strikePrice": 19900,
                    "CE": {"lastPrice": 120, "bidprice": 118, "askPrice": 122, "openInterest": 40000, "totalTradedVolume": 80000, "impliedVolatility": 15.8},
                    "PE": {"lastPrice": 170, "bidprice": 168, "askPrice": 172, "openInterest": 65000, "totalTradedVolume": 110000, "impliedVolatility": 14.5}
                },
                {
                    "strikePrice": 19750,
                    "CE": {"lastPrice": 210, "bidprice": 208, "askPrice": 212, "openInterest": 30000, "totalTradedVolume": 60000, "impliedVolatility": 16.0},
                    "PE": {"lastPrice": 100, "bidprice": 98, "askPrice": 102, "openInterest": 35000, "totalTradedVolume": 50000, "impliedVolatility": 15.5}
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_select_contract_bullish_affordable(self, mock_instrument, sample_option_chain):
        """Test selecting contract for bullish direction with sufficient funds."""
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bullish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("500000"),
            available_margin=Decimal("500000"),
            strategy_risk_budget=Decimal("3500"),  # 0.35% of 1M
            option_chain=sample_option_chain,
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        assert isinstance(result, StrikeSelectionResult)
        assert result.is_affordable == True
        assert result.selected_contract is not None
        assert result.selected_contract.option_type == "CE"
        assert result.selected_contract.strike in [Decimal("19800"), Decimal("19850"), Decimal("19900")]
        assert result.rejection_reason is None

    @pytest.mark.asyncio
    async def test_select_contract_bearish_affordable(self, mock_instrument, sample_option_chain):
        """Test selecting contract for bearish direction with sufficient funds."""
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bearish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("500000"),
            available_margin=Decimal("500000"),
            strategy_risk_budget=Decimal("3500"),
            option_chain=sample_option_chain,
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        assert result.is_affordable == True
        assert result.selected_contract is not None
        assert result.selected_contract.option_type == "PE"

    @pytest.mark.asyncio
    async def test_select_contract_insufficient_funds(self, mock_instrument, sample_option_chain):
        """Test contract selection with insufficient funds."""
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bullish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("5000"),  # Very low funds
            available_margin=Decimal("5000"),
            strategy_risk_budget=Decimal("3500"),
            option_chain=sample_option_chain,
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        assert result.is_affordable == False
        assert result.selected_contract is None
        assert "INSUFFICIENT_ELIGIBLE_CAPITAL" in result.rejection_reason

    @pytest.mark.asyncio
    async def test_select_contract_risk_budget_exceeded(self, mock_instrument, sample_option_chain):
        """Test contract selection when risk budget too low."""
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bullish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("500000"),
            available_margin=Decimal("500000"),
            strategy_risk_budget=Decimal("1000"),  # Too low for premium * 75
            option_chain=sample_option_chain,
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        # Should try alternative strikes but may still fail if all exceed risk budget
        assert result.is_affordable == False or result.selected_contract is None

    @pytest.mark.asyncio
    async def test_contract_filtering(self, mock_instrument, sample_option_chain):
        """Test contract filtering by liquidity and spread."""
        # All contracts in sample have good OI, volume, and spread
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bullish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("500000"),
            available_margin=Decimal("500000"),
            strategy_risk_budget=Decimal("3500"),
            option_chain=sample_option_chain,
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        if result.selected_contract:
            # Check filtered contract meets criteria
            assert result.selected_contract.oi >= 1000  # min_oi_threshold
            assert result.selected_contract.volume >= 500  # min_volume_threshold
            assert result.selected_contract.spread_pct <= 5  # max_spread_pct
            assert result.selected_contract.bid > 0
            assert result.selected_contract.ask > 0

    @pytest.mark.asyncio
    async def test_strike_ranking_preference(self, mock_instrument, sample_option_chain):
        """Test strike ranking follows preference order."""
        # Spot is 19850, so ATM = 19850, OTM1 = 19900, ITM1 = 19800
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bullish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("1000000"),
            available_margin=Decimal("1000000"),
            strategy_risk_budget=Decimal("10000"),
            option_chain=sample_option_chain,
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        if result.selected_contract:
            # Should prefer ATM (19850) if affordable
            assert result.selected_contract.strike in [Decimal("19850"), Decimal("19900"), Decimal("19800")]

    @pytest.mark.asyncio
    async def test_empty_option_chain(self, mock_instrument):
        """Test handling of empty option chain."""
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bullish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("500000"),
            available_margin=Decimal("500000"),
            strategy_risk_budget=Decimal("3500"),
            option_chain={"data": []},
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        assert result.is_affordable == False
        assert result.selected_contract is None
        assert "No valid option contracts found" in result.rejection_reason

    @pytest.mark.asyncio
    async def test_malformed_option_chain(self, mock_instrument):
        """Test handling of malformed option chain."""
        malformed_chain = {"data": [{"invalid": "data"}]}
        
        result = await options_selection_engine.select_contract(
            underlying="NIFTY",
            direction="bullish",
            spot_price=Decimal("19850"),
            available_funds=Decimal("500000"),
            available_margin=Decimal("500000"),
            strategy_risk_budget=Decimal("3500"),
            option_chain=malformed_chain,
            preferred_strikes=["atm", "otm_1", "itm_1"],
            expiry=None,
            lot_size=75
        )
        
        assert result.is_affordable == False
        assert result.selected_contract is None


class TestOptionContract:
    """Test OptionContract dataclass."""

    def test_contract_creation(self):
        """Test creating option contract."""
        from app.db.models import Instrument, InstrumentType
        
        instrument = Instrument(
            symbol="NIFTY19850CE",
            name="NIFTY 19850 CE",
            instrument_type=InstrumentType.OPTION_CE,
            exchange="NSE",
            token="12345",
            lot_size=75,
            strike=Decimal("19850"),
            option_type="CE"
        )
        
        contract = OptionContract(
            instrument=instrument,
            strike=Decimal("19850"),
            option_type="CE",
            premium=Decimal("150"),
            bid=Decimal("148"),
            ask=Decimal("152"),
            spread_pct=Decimal("2.63"),
            oi=60000,
            volume=120000,
            iv=Decimal("15.2"),
            delta=Decimal("0.52")
        )
        
        assert contract.strike == Decimal("19850")
        assert contract.option_type == "CE"
        assert contract.spread_pct == Decimal("2.63")
        assert contract.premium == Decimal("150")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])