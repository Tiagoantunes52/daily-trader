"""Property-based tests for in-memory event store."""

from hypothesis import given, strategies as st
from datetime import datetime, timezone, timedelta
import uuid
from src.utils.event_store import EventStore, Event


class TestEventStoreOrdering:
    """Tests for event store ordering and trace history."""

    @given(
        num_events=st.integers(min_value=1, max_value=50),
        num_traces=st.integers(min_value=1, max_value=5),
    )
    def test_trace_endpoint_returns_complete_history(self, num_events, num_traces):
        """
        **Feature: observability-logging, Property 15: Trace endpoint returns complete history**
        **Validates: Requirements 4.3, 4.4**

        For any trace ID, querying the trace endpoint SHALL return all log entries
        for that trace in chronological order.
        """
        store = EventStore()

        # Create multiple traces with events
        traces = [str(uuid.uuid4()) for _ in range(num_traces)]
        events_by_trace = {trace: [] for trace in traces}

        # Add events for each trace
        for i in range(num_events):
            trace_id = traces[i % num_traces]
            event = store.add_event(
                trace_id=trace_id,
                event_type="test_event",
                component="test_component",
                message=f"Event {i}",
                context={"index": i},
            )
            events_by_trace[trace_id].append(event)

        # Verify each trace returns all its events in chronological order
        for trace_id in traces:
            retrieved_events = store.get_events_by_trace(trace_id)

            # Verify all events for this trace are returned
            assert len(retrieved_events) == len(events_by_trace[trace_id])

            # Verify events are in chronological order (by timestamp)
            timestamps = [event.timestamp for event in retrieved_events]
            assert timestamps == sorted(timestamps), "Events not in chronological order"

            # Verify all events belong to the correct trace
            for event in retrieved_events:
                assert event.trace_id == trace_id

            # Verify event IDs match
            retrieved_ids = [event.id for event in retrieved_events]
            expected_ids = [event.id for event in events_by_trace[trace_id]]
            assert retrieved_ids == expected_ids

    @given(
        num_events=st.integers(min_value=1, max_value=30),
    )
    def test_recent_events_maintains_order(self, num_events):
        """
        For any set of events added to the store, get_recent_events SHALL return
        them in chronological order (oldest first).
        """
        store = EventStore()
        trace_id = str(uuid.uuid4())

        # Add events
        for i in range(num_events):
            store.add_event(
                trace_id=trace_id,
                event_type="test_event",
                component="test_component",
                message=f"Event {i}",
            )

        # Get recent events
        recent = store.get_recent_events(limit=num_events)

        # Verify count
        assert len(recent) == num_events

        # Verify chronological order
        timestamps = [event.timestamp for event in recent]
        assert timestamps == sorted(timestamps)

    @given(
        num_events=st.integers(min_value=1, max_value=50),
        limit=st.integers(min_value=1, max_value=20),
    )
    def test_recent_events_respects_limit(self, num_events, limit):
        """
        For any limit value, get_recent_events SHALL return at most that many events.
        """
        store = EventStore()
        trace_id = str(uuid.uuid4())

        # Add events
        for i in range(num_events):
            store.add_event(
                trace_id=trace_id,
                event_type="test_event",
                component="test_component",
                message=f"Event {i}",
            )

        # Get recent events with limit
        recent = store.get_recent_events(limit=limit)

        # Verify limit is respected
        assert len(recent) <= limit
        assert len(recent) == min(limit, num_events)

        # Verify they are the most recent events
        all_events = store.get_all_events()
        expected = all_events[-limit:] if limit > 0 else []
        assert [e.id for e in recent] == [e.id for e in expected]

    @given(
        num_events=st.integers(min_value=1, max_value=30),
        event_types=st.lists(
            st.sampled_from(["delivery_start", "delivery_complete", "fetch_start", "error"]),
            min_size=1,
            max_size=4,
            unique=True,
        ),
    )
    def test_events_by_type_filtering(self, num_events, event_types):
        """
        For any event type, get_events_by_type SHALL return only events of that type.
        """
        store = EventStore()
        trace_id = str(uuid.uuid4())

        # Add events of different types
        type_counts = {et: 0 for et in event_types}
        for i in range(num_events):
            event_type = event_types[i % len(event_types)]
            store.add_event(
                trace_id=trace_id,
                event_type=event_type,
                component="test_component",
                message=f"Event {i}",
            )
            type_counts[event_type] += 1

        # Verify filtering for each type
        for event_type in event_types:
            filtered = store.get_events_by_type(event_type)

            # All returned events should be of the correct type
            for event in filtered:
                assert event.event_type == event_type

            # Count should match
            assert len(filtered) == type_counts[event_type]

    @given(
        num_events=st.integers(min_value=1, max_value=30),
    )
    def test_clear_old_events_removes_expired(self, num_events):
        """
        For any max_age_seconds value, clear_old_events SHALL remove events older
        than that threshold.
        """
        store = EventStore(max_age_seconds=1)
        trace_id = str(uuid.uuid4())

        # Add events
        for i in range(num_events):
            store.add_event(
                trace_id=trace_id,
                event_type="test_event",
                component="test_component",
                message=f"Event {i}",
            )

        # Get initial count
        initial_count = store.size()
        assert initial_count == num_events

        # Clear old events with a very short age (should remove all after a small delay)
        # Use a negative max_age to ensure all events are considered old
        removed = store.clear_old_events(max_age_seconds=-1)

        # All events should be removed (they're older than -1 seconds, i.e., all past events)
        assert removed == initial_count
        assert store.size() == 0

    @given(
        num_events=st.integers(min_value=1, max_value=30),
    )
    def test_event_store_size_limit(self, num_events):
        """
        For any number of events exceeding max_size, the store SHALL maintain
        only the most recent max_size events.
        """
        max_size = 10
        store = EventStore(max_size=max_size)
        trace_id = str(uuid.uuid4())

        # Add more events than max_size
        num_to_add = min(num_events, 50)  # Cap at 50 to keep test reasonable
        for i in range(num_to_add):
            store.add_event(
                trace_id=trace_id,
                event_type="test_event",
                component="test_component",
                message=f"Event {i}",
                context={"index": i},
            )

        # Verify size doesn't exceed max_size
        assert store.size() <= max_size

        # If we added more than max_size, verify oldest events were removed
        if num_to_add > max_size:
            assert store.size() == max_size
            # Verify we have the most recent events
            events = store.get_all_events()
            # The first event should have index >= (num_to_add - max_size)
            first_index = events[0].context.get("index", 0)
            assert first_index >= (num_to_add - max_size)

    @given(
        num_traces=st.integers(min_value=2, max_value=5),
        events_per_trace=st.integers(min_value=1, max_value=10),
    )
    def test_trace_isolation(self, num_traces, events_per_trace):
        """
        For any set of traces, events from one trace SHALL not appear when
        querying another trace.
        """
        store = EventStore()
        traces = [str(uuid.uuid4()) for _ in range(num_traces)]

        # Add events for each trace
        for trace_id in traces:
            for i in range(events_per_trace):
                store.add_event(
                    trace_id=trace_id,
                    event_type="test_event",
                    component="test_component",
                    message=f"Event {i}",
                )

        # Verify trace isolation
        for trace_id in traces:
            events = store.get_events_by_trace(trace_id)

            # All events should belong to this trace
            assert len(events) == events_per_trace
            for event in events:
                assert event.trace_id == trace_id

            # No events from other traces
            for other_trace in traces:
                if other_trace != trace_id:
                    other_events = store.get_events_by_trace(other_trace)
                    for event in other_events:
                        assert event.trace_id != trace_id
