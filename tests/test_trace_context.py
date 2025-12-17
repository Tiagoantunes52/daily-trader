"""Property-based tests for trace context management."""

import uuid
from hypothesis import given, strategies as st
from src.utils.trace_context import (
    create_trace,
    get_current_trace,
    set_trace,
    clear_trace,
)


class TestTraceContextManagement:
    """Tests for trace context management."""

    @given(num_operations=st.integers(min_value=1, max_value=10))
    def test_trace_ids_are_assigned_to_operations(self, num_operations):
        """
        **Feature: observability-logging, Property 14: Trace IDs are assigned to operations**
        **Validates: Requirements 4.1, 4.2**

        For any delivery operation, the system SHALL assign a unique trace ID
        that is included in all related log entries.
        """
        # Clear any existing trace
        clear_trace()

        # Create a trace ID
        trace_id = create_trace()

        # Verify trace ID is set
        assert get_current_trace() == trace_id

        # Verify trace ID is a valid UUID
        try:
            uuid.UUID(trace_id)
        except ValueError:
            raise AssertionError(f"Trace ID {trace_id} is not a valid UUID")

        # Simulate multiple operations within the same trace
        for _ in range(num_operations):
            # Verify trace ID persists across operations
            assert get_current_trace() == trace_id

        # Clear the trace
        clear_trace()

        # Verify trace is cleared
        assert get_current_trace() is None

    @given(trace_ids=st.lists(st.uuids(), min_size=1, max_size=5, unique=True))
    def test_trace_id_uniqueness(self, trace_ids):
        """
        For any set of trace IDs created, each SHALL be unique.
        """
        # Clear any existing trace
        clear_trace()

        created_traces = []
        for _ in range(len(trace_ids)):
            trace_id = create_trace()
            created_traces.append(trace_id)

        # Verify all created traces are unique
        assert len(created_traces) == len(set(created_traces))

        # Verify all are valid UUIDs
        for trace_id in created_traces:
            try:
                uuid.UUID(trace_id)
            except ValueError:
                raise AssertionError(f"Trace ID {trace_id} is not a valid UUID")

        clear_trace()

    @given(trace_id=st.uuids().map(str))
    def test_set_and_get_trace(self, trace_id):
        """
        For any trace ID, setting it SHALL make it retrievable via get_current_trace.
        """
        # Clear any existing trace
        clear_trace()

        # Set the trace ID
        set_trace(trace_id)

        # Verify it can be retrieved
        assert get_current_trace() == trace_id

        # Clear for cleanup
        clear_trace()

    def test_clear_trace_removes_context(self):
        """
        When clear_trace is called, the trace context SHALL be removed.
        """
        # Create a trace
        trace_id = create_trace()
        assert get_current_trace() == trace_id

        # Clear it
        clear_trace()

        # Verify it's gone
        assert get_current_trace() is None

    @given(num_traces=st.integers(min_value=2, max_value=5))
    def test_trace_context_isolation(self, num_traces):
        """
        For any sequence of trace creations, each new trace SHALL replace the previous one.
        """
        clear_trace()

        traces = []
        for _ in range(num_traces):
            trace_id = create_trace()
            traces.append(trace_id)
            # Verify current trace is the most recent one
            assert get_current_trace() == trace_id

        # Verify all traces are unique
        assert len(traces) == len(set(traces))

        clear_trace()
