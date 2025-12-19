"""Tests for analysis engine service."""

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from src.models.market_data import DataSource, HistoricalData, MarketData
from src.models.trading_tip import TradingTip
from src.services.analysis_engine import AnalysisEngine
from src.utils.event_store import EventStore
from src.utils.trace_context import clear_trace, create_trace


# Strategies for generating test data
@st.composite
def market_data_strategy(draw, asset_type=None):
    """Generate valid MarketData objects."""
    symbol = draw(
        st.text(min_size=1, max_size=10, alphabet=st.characters(blacklist_characters="\x00"))
    )
    if asset_type is None:
        data_type = draw(st.sampled_from(["crypto", "stock"]))
    else:
        data_type = asset_type

    current_price = draw(
        st.floats(min_value=0.01, max_value=1000000, allow_nan=False, allow_infinity=False)
    )
    price_change = draw(
        st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False)
    )
    volume = draw(
        st.floats(min_value=0, max_value=1000000000, allow_nan=False, allow_infinity=False)
    )

    # Generate historical data with at least 26 prices for MACD calculation
    prices = draw(
        st.lists(
            st.floats(min_value=0.01, max_value=1000000, allow_nan=False, allow_infinity=False),
            min_size=26,
            max_size=100,
        )
    )
    timestamps = draw(
        st.lists(
            st.floats(min_value=0, allow_nan=False, allow_infinity=False),
            min_size=len(prices),
            max_size=len(prices),
        )
    )

    period = draw(st.sampled_from(["24h", "7d", "30d"]))

    historical = HistoricalData(period=period, prices=prices, timestamps=timestamps)

    source = DataSource(
        name=draw(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters="\x00"))
        ),
        url=draw(
            st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters="\x00"))
        ),
        fetched_at=datetime.now(),
    )

    return MarketData(
        symbol=symbol,
        type=data_type,
        current_price=current_price,
        price_change_24h=price_change,
        volume_24h=volume,
        historical_data=historical,
        source=source,
    )


