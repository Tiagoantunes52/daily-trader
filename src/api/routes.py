"""API routes for dashboard and tip retrieval."""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timedelta
from src.database.db import get_db
from src.database.models import TipRecord, MarketDataRecord, UserProfile
from src.models.trading_tip import DashboardTip, TipSource
from src.models.market_data import MarketData, DataSource, HistoricalData
from src.services.user_service import UserService
from pydantic import BaseModel, EmailStr
import json

router = APIRouter()


# Pydantic models for user endpoints
class UserProfileCreate(BaseModel):
    """Request model for creating a user profile."""
    email: str
    morning_time: Optional[str] = None
    evening_time: Optional[str] = None
    asset_preferences: Optional[list[str]] = None


class UserProfileUpdate(BaseModel):
    """Request model for updating user profile."""
    email: Optional[str] = None
    morning_time: Optional[str] = None
    evening_time: Optional[str] = None
    asset_preferences: Optional[list[str]] = None


class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    id: str
    email: str
    morning_time: Optional[str]
    evening_time: Optional[str]
    asset_preferences: Optional[list[str]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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
        delivery_type=record.delivery_type
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
                timestamps=hist_dict.get("timestamps", [])
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
            name=record.source_name,
            url=record.source_url,
            fetched_at=record.fetched_at
        )
    )


@router.get("/tips")
async def get_tips(
    asset_type: Optional[str] = Query(None, description="Filter by 'crypto' or 'stock'"),
    days: Optional[int] = Query(None, description="Number of past days to retrieve"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieve market tips with optional filtering.
    
    Args:
        asset_type: Filter by asset type (crypto/stock)
        days: Number of past days to retrieve
        skip: Number of results to skip (pagination)
        limit: Maximum number of results to return
        db: Database session
        
    Returns:
        List of trading tips with pagination info
    """
    query = db.query(TipRecord)
    
    # Filter by asset type if provided
    if asset_type and asset_type in ["crypto", "stock"]:
        query = query.filter(TipRecord.type == asset_type)
    
    # Filter by date range if provided
    if days and days > 0:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(TipRecord.generated_at >= cutoff_date)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination and sorting
    tips = query.order_by(desc(TipRecord.generated_at)).offset(skip).limit(limit).all()
    
    # Convert to DashboardTip models
    dashboard_tips = [_parse_tip_record(tip) for tip in tips]
    
    return {
        "tips": dashboard_tips,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/market-data")
async def get_market_data(
    symbols: Optional[list[str]] = Query(None),
    db: Session = Depends(get_db)
):
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
    records = query.order_by(
        MarketDataRecord.symbol,
        desc(MarketDataRecord.fetched_at)
    ).all()
    
    # Group by symbol and keep only the most recent
    market_data_dict = {}
    for record in records:
        if record.symbol not in market_data_dict:
            market_data_dict[record.symbol] = record
    
    # Convert to MarketData models
    market_data = [_parse_market_data_record(record) for record in market_data_dict.values()]
    
    return {
        "market_data": market_data,
        "count": len(market_data)
    }


@router.get("/tip-history")
async def get_tip_history(
    days: int = Query(7, ge=1, le=90),
    asset_type: Optional[str] = Query(None, description="Filter by 'crypto' or 'stock'"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
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
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
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
    
    return {
        "tips": dashboard_tips,
        "total": total,
        "skip": skip,
        "limit": limit,
        "days": days
    }


# User Configuration Management Endpoints

@router.post("/users", response_model=UserProfileResponse)
async def create_user(
    user_data: UserProfileCreate,
    db: Session = Depends(get_db)
):
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
            asset_preferences=user_data.asset_preferences
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db)
):
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
async def get_user_by_email(
    email: str,
    db: Session = Depends(get_db)
):
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
async def update_user(
    user_id: str,
    user_data: UserProfileUpdate,
    db: Session = Depends(get_db)
):
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
                user_id,
                morning_time=user_data.morning_time,
                evening_time=user_data.evening_time
            )
        
        # Update asset preferences if provided
        if user_data.asset_preferences:
            user = service.update_asset_preferences(
                user_id,
                asset_preferences=user_data.asset_preferences
            )
        
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db)
):
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
        raise HTTPException(status_code=400, detail=str(e))
