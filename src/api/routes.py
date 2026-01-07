"""API routes for dashboard and tip retrieval."""

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import MarketDataRecord, TipRecord
from src.models.market_data import DataSource, HistoricalData, MarketData
from src.models.trading_tip import DashboardTip, TipSource
from src.services.scheduler_service import SchedulerService
from src.services.user_service import UserService
from src.utils.event_store import EventStore

router = APIRouter()

# Global event store instance for debug endpoints
_event_store = EventStore()
_scheduler_service = None


def get_scheduler_service():
    """Get or create scheduler service instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService(event_store=_event_store)
    return _scheduler_service


# Pydantic models for user endpoints
class UserProfileCreate(BaseModel):
    """Request model for creating a user profile."""

    email: str
    morning_time: str | None = None
    evening_time: str | None = None
    asset_preferences: list[str] | None = None


class UserProfileUpdate(BaseModel):
    """Request model for updating user profile."""

    email: str | None = None
    morning_time: str | None = None
    evening_time: str | None = None
    asset_preferences: list[str] | None = None


class UserProfileResponse(BaseModel):
    """Response model for user profile."""

    id: str
    email: str
    morning_time: str | None
    evening_time: str | None
    asset_preferences: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def _parse_tip_record(record: TipRecord) -> DashboardTip:
    """Convert database TipRecord to DashboardTip model."""
    indicators = []
    if record.indicators:
        try:
            indicators = json.loads(record.indicators)
        except (json.JSONDecodeError, TypeError):
            indicators = []

    sources = []
    if record.sources:
        try:
            sources_data = json.loads(record.sources)
            sources = [TipSource(name=s["name"], url=s["url"]) for s in sources_data]
        except (json.JSONDecodeError, TypeError, KeyError):
            sources = []

    return DashboardTip(
        id=record.id,
        symbol=record.symbol,
        type=record.type,
        recommendation=record.recommendation,
        reasoning=record.reasoning,
        confidence=record.confidence,
        indicators=indicators,
        sources=sources,
        generated_at=record.generated_at,
        delivery_type=record.delivery_type,
    )


def _parse_market_data_record(record: MarketDataRecord) -> MarketData:
    """Convert database MarketDataRecord to MarketData model."""
    historical_data = HistoricalData(period="24h")
    if record.historical_data:
        try:
            hist_dict = json.loads(record.historical_data)
            historical_data = HistoricalData(
                period=hist_dict.get("period", "24h"),
                prices=hist_dict.get("prices", []),
                timestamps=hist_dict.get("timestamps", []),
            )
        except (json.JSONDecodeError, TypeError):
            pass

    return MarketData(
        symbol=record.symbol,
        type=record.type,
        current_price=record.current_price,
        price_change_24h=record.price_change_24h,
        volume_24h=record.volume_24h,
        historical_data=historical_data,
        source=DataSource(
            name=record.source_name, url=record.source_url, fetched_at=record.fetched_at
        ),
    )


@router.post("/tips/generate")
async def generate_tips(db: Session = Depends(get_db)):
    """
    Trigger tip generation pipeline on-demand.

    This endpoint fetches market data, analyzes it, and generates trading tips.
    Useful for dashboard initialization or manual refresh.

    Args:
        db: Database session

    Returns:
        Generated tips and market data
    """
    try:
        scheduler = get_scheduler_service()

        # Execute delivery without email (just generate and store tips)
        scheduler.db_session = db
        scheduler.execute_delivery("dashboard")

        # Return the newly generated tips
        query = db.query(TipRecord).order_by(desc(TipRecord.generated_at))
        tips = query.limit(20).all()
        dashboard_tips = [_parse_tip_record(tip) for tip in tips]

        return {
            "tips": dashboard_tips,
            "total": len(dashboard_tips),
            "generated": True,
            "message": "Tips generated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tips: {e!s}") from e


@router.get("/tips")
async def get_tips(
    asset_type: str | None = Query(None, description="Filter by 'crypto' or 'stock'"),
    days: int | None = Query(None, description="Number of past days to retrieve"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieve the latest market tips (one per symbol).

    For the dashboard, this returns only the most recent tip for each symbol.
    Use /api/tip-history for all historical tips.

    Args:
        asset_type: Filter by asset type (crypto/stock)
        days: Number of past days to retrieve
        skip: Number of results to skip (pagination)
        limit: Maximum number of results to return
        db: Database session

    Returns:
        List of latest trading tips with pagination info
    """
    # Get the most recent tip for each symbol
    from sqlalchemy import func

    subquery = db.query(
        TipRecord.symbol, func.max(TipRecord.generated_at).label("max_generated_at")
    )

    # Filter by asset type if provided
    if asset_type and asset_type in ["crypto", "stock"]:
        subquery = subquery.filter(TipRecord.type == asset_type)

    # Filter by date range if provided
    if days and days > 0:
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        subquery = subquery.filter(TipRecord.generated_at >= cutoff_date)

    subquery = subquery.group_by(TipRecord.symbol).subquery()

    # Join to get the full records
    query = db.query(TipRecord).join(
        subquery,
        (TipRecord.symbol == subquery.c.symbol)
        & (TipRecord.generated_at == subquery.c.max_generated_at),
    )

    # Get total count before pagination
    total = query.count()

    # Apply pagination and sorting
    tips = query.order_by(desc(TipRecord.generated_at)).offset(skip).limit(limit).all()

    # Convert to DashboardTip models
    dashboard_tips = [_parse_tip_record(tip) for tip in tips]

    return {"tips": dashboard_tips, "total": total, "skip": skip, "limit": limit}


