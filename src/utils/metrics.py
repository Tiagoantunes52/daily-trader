"""Metrics calculator for aggregating event store data."""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from src.utils.event_store import EventStore


@dataclass
class Metrics:
    """Represents aggregated system metrics."""

    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    average_delivery_duration_ms: float
    total_tips_generated: int
    total_emails_sent: int
    total_fetch_attempts: int
    successful_fetches: int
    failed_fetches: int
    average_fetch_duration_ms: float
    recent_errors_count: int
    uptime_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_deliveries": self.total_deliveries,
            "successful_deliveries": self.successful_deliveries,
            "failed_deliveries": self.failed_deliveries,
            "success_rate": self.success_rate,
            "average_delivery_duration_ms": self.average_delivery_duration_ms,
            "total_tips_generated": self.total_tips_generated,
            "total_emails_sent": self.total_emails_sent,
            "total_fetch_attempts": self.total_fetch_attempts,
            "successful_fetches": self.successful_fetches,
            "failed_fetches": self.failed_fetches,
            "average_fetch_duration_ms": self.average_fetch_duration_ms,
            "recent_errors_count": self.recent_errors_count,
            "uptime_seconds": self.uptime_seconds,
        }


class MetricsCalculator:
    """Calculates metrics from event store data."""

    def __init__(self, event_store: EventStore, start_time: Optional[datetime] = None):
        """
        Initialize the metrics calculator.

        Args:
            event_store: The event store to calculate metrics from
            start_time: Optional start time for uptime calculation (defaults to now)
        """
        self.event_store = event_store
        self.start_time = start_time or datetime.now(timezone.utc)

    def calculate(self) -> Metrics:
        """
        Calculate metrics from the event store.

        Returns:
            Metrics object with aggregated statistics
        """
        events = self.event_store.get_all_events()

        # Calculate delivery metrics
        delivery_completes = [e for e in events if e.event_type == "delivery_complete"]

        total_deliveries = len(delivery_completes)
        successful_deliveries = len(
            [e for e in delivery_completes if e.context.get("status") == "success"]
        )
        failed_deliveries = len(
            [e for e in delivery_completes if e.context.get("status") == "failed"]
        )

        # Calculate success rate
        success_rate = (
            (successful_deliveries / total_deliveries * 100)
            if total_deliveries > 0
            else 0.0
        )

        # Calculate average delivery duration
        delivery_durations = [
            e.duration_ms for e in delivery_completes if e.duration_ms is not None
        ]
        average_delivery_duration_ms = (
            sum(delivery_durations) / len(delivery_durations)
            if delivery_durations
            else 0.0
        )

        # Calculate tips and emails
        total_tips_generated = sum(
            e.context.get("tips_generated", 0) for e in delivery_completes
        )
        total_emails_sent = sum(
            e.context.get("recipients_sent", 0) for e in delivery_completes
        )

        # Calculate fetch metrics
        fetch_completes = [e for e in events if e.event_type == "fetch_complete"]
        total_fetch_attempts = len(fetch_completes)
        successful_fetches = len(
            [e for e in fetch_completes if e.context.get("status") == "success"]
        )
        failed_fetches = len(
            [e for e in fetch_completes if e.context.get("status") == "failed"]
        )

        # Calculate average fetch duration
        fetch_durations = [
            e.duration_ms for e in fetch_completes if e.duration_ms is not None
        ]
        average_fetch_duration_ms = (
            sum(fetch_durations) / len(fetch_durations) if fetch_durations else 0.0
        )

        # Calculate error metrics
        error_events = [e for e in events if e.event_type == "error"]
        recent_errors_count = len(error_events)

        # Calculate uptime
        current_time = datetime.now(timezone.utc)
        uptime_seconds = int((current_time - self.start_time).total_seconds())

        return Metrics(
            total_deliveries=total_deliveries,
            successful_deliveries=successful_deliveries,
            failed_deliveries=failed_deliveries,
            success_rate=success_rate,
            average_delivery_duration_ms=average_delivery_duration_ms,
            total_tips_generated=total_tips_generated,
            total_emails_sent=total_emails_sent,
            total_fetch_attempts=total_fetch_attempts,
            successful_fetches=successful_fetches,
            failed_fetches=failed_fetches,
            average_fetch_duration_ms=average_fetch_duration_ms,
            recent_errors_count=recent_errors_count,
            uptime_seconds=uptime_seconds,
        )
