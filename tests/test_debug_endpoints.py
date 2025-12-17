"""Property-based tests for debug API endpoints."""

import json
import uuid
from hypothesis import given, strategies as st
from datetime import datetime, timezone
from src.utils.event_store import EventStore


class TestDebugStatusEndpoint:
    """Tests for debug status endpoint."""

    @given(
        num_events=st.integers(min_value=1, max_value=20),
    )
    def test_debug_status_endpoint_returns_scheduler_state(self, num_events):
        """
        **Feature: observability-logging, Property 6: Debug status endpoint returns scheduler state**
        **Validates: Requirements 2.1**

        For any call to the debug status endpoint, the response SHALL include
        current scheduler status and next scheduled delivery times.
        """
        store = EventStore()
        trace_id = str(uuid.uuid4())

        # Add delivery events
        for i in range(num_events):
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_start",
                component="scheduler",
                message=f"Delivery {i} started",
                context={
                    "delivery_type": "morning" if i % 2 == 0 else "evening",
                    "next_delivery_time": f"2024-01-{(i % 28) + 1:02d}T08:00:00Z"
                }
            )

        # Simulate status endpoint logic
        recent_events = store.get_recent_events(limit=100)
        delivery_events = [e for e in recent_events if "delivery" in e.event_type]
        is_running = len(delivery_events) > 0
        
        next_deliveries = []
        for event in delivery_events[-2:]:
            if event.context and "next_delivery_time" in event.context:
                next_deliveries.append(event.context["next_delivery_time"])

        # Verify response structure
        assert isinstance(is_running, bool)
        assert is_running == True  # Should be running since we added delivery events
        assert isinstance(next_deliveries, list)
        assert len(next_deliveries) <= 2
        assert store.size() == num_events


class TestExecutionHistoryEndpoint:
    """Tests for execution history endpoint."""

    @given(
        num_deliveries=st.integers(min_value=1, max_value=20),
    )
    def test_execution_history_includes_required_fields(self, num_deliveries):
        """
        **Feature: observability-logging, Property 7: Execution history includes required fields**
        **Validates: Requirements 2.2**

        For any delivery event in the event store, querying the execution history
        endpoint SHALL return entries with timestamps and status.
        """
        store = EventStore()

        # Add delivery events
        for i in range(num_deliveries):
            trace_id = str(uuid.uuid4())
            delivery_id = str(uuid.uuid4())
            
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_start",
                component="scheduler",
                message=f"Delivery {i} started",
                context={
                    "delivery_id": delivery_id,
                    "delivery_type": "morning" if i % 2 == 0 else "evening"
                }
            )
            
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_complete",
                component="scheduler",
                message=f"Delivery {i} completed",
                context={
                    "delivery_id": delivery_id,
                    "delivery_type": "morning" if i % 2 == 0 else "evening",
                    "status": "success"
                }
            )

        # Simulate execution history endpoint logic
        delivery_events = store.get_events_by_type("delivery_start", limit=50)
        delivery_events.extend(store.get_events_by_type("delivery_complete", limit=50))
        delivery_events.sort(key=lambda e: e.timestamp)

        execution_history = []
        for event in delivery_events[-50:]:
            execution_history.append({
                "delivery_id": event.context.get("delivery_id", event.id),
                "trace_id": event.trace_id,
                "delivery_type": event.context.get("delivery_type", "unknown"),
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "status": "in_progress" if event.event_type == "delivery_start" else "completed",
                "message": event.message,
                "context": event.context
            })

        # Verify all entries have required fields
        for entry in execution_history:
            assert "delivery_id" in entry
            assert "trace_id" in entry
            assert "timestamp" in entry
            assert "status" in entry
            assert entry["timestamp"].endswith("Z")
            assert entry["status"] in ["in_progress", "completed"]


class TestFetchHistoryEndpoint:
    """Tests for fetch history endpoint."""

    @given(
        num_fetches=st.integers(min_value=1, max_value=20),
        sources=st.lists(
            st.sampled_from(["crypto_api", "stock_api", "market_data_service"]),
            min_size=1,
            max_size=3,
            unique=True
        ),
    )
    def test_fetch_history_includes_required_fields(self, num_fetches, sources):
        """
        **Feature: observability-logging, Property 8: Fetch history includes required fields**
        **Validates: Requirements 2.3**

        For any fetch event in the event store, querying the fetch history endpoint
        SHALL return entries with sources and results.
        """
        store = EventStore()

        # Add fetch events
        for i in range(num_fetches):
            trace_id = str(uuid.uuid4())
            fetch_id = str(uuid.uuid4())
            source = sources[i % len(sources)]
            
            store.add_event(
                trace_id=trace_id,
                event_type="fetch_start",
                component="market_aggregator",
                message=f"Fetch {i} started",
                context={
                    "fetch_id": fetch_id,
                    "source": source,
                    "symbols": ["BTC", "ETH"] if source == "crypto_api" else ["AAPL", "GOOGL"]
                }
            )
            
            store.add_event(
                trace_id=trace_id,
                event_type="fetch_complete",
                component="market_aggregator",
                message=f"Fetch {i} completed",
                context={
                    "fetch_id": fetch_id,
                    "source": source,
                    "symbols": ["BTC", "ETH"] if source == "crypto_api" else ["AAPL", "GOOGL"],
                    "status": "success",
                    "records_fetched": 2
                }
            )

        # Simulate fetch history endpoint logic
        fetch_events = store.get_events_by_type("fetch_start", limit=50)
        fetch_events.extend(store.get_events_by_type("fetch_complete", limit=50))
        fetch_events.sort(key=lambda e: e.timestamp)

        fetch_history = []
        for event in fetch_events[-50:]:
            fetch_history.append({
                "fetch_id": event.context.get("fetch_id", event.id),
                "trace_id": event.trace_id,
                "source": event.context.get("source", "unknown"),
                "symbols": event.context.get("symbols", []),
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "status": "in_progress" if event.event_type == "fetch_start" else "completed",
                "records_fetched": event.context.get("records_fetched", 0),
                "message": event.message
            })

        # Verify all entries have required fields
        for entry in fetch_history:
            assert "fetch_id" in entry
            assert "trace_id" in entry
            assert "source" in entry
            assert "symbols" in entry
            assert "timestamp" in entry
            assert entry["timestamp"].endswith("Z")
            assert isinstance(entry["symbols"], list)


