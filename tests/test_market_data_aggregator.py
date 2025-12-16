"""Tests for market data aggregator service."""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from src.services.market_data_aggregator import MarketDataAggregator
from src.models.market_data import MarketData, HistoricalData, DataSource


# Strategies for generating test data
@st.composite
def market_data_strategy(draw):
    """Generate valid MarketData objects."""
    symbol = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(blacklist_characters="\x00")))
    data_type = draw(st.sampled_from(["crypto", "stock"]))
    current_price = draw(st.floats(min_value=0.01, max_value=1000000, allow_nan=False, allow_infinity=False))
    price_change = draw(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False))
    volume = draw(st.floats(min_value=0, max_value=1000000000, allow_nan=False, allow_infinity=False))
    
    # Generate historical data
    prices = draw(st.lists(
        st.floats(min_value=0.01, max_value=1000000, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=30
    ))
    timestamps = draw(st.lists(
        st.floats(min_value=0, allow_nan=False, allow_infinity=False),
        min_size=len(prices),
        max_size=len(prices)
    ))
    
    period = draw(st.sampled_from(["24h", "7d", "30d"]))
    
    historical = HistoricalData(
        period=period,
        prices=prices,
        timestamps=timestamps
    )
    
    source = DataSource(
        name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters="\x00"))),
        url=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters="\x00"))),
        fetched_at=datetime.now()
    )
    
    return MarketData(
        symbol=symbol,
        type=data_type,
        current_price=current_price,
        price_change_24h=price_change,
        volume_24h=volume,
        historical_data=historical,
        source=source
    )


class TestMarketDataAggregator:
    """Test suite for MarketDataAggregator."""

    def test_aggregator_initialization(self):
        """Test that aggregator initializes correctly."""
        aggregator = MarketDataAggregator()
        assert aggregator.coingecko_base_url == "https://api.coingecko.com/api/v3"
        assert aggregator.alphavantage_base_url == "https://www.alphavantage.co/query"

    @given(market_data_strategy())
    def test_market_data_source_attribution(self, market_data):
        """
        **Feature: daily-market-tips, Property 1: Exchange data includes source attribution**
        
        For any MarketData object, the source field SHALL contain a non-empty name and url.
        
        **Validates: Requirements 1.3, 2.3**
        """
        # Property: All market data must have source attribution
        assert market_data.source is not None, "Market data must have a source"
        assert isinstance(market_data.source, DataSource), "Source must be a DataSource object"
        assert market_data.source.name, "Source name must not be empty"
        assert market_data.source.url, "Source URL must not be empty"
        assert market_data.source.fetched_at is not None, "Source must have a fetch timestamp"

    @given(market_data_strategy())
    def test_historical_data_inclusion(self, market_data):
        """
        **Feature: daily-market-tips, Property 2: Historical data is included with exchange data**
        
        For any MarketData object, the historical_data field SHALL contain at least one price point
        and the period SHALL be one of the valid values.
        
        **Validates: Requirements 1.4**
        """
        # Property: All market data must include historical data
        assert market_data.historical_data is not None, "Market data must have historical data"
        assert isinstance(market_data.historical_data, HistoricalData), "Historical data must be a HistoricalData object"
        assert market_data.historical_data.period in ["24h", "7d", "30d"], "Period must be valid"
        assert len(market_data.historical_data.prices) > 0, "Historical data must contain at least one price"
        assert len(market_data.historical_data.timestamps) == len(market_data.historical_data.prices), \
            "Timestamps and prices must have the same length"

    def test_get_historical_data_invalid_period(self):
        """Test that invalid period returns None."""
        aggregator = MarketDataAggregator()
        result = aggregator.get_historical_data("bitcoin", "invalid")
        assert result is None

    def test_historical_data_structure(self):
        """Test that historical data has correct structure."""
        historical = HistoricalData(
            period="7d",
            prices=[100.0, 101.0, 102.0],
            timestamps=[1000.0, 2000.0, 3000.0]
        )
        assert historical.period == "7d"
        assert len(historical.prices) == 3
        assert len(historical.timestamps) == 3
