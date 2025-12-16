"""SQLAlchemy database models for persistent storage."""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class TipRecord(Base):
    """Database model for storing trading tips."""
    __tablename__ = "tips"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # "crypto" or "stock"
    recommendation = Column(String, nullable=False)  # "BUY", "SELL", "HOLD"
    reasoning = Column(Text, nullable=False)
    confidence = Column(Integer, nullable=False)
    indicators = Column(String, nullable=True)  # JSON string
    sources = Column(String, nullable=True)  # JSON string
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    delivery_type = Column(String, nullable=False)  # "morning" or "evening"


class MarketDataRecord(Base):
    """Database model for storing market data."""
    __tablename__ = "market_data"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # "crypto" or "stock"
    current_price = Column(Float, nullable=False)
    price_change_24h = Column(Float, nullable=False)
    volume_24h = Column(Float, nullable=False)
    historical_data = Column(String, nullable=True)  # JSON string
    source_name = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DeliveryLog(Base):
    """Database model for tracking email delivery attempts."""
    __tablename__ = "delivery_logs"

    id = Column(String, primary_key=True)
    recipient = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # "success", "failed", "retrying"
    delivery_type = Column(String, nullable=False)  # "morning" or "evening"
    attempt_number = Column(Integer, nullable=False, default=1)
    error_message = Column(Text, nullable=True)
    attempted_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class UserProfile(Base):
    """Database model for user configuration."""
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    morning_time = Column(String, nullable=True)  # HH:MM format
    evening_time = Column(String, nullable=True)  # HH:MM format
    asset_preferences = Column(String, nullable=True)  # JSON string
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
