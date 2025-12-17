"""Trace context management for tracking operations through the system."""

import contextvars
import uuid
from typing import Optional

# Context variable for storing the current trace ID
_trace_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)


def create_trace() -> str:
    """
    Generate a new unique trace ID and set it in the current context.

    Returns:
        A unique trace ID string (UUID4 format)
    """
    trace_id = str(uuid.uuid4())
    set_trace(trace_id)
    return trace_id


def get_current_trace() -> Optional[str]:
    """
    Get the current trace ID from the context.

    Returns:
        The current trace ID if set, None otherwise
    """
    return _trace_id_context.get()


def set_trace(trace_id: str) -> None:
    """
    Set the trace ID in the current context.

    Args:
        trace_id: The trace ID to set
    """
    _trace_id_context.set(trace_id)


def clear_trace() -> None:
    """Clear the trace ID from the current context."""
    _trace_id_context.set(None)