class TestAnalysisEngine:
    """Test suite for AnalysisEngine."""

    def test_engine_initialization(self):
        """Test that analysis engine initializes correctly."""
        engine = AnalysisEngine()
        assert engine is not None

    @given(st.lists(market_data_strategy(asset_type="crypto"), min_size=1, max_size=10))
    def test_tip_reasoning_inclusion(self, market_data_list):
        """
        **Feature: daily-market-tips, Property 3: All tips include reasoning**

        For any list of market data, all generated tips SHALL include a non-empty reasoning field.

        **Validates: Requirements 2.2**
        """
        engine = AnalysisEngine()
        tips = engine.analyze_crypto(market_data_list)

        # Property: All tips must have reasoning
        for tip in tips:
            assert isinstance(tip, TradingTip), "Result must be a TradingTip object"
            assert tip.reasoning is not None, "Tip must have reasoning"
            assert isinstance(tip.reasoning, str), "Reasoning must be a string"
            assert len(tip.reasoning) > 0, "Reasoning must not be empty"

    @given(st.lists(market_data_strategy(), min_size=1, max_size=10))
    def test_tip_categorization(self, market_data_list):
        """
        **Feature: daily-market-tips, Property 4: Tips are categorized by type**

        For any list of market data, all generated tips SHALL be properly categorized as either
        "crypto" or "stock" with no mixed or undefined types.

        **Validates: Requirements 2.5**
        """
        engine = AnalysisEngine()

        # Analyze crypto data
        crypto_data = [d for d in market_data_list if d.type == "crypto"]
        if crypto_data:
            crypto_tips = engine.analyze_crypto(crypto_data)
            for tip in crypto_tips:
                assert tip.type == "crypto", "Crypto tips must be categorized as crypto"
                assert tip.type in ["crypto", "stock"], "Tip type must be valid"

        # Analyze stock data
        stock_data = [d for d in market_data_list if d.type == "stock"]
        if stock_data:
            stock_tips = engine.analyze_stocks(stock_data)
            for tip in stock_tips:
                assert tip.type == "stock", "Stock tips must be categorized as stock"
                assert tip.type in ["crypto", "stock"], "Tip type must be valid"

    @given(st.lists(market_data_strategy(asset_type="crypto"), min_size=1, max_size=10))
    def test_indicator_references(self, market_data_list):
        """
        **Feature: daily-market-tips, Property 5: Analysis references indicators**

        For any list of market data, all generated tips SHALL reference at least one established
        technical analysis indicator (RSI, SMA, MACD, etc.).

        **Validates: Requirements 2.1**
        """
        engine = AnalysisEngine()
        tips = engine.analyze_crypto(market_data_list)

        # Property: All tips must reference at least one indicator
        for tip in tips:
            assert isinstance(tip.indicators, list), "Indicators must be a list"
            assert len(tip.indicators) > 0, "Tip must reference at least one indicator"
            # Verify indicators are valid technical analysis indicators
            valid_indicators = {"RSI", "SMA", "MACD", "EMA"}
            for indicator in tip.indicators:
                assert indicator in valid_indicators, (
                    f"Indicator {indicator} must be a valid technical analysis indicator"
                )

    def test_crypto_analysis_generates_tips(self):
        """Test that crypto analysis generates tips."""
        engine = AnalysisEngine()

        historical = HistoricalData(
            period="24h",
            prices=[
                100.0,
                101.0,
                102.0,
                103.0,
                104.0,
                105.0,
                106.0,
                107.0,
                108.0,
                109.0,
                110.0,
                111.0,
                112.0,
                113.0,
                114.0,
                115.0,
                116.0,
                117.0,
                118.0,
                119.0,
                120.0,
                121.0,
                122.0,
                123.0,
                124.0,
                125.0,
                126.0,
                127.0,
                128.0,
                129.0,
            ],
            timestamps=[float(i) for i in range(30)],
        )

        market_data = MarketData(
            symbol="BTC",
            type="crypto",
            current_price=129.0,
            price_change_24h=29.0,
            volume_24h=1000000.0,
            historical_data=historical,
            source=DataSource(
                name="CoinGecko", url="https://coingecko.com", fetched_at=datetime.now()
            ),
        )

        tips = engine.analyze_crypto([market_data])
        assert len(tips) == 1
        assert tips[0].symbol == "BTC"
        assert tips[0].type == "crypto"
        assert tips[0].recommendation in ["BUY", "SELL", "HOLD"]
        assert tips[0].confidence >= 0
        assert tips[0].confidence <= 100

    def test_stock_analysis_generates_tips(self):
        """Test that stock analysis generates tips."""
        engine = AnalysisEngine()

        historical = HistoricalData(
            period="7d",
            prices=[
                100.0,
                101.0,
                102.0,
                103.0,
                104.0,
                105.0,
                106.0,
                107.0,
                108.0,
                109.0,
                110.0,
                111.0,
                112.0,
                113.0,
                114.0,
                115.0,
                116.0,
                117.0,
                118.0,
                119.0,
                120.0,
                121.0,
                122.0,
                123.0,
                124.0,
                125.0,
                126.0,
                127.0,
                128.0,
                129.0,
            ],
            timestamps=[float(i) for i in range(30)],
        )

        market_data = MarketData(
            symbol="AAPL",
            type="stock",
            current_price=129.0,
            price_change_24h=-2.0,
            volume_24h=5000000.0,
            historical_data=historical,
            source=DataSource(
                name="Alpha Vantage", url="https://alphavantage.co", fetched_at=datetime.now()
            ),
        )

        tips = engine.analyze_stocks([market_data])
        assert len(tips) == 1
        assert tips[0].symbol == "AAPL"
        assert tips[0].type == "stock"
        assert tips[0].recommendation in ["BUY", "SELL", "HOLD"]
        assert tips[0].confidence >= 0
        assert tips[0].confidence <= 100

    def test_analysis_filters_by_type(self):
        """Test that analysis correctly filters by asset type."""
        engine = AnalysisEngine()

        historical = HistoricalData(
            period="24h",
            prices=[100.0 + i for i in range(30)],
            timestamps=[float(i) for i in range(30)],
        )

        crypto_data = MarketData(
            symbol="BTC",
            type="crypto",
            current_price=130.0,
            price_change_24h=30.0,
            volume_24h=1000000.0,
            historical_data=historical,
            source=DataSource(
                name="CoinGecko", url="https://coingecko.com", fetched_at=datetime.now()
            ),
        )

        stock_data = MarketData(
            symbol="AAPL",
            type="stock",
            current_price=130.0,
            price_change_24h=30.0,
            volume_24h=5000000.0,
            historical_data=historical,
            source=DataSource(
                name="Alpha Vantage", url="https://alphavantage.co", fetched_at=datetime.now()
            ),
        )

        # Crypto analysis should only return crypto tips
        crypto_tips = engine.analyze_crypto([crypto_data, stock_data])
        assert len(crypto_tips) == 1
        assert crypto_tips[0].type == "crypto"

        # Stock analysis should only return stock tips
        stock_tips = engine.analyze_stocks([crypto_data, stock_data])
        assert len(stock_tips) == 1
        assert stock_tips[0].type == "stock"

    @given(st.lists(market_data_strategy(asset_type="crypto"), min_size=1, max_size=10))
    def test_analysis_operations_logged_with_indicators(self, market_data_list):
        """
        **Feature: observability-logging, Property 3: Analysis operations are logged with indicators**

        For any analysis operation, the event store SHALL contain analysis_complete events
        with indicators included in the context.

        **Validates: Requirements 1.3**
        """
        # Setup
        event_store = EventStore()
        engine = AnalysisEngine(event_store=event_store)
        trace_id = create_trace()

        try:
            # Execute
            tips = engine.analyze_crypto(market_data_list)

            # Verify
            # Get all analysis_complete events for this trace that have symbol in context
            # (these are per-symbol analysis events, not the summary event)
            analysis_events = [
                e
                for e in event_store.get_events_by_trace(trace_id)
                if e.event_type == "analysis_complete" and "symbol" in e.context
            ]

            # Property: For each tip generated, there should be a corresponding analysis_complete event
            # with indicators in the context
            assert len(analysis_events) == len(tips), (
                "Each tip must have a corresponding analysis event"
            )

            for event in analysis_events:
                # Each event should have indicators in context
                assert "indicators" in event.context, "Analysis event must include indicators"
                indicators = event.context["indicators"]
                assert isinstance(indicators, list), "Indicators must be a list"
                assert len(indicators) > 0, "Analysis must reference at least one indicator"

                # Verify indicators are valid
                valid_indicators = {"RSI", "SMA", "MACD"}
                for indicator in indicators:
                    assert indicator in valid_indicators, f"Indicator {indicator} must be valid"

        finally:
            clear_trace()
