import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Pytest configuration
pytest_plugins = []

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")

# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    np.random.seed(42)
    dates = pd.date_range(
        start='2026-01-01 09:15', 
        periods=100, 
        freq='5min', 
        tz='Asia/Kolkata'
    )
    
    base_price = 19800
    trend = np.linspace(0, 200, 100)
    noise = np.random.normal(0, 10, 100)
    close_prices = base_price + trend + noise
    
    high = close_prices + np.abs(np.random.normal(0, 5, 100))
    low = close_prices - np.abs(np.random.normal(0, 5, 100))
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0]
    volume = np.random.randint(100000, 1000000, 100)
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close_prices,
        'volume': volume
    }, index=dates)
    
    return df

@pytest.fixture
def mock_option_chain():
    """Create mock option chain data."""
    return {
        "data": [
            {
                "strikePrice": 19800,
                "CE": {"lastPrice": 150, "bidprice": 148, "askPrice": 152, "openInterest": 50000, "totalTradedVolume": 100000, "impliedVolatility": 15.5},
                "PE": {"lastPrice": 120, "bidprice": 118, "askPrice": 122, "openInterest": 45000, "totalTradedVolume": 80000, "impliedVolatility": 14.8}
            },
            {
                "strikePrice": 19850,
                "CE": {"lastPrice": 120, "bidprice": 118, "askPrice": 122, "openInterest": 60000, "totalTradedVolume": 120000, "impliedVolatility": 15.2},
                "PE": {"lastPrice": 140, "bidprice": 138, "askPrice": 142, "openInterest": 55000, "totalTradedVolume": 90000, "impliedVolatility": 15.0}
            },
            {
                "strikePrice": 19900,
                "CE": {"lastPrice": 90, "bidprice": 88, "askPrice": 92, "openInterest": 40000, "totalTradedVolume": 80000, "impliedVolatility": 15.8},
                "PE": {"lastPrice": 170, "bidprice": 168, "askPrice": 172, "openInterest": 65000, "totalTradedVolume": 110000, "impliedVolatility": 14.5}
            }
        ]
    }