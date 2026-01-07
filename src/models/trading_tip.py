"""Trading tip models for recommendations and analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class TipSource:
    """Source information for a trading tip."""

    name: str
    url: str


@dataclass
class TradingTip:
    """A trading recommendation based on market analysis."""

    symbol: str
    type: Literal["crypto", "stock"]
    recommendation: Literal["BUY", "SELL", "HOLD"]
    reasoning: str
    confidence: int  # 0-100
    indicators: list[str] = field(default_factory=list)
    sources: list[TipSource] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmailContent:
    """Email content combining tips and market data."""

    recipient: str
    subject: str
    delivery_type: Literal["morning", "evening"]
    generated_at: datetime = field(default_factory=datetime.now)
    tips: list[TradingTip] = field(default_factory=list)
    market_data: list = field(default_factory=list)


@dataclass
class DashboardTip:
    """Tip data formatted for dashboard display."""

    id: str
    symbol: str
    type: Literal["crypto", "stock"]
    recommendation: Literal["BUY", "SELL", "HOLD"]
    reasoning: str
    confidence: int  # 0-100
    generated_at: datetime
    delivery_type: Literal["morning", "evening"]
    indicators: list[str] = field(default_factory=list)
    sources: list[TipSource] = field(default_factory=list)
