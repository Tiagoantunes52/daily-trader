"""Market data models for exchange information and historical trends."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class DataSource:
    """Represents the source of market data."""

    name: str
    url: str
    fetched_at: datetime


@dataclass
class HistoricalData:
    """Historical price and volume data for a given period."""

    period: Literal["24h", "7d", "30d"]
    prices: list[float] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)


@dataclass
class MarketData:
    """Complete market data for a symbol including current and historical information."""

    symbol: str
    type: Literal["crypto", "stock"]
    current_price: float
    price_change_24h: float
    volume_24h: float
    historical_data: HistoricalData
    source: DataSource
