"""In-memory event store for tracking system operations and logs."""

import threading
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class Event:
    """Represents a system event."""

    id: str
    timestamp: str
    trace_id: str
    event_type: str
    component: str
    message: str
    context: dict[str, Any]
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary, excluding None values."""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


class EventStore:
    """In-memory event store with configurable size limit and automatic purging."""

    def __init__(self, max_size: int = 10000, max_age_seconds: int = 3600):
        """
        Initialize the event store.

        Args:
            max_size: Maximum number of events to store (default 10000)
            max_age_seconds: Maximum age of events in seconds (default 1 hour)
        """
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self._events: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def add_event(
        self,
        trace_id: str,
        event_type: str,
        component: str,
        message: str,
        context: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> Event:
        """
        Add an event to the store.

        Args:
            trace_id: Trace ID for this event
            event_type: Type of event
            component: Component that generated the event
            message: Event message
            context: Optional context fields
            duration_ms: Optional duration in milliseconds

        Returns:
            The created Event object
        """
        with self._lock:
            event = Event(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                trace_id=trace_id,
                event_type=event_type,
                component=component,
                message=message,
                context=context or {},
                duration_ms=duration_ms,
            )
            self._events.append(event)
            return event

    def get_recent_events(self, limit: int = 100) -> list[Event]:
        """
        Get the most recent events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent events in chronological order (oldest first)
        """
        with self._lock:
            # Convert deque to list and return the most recent 'limit' events
            events_list = list(self._events)
            return events_list[-limit:] if limit > 0 else []

    def get_events_by_trace(self, trace_id: str) -> list[Event]:
        """
        Get all events for a specific trace ID.

        Args:
            trace_id: The trace ID to filter by

        Returns:
            List of events for the trace in chronological order
        """
        with self._lock:
            return [event for event in self._events if event.trace_id == trace_id]

    def get_events_by_type(self, event_type: str, limit: int = 100) -> list[Event]:
        """
        Get events of a specific type.

        Args:
            event_type: The event type to filter by
            limit: Maximum number of events to return

        Returns:
            List of events of the specified type in chronological order
        """
        with self._lock:
            matching_events = [event for event in self._events if event.event_type == event_type]
            return matching_events[-limit:] if limit > 0 else []

    def clear_old_events(self, max_age_seconds: int | None = None) -> int:
        """
        Remove events older than the specified age.

        Args:
            max_age_seconds: Maximum age in seconds (uses instance default if None)

        Returns:
            Number of events removed
        """
        max_age = max_age_seconds or self.max_age_seconds
        cutoff_time = datetime.now(UTC) - timedelta(seconds=max_age)

        with self._lock:
            initial_count = len(self._events)

            # Create a new deque with only recent events
            new_events = deque(maxlen=self.max_size)
            for event in self._events:
                # Parse the ISO8601 timestamp
                event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                if event_time > cutoff_time:
                    new_events.append(event)

            self._events = new_events
            return initial_count - len(self._events)

    def clear(self) -> None:
        """Clear all events from the store."""
        with self._lock:
            self._events.clear()

    def size(self) -> int:
        """Get the current number of events in the store."""
        with self._lock:
            return len(self._events)

    def get_all_events(self) -> list[Event]:
        """
        Get all events in the store.

        Returns:
            List of all events in chronological order
        """
        with self._lock:
            return list(self._events)
