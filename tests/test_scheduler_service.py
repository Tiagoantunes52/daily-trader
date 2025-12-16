"""Tests for scheduler service."""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.services.scheduler_service import SchedulerService
from src.services.email_service import EmailService
from src.services.market_data_aggregator import MarketDataAggregator
from src.services.analysis_engine import AnalysisEngine
from src.models.trading_tip import EmailContent, TradingTip, TipSource
from src.models.market_data import MarketData, HistoricalData, DataSource


# Strategies for generating test data
@st.composite
def valid_time_strategy(draw):
    """Generate valid HH:MM time strings."""
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    return f"{hour:02d}:{minute:02d}"


@st.composite
def market_data_strategy(draw, asset_type=None):
    """Generate valid MarketData objects."""
    symbol = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(blacklist_characters="\x00")))
    if asset_type is None:
        data_type = draw(st.sampled_from(["crypto", "stock"]))
    else:
        data_type = asset_type
    
    current_price = draw(st.floats(min_value=0.01, max_value=1000000, allow_nan=False, allow_infinity=False))
    price_change = draw(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False))
    volume = draw(st.floats(min_value=0, max_value=1000000000, allow_nan=False, allow_infinity=False))
    
    # Generate historical data with at least 26 prices for MACD calculation
    prices = draw(st.lists(
        st.floats(min_value=0.01, max_value=1000000, allow_nan=False, allow_infinity=False),
        min_size=26,
        max_size=100
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


class TestSchedulerService:
    """Test suite for SchedulerService."""

    def test_scheduler_initialization(self):
        """Test that scheduler initializes correctly."""
        scheduler = SchedulerService()
        assert scheduler is not None
        assert scheduler.is_running is False
        assert scheduler.scheduler is not None

    def test_validate_time_format_valid(self):
        """Test that valid time formats are accepted."""
        scheduler = SchedulerService()
        # Should not raise
        scheduler._validate_time_format("06:00")
        scheduler._validate_time_format("18:30")
        scheduler._validate_time_format("00:00")
        scheduler._validate_time_format("23:59")

    def test_validate_time_format_invalid(self):
        """Test that invalid time formats are rejected."""
        scheduler = SchedulerService()
        
        with pytest.raises(ValueError):
            scheduler._validate_time_format("25:00")  # Invalid hour
        
        with pytest.raises(ValueError):
            scheduler._validate_time_format("12:60")  # Invalid minute
        
        with pytest.raises(ValueError):
            scheduler._validate_time_format("12")  # Missing minute
        
        with pytest.raises(ValueError):
            scheduler._validate_time_format("12:30:45")  # Too many parts

    @given(valid_time_strategy(), valid_time_strategy())
    @settings(max_examples=50)
    def test_scheduled_delivery_execution(self, morning_time, evening_time):
        """
        **Feature: daily-market-tips, Property 6: Email delivery executes on schedule**
        
        For any valid morning and evening times, when schedule_deliveries is called,
        the scheduler SHALL be started and jobs SHALL be registered for both times.
        
        **Validates: Requirements 3.2**
        """
        scheduler = SchedulerService()
        
        # Schedule deliveries
        scheduler.schedule_deliveries(morning_time, evening_time)
        
        # Property: Scheduler must be running
        assert scheduler.is_running is True, "Scheduler must be running after scheduling deliveries"
        
        # Property: Jobs must be registered
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) >= 2, "At least 2 jobs (morning and evening) must be registered"
        
        # Property: Morning job must exist
        morning_job = scheduler.scheduler.get_job("morning_delivery")
        assert morning_job is not None, "Morning delivery job must be registered"
        assert morning_job.name == "Morning Market Tips Delivery"
        
        # Property: Evening job must exist
        evening_job = scheduler.scheduler.get_job("evening_delivery")
        assert evening_job is not None, "Evening delivery job must be registered"
        assert evening_job.name == "Evening Market Tips Delivery"
        
        # Cleanup
        scheduler.stop()

    def test_execute_delivery_with_mocked_services(self):
        """Test that execute_delivery orchestrates the full flow."""
        scheduler = SchedulerService()
        
        # Mock the services
        mock_market_data = MarketData(
            symbol="BTC",
            type="crypto",
            current_price=50000.0,
            price_change_24h=5.0,
            volume_24h=1000000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[49000.0 + i*100 for i in range(30)],
                timestamps=[float(i) for i in range(30)]
            ),
            source=DataSource(name="CoinGecko", url="https://coingecko.com", fetched_at=datetime.now())
        )
        
        mock_tip = TradingTip(
            symbol="BTC",
            type="crypto",
            recommendation="BUY",
            reasoning="Strong upward momentum",
            confidence=75,
            indicators=["RSI", "SMA"],
            sources=[TipSource(name="CoinGecko", url="https://coingecko.com")]
        )
        
        with patch.object(scheduler.market_aggregator, 'fetch_crypto_data', return_value=[mock_market_data]):
            with patch.object(scheduler.market_aggregator, 'fetch_stock_data', return_value=[]):
                with patch.object(scheduler.analysis_engine, 'analyze_crypto', return_value=[mock_tip]):
                    with patch.object(scheduler.analysis_engine, 'analyze_stocks', return_value=[]):
                        with patch.object(scheduler.email_service, 'send_email_content', return_value=True) as mock_send:
                            # Execute delivery
                            scheduler.execute_delivery("morning")
                            
                            # Verify email was sent
                            assert mock_send.called, "Email service should be called"
                            call_args = mock_send.call_args[0][0]
                            assert isinstance(call_args, EmailContent)
                            assert call_args.delivery_type == "morning"
                            assert len(call_args.tips) > 0
                            assert len(call_args.market_data) > 0

    def test_execute_delivery_invalid_type(self):
        """Test that invalid delivery type is handled gracefully."""
        scheduler = SchedulerService()
        
        # Should not raise, just log error
        scheduler.execute_delivery("invalid")

    def test_scheduler_stop(self):
        """Test that scheduler can be stopped."""
        scheduler = SchedulerService()
        scheduler.schedule_deliveries("06:00", "18:00")
        
        assert scheduler.is_running is True
        scheduler.stop()
        assert scheduler.is_running is False

    def test_schedule_deliveries_replaces_existing_jobs(self):
        """Test that scheduling twice replaces existing jobs."""
        scheduler = SchedulerService()
        
        # Schedule first time
        scheduler.schedule_deliveries("06:00", "18:00")
        jobs_count_1 = len(scheduler.scheduler.get_jobs())
        
        # Schedule second time with different times
        scheduler.schedule_deliveries("07:00", "19:00")
        jobs_count_2 = len(scheduler.scheduler.get_jobs())
        
        # Should have same number of jobs (replaced, not added)
        assert jobs_count_1 == jobs_count_2
        
        scheduler.stop()