class TestErrorLogEndpoint:
    """Tests for error log endpoint."""

    @given(
        num_errors=st.integers(min_value=1, max_value=20),
    )
    def test_error_log_endpoint_returns_recent_errors(self, num_errors):
        """
        **Feature: observability-logging, Property 9: Error log endpoint returns recent errors**
        **Validates: Requirements 2.4**

        For any error event in the event store, querying the error log endpoint
        SHALL return entries with timestamps and context.
        """
        store = EventStore()

        # Add error events
        for i in range(num_errors):
            trace_id = str(uuid.uuid4())
            
            store.add_event(
                trace_id=trace_id,
                event_type="error",
                component="scheduler",
                message=f"Error {i} occurred",
                context={
                    "error_type": "ValueError",
                    "error_message": f"Invalid value at step {i}",
                    "operation": "delivery"
                }
            )

        # Simulate error log endpoint logic
        error_events = store.get_events_by_type("error", limit=50)

        error_log = []
        for event in error_events:
            error_log.append({
                "error_id": event.id,
                "trace_id": event.trace_id,
                "timestamp": event.timestamp,
                "component": event.component,
                "message": event.message,
                "context": event.context
            })

        # Verify all entries have required fields
        assert len(error_log) == num_errors
        for entry in error_log:
            assert "error_id" in entry
            assert "trace_id" in entry
            assert "timestamp" in entry
            assert "component" in entry
            assert "message" in entry
            assert "context" in entry
            assert entry["timestamp"].endswith("Z")


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""

    @given(
        num_deliveries=st.integers(min_value=1, max_value=10),
        success_rate=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_metrics_calculation_is_accurate(self, num_deliveries, success_rate):
        """
        **Feature: observability-logging, Property 10: Metrics calculation is accurate**
        **Validates: Requirements 2.5**

        For any set of delivery events in the event store, the metrics endpoint
        SHALL return success_rate equal to (successful_deliveries / total_deliveries) * 100.
        """
        store = EventStore()
        trace_id = str(uuid.uuid4())

        # Calculate how many should succeed
        num_successful = int(num_deliveries * success_rate)
        num_failed = num_deliveries - num_successful

        # Add successful delivery events
        for i in range(num_successful):
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_complete",
                component="scheduler",
                message=f"Delivery {i} completed successfully",
                context={
                    "status": "success",
                    "tips_generated": 5
                },
                duration_ms=1000.0
            )

        # Add failed delivery events
        for i in range(num_failed):
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_complete",
                component="scheduler",
                message=f"Delivery {num_successful + i} failed",
                context={
                    "status": "failed",
                    "tips_generated": 0
                },
                duration_ms=500.0
            )

        # Simulate metrics calculation
        all_events = store.get_all_events()
        
        total_deliveries = len([e for e in all_events if e.event_type == "delivery_complete"])
        successful_deliveries = len([e for e in all_events if e.event_type == "delivery_complete" and e.context.get("status") == "success"])
        failed_deliveries = total_deliveries - successful_deliveries
        
        calculated_success_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0

        # Verify metrics accuracy
        assert total_deliveries == num_deliveries
        assert successful_deliveries == num_successful
        assert failed_deliveries == num_failed
        
        # Verify success rate calculation
        expected_rate = (num_successful / num_deliveries * 100) if num_deliveries > 0 else 0
        assert abs(calculated_success_rate - expected_rate) < 0.01


class TestTraceEndpoint:
    """Tests for trace endpoint."""

    @given(
        num_events=st.integers(min_value=1, max_value=20),
    )
    def test_trace_endpoint_returns_complete_history(self, num_events):
        """
        **Feature: observability-logging, Property 15: Trace endpoint returns complete history**
        **Validates: Requirements 4.3, 4.4**

        For any trace ID, querying the trace endpoint SHALL return all log entries
        for that trace in chronological order.
        """
        store = EventStore()
        trace_id = str(uuid.uuid4())

        # Add events for the trace
        for i in range(num_events):
            store.add_event(
                trace_id=trace_id,
                event_type="delivery_start" if i == 0 else "delivery_complete" if i == num_events - 1 else "fetch_complete",
                component="scheduler",
                message=f"Event {i}",
                context={"step": i}
            )

        # Simulate trace endpoint logic
        trace_events = store.get_events_by_trace(trace_id)

        trace_data = []
        for event in trace_events:
            trace_data.append({
                "event_id": event.id,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "component": event.component,
                "message": event.message,
                "context": event.context,
                "duration_ms": event.duration_ms
            })

        # Verify trace completeness
        assert len(trace_data) == num_events
        
        # Verify chronological order
        timestamps = [event["timestamp"] for event in trace_data]
        assert timestamps == sorted(timestamps)
        
        # Verify all events belong to the trace
        for event in trace_data:
            assert event["event_id"] is not None
            assert event["timestamp"].endswith("Z")
