"""Tests for scheduler service."""

import pytest
import json
import sys
from io import StringIO
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.services.scheduler_service import SchedulerService
from src.services.email_service import EmailService
from src.services.market_data_aggregator import MarketDataAggregator
from src.services.analysis_engine import AnalysisEngine
from src.models.trading_tip import EmailContent, TradingTip, TipSource
from src.models.market_data import MarketData, HistoricalData, DataSource
from src.utils.logger import StructuredLogger


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

    @given(market_data_strategy(asset_type="crypto"))
    @settings(max_examples=20)
    def test_delivery_operations_are_logged(self, market_data):
        """
        **Feature: observability-logging, Property 1: Delivery operations are logged**
        **Validates: Requirements 1.1**

        For any delivery operation, the event store SHALL contain both a delivery_start
        and delivery_complete event with matching trace IDs.
        """
        from src.utils.event_store import EventStore
        from src.utils.trace_context import create_trace, clear_trace
        
        event_store = EventStore()
        scheduler = SchedulerService(event_store=event_store)
        
        # Create a trace for this test
        trace_id = create_trace()
        
        try:
            # Mock the services to return our test data
            with patch.object(scheduler.market_aggregator, 'fetch_crypto_data', return_value=[market_data]):
                with patch.object(scheduler.market_aggregator, 'fetch_stock_data', return_value=[]):
                    mock_tip = TradingTip(
                        symbol=market_data.symbol,
                        type="crypto",
                        recommendation="BUY",
                        reasoning="Test recommendation",
                        confidence=75,
                        indicators=["RSI"],
                        sources=[TipSource(name="Test", url="https://test.com")]
                    )
                    with patch.object(scheduler.analysis_engine, 'analyze_crypto', return_value=[mock_tip]):
                        with patch.object(scheduler.analysis_engine, 'analyze_stocks', return_value=[]):
                            with patch.object(scheduler.email_service, 'send_email_content', return_value=True):
                                # Execute delivery
                                scheduler.execute_delivery("morning")
                                
                                # Property: Event store should contain delivery_start event
                                events = event_store.get_all_events()
                                delivery_start_events = [e for e in events if e.event_type == "delivery_start"]
                                assert len(delivery_start_events) > 0, "delivery_start event not found"
                                
                                # Property: Event store should contain delivery_complete event
                                delivery_complete_events = [e for e in events if e.event_type == "delivery_complete"]
                                assert len(delivery_complete_events) > 0, "delivery_complete event not found"
                                
                                # Property: Both events should have matching trace IDs
                                start_trace = delivery_start_events[0].trace_id
                                complete_trace = delivery_complete_events[0].trace_id
                                assert start_trace == complete_trace, "Trace IDs don't match between start and complete events"
        finally:
            clear_trace()

    @given(market_data_strategy(asset_type="crypto"))
    @settings(max_examples=20)
    def test_fetch_operations_are_logged_with_required_fields(self, market_data):
        """
        **Feature: observability-logging, Property 2: Fetch operations are logged with required fields**
        **Validates: Requirements 1.2**

        For any market data fetch operation, the log entry SHALL include source,
        symbols, and result (success/failure).
        """
        from src.utils.trace_context import create_trace, clear_trace
        
        trace_id = create_trace()
        
        try:
            aggregator = MarketDataAggregator()
            
            # Mock the requests to return our test data
            with patch('src.services.market_data_aggregator.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    market_data.symbol.lower(): {
                        "usd": market_data.current_price,
                        "usd_24h_change": market_data.price_change_24h,
                        "usd_24h_vol": market_data.volume_24h
                    }
                }
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                # Capture logs
                captured_output = StringIO()
                original_stdout = sys.stdout
                sys.stdout = captured_output
                
                try:
                    # Fetch crypto data
                    result = aggregator.fetch_crypto_data([market_data.symbol])
                    
                    # Restore stdout
                    sys.stdout = original_stdout
                    output = captured_output.getvalue()
                    
                    # Parse log entries
                    log_lines = output.strip().split('\n')
                    log_entries = [json.loads(line) for line in log_lines if line.strip()]
                    
                    # Property: At least one log entry should exist
                    assert len(log_entries) > 0, "No log entries found"
                    
                    # Property: Log entries should include source and symbol
                    source_logs = [e for e in log_entries if "source" in e.get("context", {})]
                    assert len(source_logs) > 0, "No logs with source field found"
                    
                    for log_entry in source_logs:
                        context = log_entry.get("context", {})
                        assert "source" in context, "Missing 'source' field in context"
                        assert "symbol" in context, "Missing 'symbol' field in context"
                    
                    # Property: At least one log entry should have a result field
                    result_logs = [e for e in log_entries if "result" in e.get("context", {})]
                    assert len(result_logs) > 0, "No logs with result field found"
                    
                    for log_entry in result_logs:
                        context = log_entry.get("context", {})
                        assert context["result"] in ["success", "failed", "not_found"], "Invalid result value"
                        
                finally:
                    sys.stdout = original_stdout
        finally:
            clear_trace()

    @given(market_data_strategy(asset_type="crypto"))
    @settings(max_examples=20)
    def test_analysis_operations_are_logged_with_indicators(self, market_data):
        """
        **Feature: observability-logging, Property 3: Analysis operations are logged with indicators**
        **Validates: Requirements 1.3**

        For any analysis operation, the log entry SHALL include the indicators
        calculated and the resulting recommendation.
        """
        from src.utils.trace_context import create_trace, clear_trace
        
        trace_id = create_trace()
        
        try:
            engine = AnalysisEngine()
            
            # Capture logs
            captured_output = StringIO()
            original_stdout = sys.stdout
            sys.stdout = captured_output
            
            try:
                # Analyze crypto data
                tips = engine.analyze_crypto([market_data])
                
                # Restore stdout
                sys.stdout = original_stdout
                output = captured_output.getvalue()
                
                # Parse log entries
                log_lines = output.strip().split('\n')
                log_entries = [json.loads(line) for line in log_lines if line.strip()]
                
                # Property: Log entries should include indicators and recommendation
                analysis_logs = [e for e in log_entries if "indicators" in e.get("context", {})]
                assert len(analysis_logs) > 0, "No logs with indicators found"
                
                for log_entry in analysis_logs:
                    context = log_entry.get("context", {})
                    if "indicators" in context:
                        assert isinstance(context["indicators"], list), "Indicators should be a list"
                        if "recommendation" in context:
                            assert context["recommendation"] in ["BUY", "SELL", "HOLD"], "Invalid recommendation"
                
            finally:
                sys.stdout = original_stdout
        finally:
            clear_trace()

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=20)
    def test_email_operations_are_logged_with_required_fields(self, recipient):
        """
        **Feature: observability-logging, Property 4: Email operations are logged with required fields**
        **Validates: Requirements 1.4**

        For any email send operation, the log entry SHALL include recipient,
        subject, and delivery status.
        """
        from src.utils.trace_context import create_trace, clear_trace
        
        trace_id = create_trace()
        
        try:
            email_service = EmailService()
            
            # Capture logs
            captured_output = StringIO()
            original_stdout = sys.stdout
            sys.stdout = captured_output
            
            try:
                # Mock SMTP to prevent actual email sending
                with patch('src.services.email_service.smtplib.SMTP'):
                    # Attempt to send email (will fail due to mock, but logs should be created)
                    email_service.send_email(recipient, "Test Subject", "Test Content", "morning")
                    
                    # Restore stdout
                    sys.stdout = original_stdout
                    output = captured_output.getvalue()
                    
                    # Parse log entries
                    log_lines = output.strip().split('\n')
                    log_entries = [json.loads(line) for line in log_lines if line.strip()]
                    
                    # Property: Log entries should include recipient, subject, and delivery_type
                    email_logs = [e for e in log_entries if "recipient" in e.get("context", {})]
                    assert len(email_logs) > 0, "No logs with recipient found"
                    
                    for log_entry in email_logs:
                        context = log_entry.get("context", {})
                        assert "recipient" in context, "Missing 'recipient' field"
                        assert "subject" in context, "Missing 'subject' field"
                        assert "delivery_type" in context, "Missing 'delivery_type' field"
                        assert context["recipient"] == recipient
                        assert context["subject"] == "Test Subject"
                        assert context["delivery_type"] == "morning"
                
            finally:
                sys.stdout = original_stdout
        finally:
            clear_trace()

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=20)
    def test_error_logging_includes_full_context(self, error_message):
        """
        **Feature: observability-logging, Property 5: Error logging includes full context**
        **Validates: Requirements 1.5**

        For any error that occurs, the error log entry SHALL include exception type,
        message, and stack trace.
        """
        from src.utils.trace_context import create_trace, clear_trace
        
        trace_id = create_trace()
        
        try:
            # Capture logs
            captured_output = StringIO()
            original_stdout = sys.stdout
            sys.stdout = captured_output
            
            try:
                logger = StructuredLogger("test_component")
                
                # Create and log an exception
                try:
                    raise ValueError(error_message)
                except ValueError as e:
                    logger.error("Test error occurred", exception=e)
                
                # Restore stdout
                sys.stdout = original_stdout
                output = captured_output.getvalue()
                
                # Parse log entry
                log_entry = json.loads(output.strip())
                
                # Property: Error log should include exception details
                assert "exception" in log_entry, "Missing 'exception' field"
                assert "type" in log_entry["exception"], "Missing exception 'type'"
                assert "message" in log_entry["exception"], "Missing exception 'message'"
                assert "stack_trace" in log_entry["exception"], "Missing exception 'stack_trace'"
                
                # Property: Exception details should match
                assert log_entry["exception"]["type"] == "ValueError"
                assert error_message in log_entry["exception"]["message"]
                
            finally:
                sys.stdout = original_stdout
        finally:
            clear_trace()

