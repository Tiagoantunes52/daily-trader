"""Property-based tests for metrics calculation."""

import uuid
from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from src.utils.event_store import EventStore
from src.utils.metrics import MetricsCalculator


class TestMetricsCalculation:
    """Tests for metrics calculation accuracy."""

    @given(
        num_successful_deliveries=st.integers(min_value=0, max_value=50),
        num_failed_deliveries=st.integers(min_value=0, max_value=50),
    )
    def test_metrics_calculation_is_accurate(
        self, num_successful_deliveries, num_failed_deliveries
    ):
        """
        **Feature: observability-logging, Property 10: Metrics calculation is accurate**
        **Validates: Requirements 2.5**

        For any set of delivery events in the event store, the metrics endpoint
        SHALL return success_rate equal to (successful_deliveries / total_deliveries) * 100
        """
        store = EventStore()
        start_time = datetime.now(UTC)
        calculator = MetricsCalculator(store, start_time=start_time)

        # Add successful delivery complete events
        for i in range(num_successful_deliveries):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="delivery_complete",
                component="scheduler",
                message="Delivery completed successfully",
                context={
                    "status": "success",
                    "tips_generated": 5,
                    "recipients_sent": 10,
                },
                duration_ms=1000.0 + i,
            )

        # Add failed delivery complete events
        for i in range(num_failed_deliveries):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="delivery_complete",
                component="scheduler",
                message="Delivery failed",
                context={
                    "status": "failed",
                    "tips_generated": 0,
                    "recipients_sent": 0,
                },
                duration_ms=500.0 + i,
            )

        # Calculate metrics
        metrics = calculator.calculate()

        # Verify total deliveries
        total_deliveries = num_successful_deliveries + num_failed_deliveries
        assert metrics.total_deliveries == total_deliveries

        # Verify successful and failed counts
        assert metrics.successful_deliveries == num_successful_deliveries
        assert metrics.failed_deliveries == num_failed_deliveries

        # Verify success rate calculation
        if total_deliveries > 0:
            expected_success_rate = (num_successful_deliveries / total_deliveries) * 100
            assert metrics.success_rate == expected_success_rate
        else:
            assert metrics.success_rate == 0.0

        # Verify tips and emails are summed correctly
        expected_tips = num_successful_deliveries * 5
        expected_emails = num_successful_deliveries * 10
        assert metrics.total_tips_generated == expected_tips
        assert metrics.total_emails_sent == expected_emails

        # Verify average delivery duration is calculated
        if total_deliveries > 0:
            # All durations should be between 500 and 1000+num_successful_deliveries
            assert metrics.average_delivery_duration_ms > 0
        else:
            assert metrics.average_delivery_duration_ms == 0.0

    @given(
        num_successful_fetches=st.integers(min_value=0, max_value=50),
        num_failed_fetches=st.integers(min_value=0, max_value=50),
    )
    def test_fetch_metrics_accuracy(self, num_successful_fetches, num_failed_fetches):
        """
        For any set of fetch events in the event store, the metrics SHALL
        accurately count successful and failed fetches.
        """
        store = EventStore()
        calculator = MetricsCalculator(store)

        # Add successful fetch complete events
        for i in range(num_successful_fetches):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="fetch_complete",
                component="market_data_aggregator",
                message="Fetch completed successfully",
                context={"status": "success", "records_fetched": 100},
                duration_ms=500.0 + i,
            )

        # Add failed fetch complete events
        for i in range(num_failed_fetches):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="fetch_complete",
                component="market_data_aggregator",
                message="Fetch failed",
                context={"status": "failed", "records_fetched": 0},
                duration_ms=100.0 + i,
            )

        # Calculate metrics
        metrics = calculator.calculate()

        # Verify fetch counts
        total_fetches = num_successful_fetches + num_failed_fetches
        assert metrics.total_fetch_attempts == total_fetches
        assert metrics.successful_fetches == num_successful_fetches
        assert metrics.failed_fetches == num_failed_fetches

        # Verify average fetch duration
        if total_fetches > 0:
            assert metrics.average_fetch_duration_ms > 0
        else:
            assert metrics.average_fetch_duration_ms == 0.0

    @given(
        num_errors=st.integers(min_value=0, max_value=50),
    )
    def test_error_metrics_accuracy(self, num_errors):
        """
        For any set of error events in the event store, the metrics SHALL
        accurately count recent errors.
        """
        store = EventStore()
        calculator = MetricsCalculator(store)

        # Add error events
        for i in range(num_errors):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="error",
                component="test_component",
                message=f"Error {i}",
                context={"error_type": "test_error"},
            )

        # Calculate metrics
        metrics = calculator.calculate()

        # Verify error count
        assert metrics.recent_errors_count == num_errors

    @given(
        num_events=st.integers(min_value=1, max_value=100),
    )
    def test_uptime_calculation(self, num_events):
        """
        For any set of events, the metrics SHALL calculate uptime as the
        time elapsed since the start time.
        """
        store = EventStore()
        start_time = datetime.now(UTC) - timedelta(seconds=100)
        calculator = MetricsCalculator(store, start_time=start_time)

        # Add some events
        for _i in range(num_events):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="delivery_complete",
                component="scheduler",
                message="Delivery completed",
                context={"status": "success"},
            )

        # Calculate metrics
        metrics = calculator.calculate()

        # Verify uptime is approximately 100 seconds (allow some tolerance)
        assert 95 <= metrics.uptime_seconds <= 105

    @given(
        num_deliveries=st.integers(min_value=1, max_value=20),
    )
    def test_metrics_with_mixed_events(self, num_deliveries):
        """
        For any mix of different event types, the metrics SHALL correctly
        aggregate only the relevant events for each metric.
        """
        store = EventStore()
        calculator = MetricsCalculator(store)

        # Add a mix of different event types
        for _i in range(num_deliveries):
            trace_id = str(uuid.uuid4())

            # Add delivery start
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_start",
                component="scheduler",
                message="Delivery started",
                context={"delivery_type": "morning"},
            )

            # Add fetch events
            store.add_event(
                trace_id=trace_id,
                event_type="fetch_complete",
                component="market_data_aggregator",
                message="Fetch completed",
                context={"status": "success", "records_fetched": 50},
                duration_ms=300.0,
            )

            # Add analysis events
            store.add_event(
                trace_id=trace_id,
                event_type="analysis_complete",
                component="analysis_engine",
                message="Analysis completed",
                context={"indicators": ["RSI", "MACD"]},
                duration_ms=200.0,
            )

            # Add email sent event
            store.add_event(
                trace_id=trace_id,
                event_type="email_sent",
                component="email_service",
                message="Email sent",
                context={"recipient": "user@example.com"},
            )

            # Add delivery complete
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_complete",
                component="scheduler",
                message="Delivery completed",
                context={
                    "status": "success",
                    "tips_generated": 3,
                    "recipients_sent": 1,
                },
                duration_ms=1000.0,
            )

        # Calculate metrics
        metrics = calculator.calculate()

        # Verify that only delivery_complete events are counted for deliveries
        assert metrics.total_deliveries == num_deliveries
        assert metrics.successful_deliveries == num_deliveries
        assert metrics.failed_deliveries == 0

        # Verify that only fetch_complete events are counted for fetches
        assert metrics.total_fetch_attempts == num_deliveries
        assert metrics.successful_fetches == num_deliveries

        # Verify tips and emails
        assert metrics.total_tips_generated == num_deliveries * 3
        assert metrics.total_emails_sent == num_deliveries * 1

        # Verify success rate
        assert metrics.success_rate == 100.0

    @given(
        num_successful=st.integers(min_value=1, max_value=30),
        num_failed=st.integers(min_value=1, max_value=30),
    )
    def test_success_rate_precision(self, num_successful, num_failed):
        """
        For any combination of successful and failed deliveries, the success_rate
        SHALL be calculated with proper precision.
        """
        store = EventStore()
        calculator = MetricsCalculator(store)

        # Add successful deliveries
        for _i in range(num_successful):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="delivery_complete",
                component="scheduler",
                message="Success",
                context={"status": "success"},
                duration_ms=1000.0,
            )

        # Add failed deliveries
        for _i in range(num_failed):
            store.add_event(
                trace_id=str(uuid.uuid4()),
                event_type="delivery_complete",
                component="scheduler",
                message="Failed",
                context={"status": "failed"},
                duration_ms=500.0,
            )

        # Calculate metrics
        metrics = calculator.calculate()

        # Verify success rate
        total = num_successful + num_failed
        expected_rate = (num_successful / total) * 100
        assert abs(metrics.success_rate - expected_rate) < 0.01  # Allow small floating point error