@router.get("/market-data")
async def get_market_data(symbols: list[str] | None = Query(None), db: Session = Depends(get_db)):
    """
    Get current and historical market data.

    Args:
        symbols: List of symbols to retrieve data for
        db: Database session

    Returns:
        Market data with source attribution and historical trends
    """
    query = db.query(MarketDataRecord)

    # Filter by symbols if provided
    if symbols and len(symbols) > 0:
        query = query.filter(MarketDataRecord.symbol.in_(symbols))

    # Get the most recent data for each symbol
    records = query.order_by(MarketDataRecord.symbol, desc(MarketDataRecord.fetched_at)).all()

    # Group by symbol and keep only the most recent
    market_data_dict = {}
    for record in records:
        if record.symbol not in market_data_dict:
            market_data_dict[record.symbol] = record

    # Convert to MarketData models
    market_data = [_parse_market_data_record(record) for record in market_data_dict.values()]

    return {"market_data": market_data, "count": len(market_data)}


@router.get("/tip-history")
async def get_tip_history(
    days: int = Query(7, ge=1, le=90),
    asset_type: str | None = Query(None, description="Filter by 'crypto' or 'stock'"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Get historical tips from past N days.

    Args:
        days: Number of past days to retrieve
        asset_type: Optional filter by asset type (crypto/stock)
        skip: Number of results to skip (pagination)
        limit: Maximum number of results to return
        db: Database session

    Returns:
        Historical tips with timestamps and pagination info
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    query = db.query(TipRecord).filter(TipRecord.generated_at >= cutoff_date)

    # Filter by asset type if provided
    if asset_type and asset_type in ["crypto", "stock"]:
        query = query.filter(TipRecord.type == asset_type)

    # Get total count before pagination
    total = query.count()

    # Apply pagination and sorting
    tips = query.order_by(desc(TipRecord.generated_at)).offset(skip).limit(limit).all()

    # Convert to DashboardTip models
    dashboard_tips = [_parse_tip_record(tip) for tip in tips]

    return {"tips": dashboard_tips, "total": total, "skip": skip, "limit": limit, "days": days}


# User Configuration Management Endpoints


@router.post("/users", response_model=UserProfileResponse)
async def create_user(user_data: UserProfileCreate, db: Session = Depends(get_db)):
    """
    Create a new user profile.

    Args:
        user_data: User profile data
        db: Database session

    Returns:
        Created user profile
    """
    service = UserService(db_session=db)

    try:
        user = service.create_user(
            email=user_data.email,
            morning_time=user_data.morning_time,
            evening_time=user_data.evening_time,
            asset_preferences=user_data.asset_preferences,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """
    Retrieve user profile by ID.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        User profile
    """
    service = UserService(db_session=db)
    user = service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/users/email/{email}", response_model=UserProfileResponse)
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """
    Retrieve user profile by email address.

    Args:
        email: User email address
        db: Database session

    Returns:
        User profile
    """
    service = UserService(db_session=db)
    user = service.get_user_by_email(email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put("/users/{user_id}", response_model=UserProfileResponse)
async def update_user(user_id: str, user_data: UserProfileUpdate, db: Session = Depends(get_db)):
    """
    Update user profile.

    Args:
        user_id: User ID
        user_data: Updated user profile data
        db: Database session

    Returns:
        Updated user profile
    """
    service = UserService(db_session=db)

    try:
        user = service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update email if provided
        if user_data.email and user_data.email != user.email:
            user = service.update_email(user_id, user_data.email)

        # Update delivery times if provided
        if user_data.morning_time or user_data.evening_time:
            user = service.update_delivery_times(
                user_id, morning_time=user_data.morning_time, evening_time=user_data.evening_time
            )

        # Update asset preferences if provided
        if user_data.asset_preferences:
            user = service.update_asset_preferences(
                user_id, asset_preferences=user_data.asset_preferences
            )

        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    """
    Delete user profile.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Deletion status
    """
    service = UserService(db_session=db)

    try:
        success = service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Debug API Endpoints


@router.get("/debug/status")
async def debug_status():
    """
    Get current scheduler status and next delivery times.

    Returns:
        Scheduler status and next scheduled delivery times
    """
    try:
        # Get recent events to determine scheduler state
        recent_events = _event_store.get_recent_events(limit=100)

        # Find most recent delivery events
        delivery_events = [e for e in recent_events if "delivery" in e.event_type]

        # Determine if scheduler is running based on recent activity
        is_running = len(delivery_events) > 0

        # Extract next delivery times from context if available
        next_deliveries = []
        for event in delivery_events[-2:]:  # Check last 2 delivery events
            if event.context and "next_delivery_time" in event.context:
                next_deliveries.append(event.context["next_delivery_time"])

        return {
            "scheduler_running": is_running,
            "next_deliveries": next_deliveries,
            "total_events": _event_store.size(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving scheduler status: {e!s}"
        ) from e


@router.get("/debug/execution-history")
async def debug_execution_history(limit: int = Query(50, ge=1, le=500)):
    """
    Get recent delivery execution attempts.

    Args:
        limit: Maximum number of execution records to return

    Returns:
        Recent delivery attempts with timestamps and status
    """
    try:
        # Get delivery events
        delivery_events = _event_store.get_events_by_type("delivery_start", limit=limit)
        delivery_events.extend(_event_store.get_events_by_type("delivery_complete", limit=limit))

        # Sort by timestamp
        delivery_events.sort(key=lambda e: e.timestamp)

        # Format execution history
        execution_history = []
        for event in delivery_events[-limit:]:
            execution_history.append(
                {
                    "delivery_id": event.context.get("delivery_id", event.id),
                    "trace_id": event.trace_id,
                    "delivery_type": event.context.get("delivery_type", "unknown"),
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "status": "in_progress"
                    if event.event_type == "delivery_start"
                    else "completed",
                    "message": event.message,
                    "context": event.context,
                }
            )

        return {
            "execution_history": execution_history,
            "count": len(execution_history),
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving execution history: {e!s}"
        ) from e


@router.get("/debug/fetch-history")
async def debug_fetch_history(limit: int = Query(50, ge=1, le=500)):
    """
    Get recent market data fetch attempts.

    Args:
        limit: Maximum number of fetch records to return

    Returns:
        Recent fetch attempts with sources and results
    """
    try:
        # Get fetch events
        fetch_events = _event_store.get_events_by_type("fetch_start", limit=limit)
        fetch_events.extend(_event_store.get_events_by_type("fetch_complete", limit=limit))

        # Sort by timestamp
        fetch_events.sort(key=lambda e: e.timestamp)

        # Format fetch history
        fetch_history = []
        for event in fetch_events[-limit:]:
            fetch_history.append(
                {
                    "fetch_id": event.context.get("fetch_id", event.id),
                    "trace_id": event.trace_id,
                    "source": event.context.get("source", "unknown"),
                    "symbols": event.context.get("symbols", []),
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "status": "in_progress" if event.event_type == "fetch_start" else "completed",
                    "records_fetched": event.context.get("records_fetched", 0),
                    "message": event.message,
                }
            )

        return {"fetch_history": fetch_history, "count": len(fetch_history), "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving fetch history: {e!s}") from e


@router.get("/debug/errors")
async def debug_errors(limit: int = Query(50, ge=1, le=500)):
    """
    Get recent error events.

    Args:
        limit: Maximum number of error records to return

    Returns:
        Recent errors with timestamps and context
    """
    try:
        # Get error events
        error_events = _event_store.get_events_by_type("error", limit=limit)

        # Format error log
        error_log = []
        for event in error_events:
            error_log.append(
                {
                    "error_id": event.id,
                    "trace_id": event.trace_id,
                    "timestamp": event.timestamp,
                    "component": event.component,
                    "message": event.message,
                    "context": event.context,
                }
            )

        return {"errors": error_log, "count": len(error_log), "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving errors: {e!s}") from e


@router.get("/debug/metrics")
async def debug_metrics():
    """
    Get aggregated system metrics.

    Returns:
        Aggregated statistics about system operations
    """
    try:
        all_events = _event_store.get_all_events()

        # Calculate metrics
        total_deliveries = len([e for e in all_events if e.event_type == "delivery_complete"])
        successful_deliveries = len(
            [
                e
                for e in all_events
                if e.event_type == "delivery_complete" and e.context.get("status") == "success"
            ]
        )
        failed_deliveries = total_deliveries - successful_deliveries

        success_rate = (
            (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
        )

        # Calculate average delivery duration
        delivery_durations = [
            e.duration_ms
            for e in all_events
            if e.event_type == "delivery_complete" and e.duration_ms
        ]
        average_delivery_duration = (
            sum(delivery_durations) / len(delivery_durations) if delivery_durations else 0
        )

        # Count tips and emails
        total_tips = sum(
            e.context.get("tips_generated", 0)
            for e in all_events
            if e.event_type == "delivery_complete"
        )
        total_emails = len([e for e in all_events if e.event_type == "email_sent"])

        # Fetch statistics
        total_fetches = len([e for e in all_events if e.event_type == "fetch_complete"])
        successful_fetches = len(
            [
                e
                for e in all_events
                if e.event_type == "fetch_complete" and e.context.get("status") == "success"
            ]
        )
        failed_fetches = total_fetches - successful_fetches

        fetch_durations = [
            e.duration_ms for e in all_events if e.event_type == "fetch_complete" and e.duration_ms
        ]
        average_fetch_duration = (
            sum(fetch_durations) / len(fetch_durations) if fetch_durations else 0
        )

        # Error count
        recent_errors = len([e for e in all_events if e.event_type == "error"])

        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "success_rate": round(success_rate, 2),
            "average_delivery_duration_ms": round(average_delivery_duration, 2),
            "total_tips_generated": total_tips,
            "total_emails_sent": total_emails,
            "total_fetch_attempts": total_fetches,
            "successful_fetches": successful_fetches,
            "failed_fetches": failed_fetches,
            "average_fetch_duration_ms": round(average_fetch_duration, 2),
            "recent_errors_count": recent_errors,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {e!s}") from e


@router.get("/debug/trace/{trace_id}")
async def debug_trace(trace_id: str):
    """
    Get complete trace for a specific operation.

    Args:
        trace_id: The trace ID to retrieve

    Returns:
        All log entries for the trace in chronological order
    """
    try:
        # Get all events for this trace
        trace_events = _event_store.get_events_by_trace(trace_id)

        if not trace_events:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        # Format trace events
        trace_data = []
        for event in trace_events:
            trace_data.append(
                {
                    "event_id": event.id,
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "component": event.component,
                    "message": event.message,
                    "context": event.context,
                    "duration_ms": event.duration_ms,
                }
            )

        return {
            "trace_id": trace_id,
            "events": trace_data,
            "event_count": len(trace_data),
            "start_time": trace_events[0].timestamp if trace_events else None,
            "end_time": trace_events[-1].timestamp if trace_events else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving trace: {e!s}") from e
