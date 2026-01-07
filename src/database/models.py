"""SQLAlchemy database models for persistent storage."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

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
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
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
    fetched_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class DeliveryLog(Base):
    """Database model for tracking email delivery attempts."""

    __tablename__ = "delivery_logs"

    id = Column(String, primary_key=True)
    recipient = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # "success", "failed", "retrying"
    delivery_type = Column(String, nullable=False)  # "morning" or "evening"
    attempt_number = Column(Integer, nullable=False, default=1)
    error_message = Column(Text, nullable=True)
    attempted_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class UserProfile(Base):
    """Database model for user configuration."""

    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    morning_time = Column(String, nullable=True)  # HH:MM format
    evening_time = Column(String, nullable=True)  # HH:MM format
    asset_preferences = Column(String, nullable=True)  # JSON string
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class User(Base):
    """Database model for user authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_email_verified = Column(Boolean, default=False)

    oauth_connections = relationship(
        "OAuthConnection", back_populates="user", cascade="all, delete-orphan"
    )


class OAuthConnection(Base):
    """Database model for OAuth provider connections."""

    __tablename__ = "oauth_connections"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'google' or 'github'
    provider_user_id = Column(String(255), nullable=False)
    access_token = Column(String(1024), nullable=True)  # Encrypted
    refresh_token = Column(String(1024), nullable=True)  # Encrypted
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="oauth_connections")
