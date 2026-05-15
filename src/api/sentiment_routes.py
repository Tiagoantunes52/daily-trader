"""Sentiment API routes — consumed by the NemoClaw agent, not end users."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.services.sentiment_service import SentimentService
from src.utils.config import config

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


def _require_agent_key(x_agent_key: str | None = Header(default=None)) -> None:
    expected = config.agent.sentiment_api_key
    if not expected:
        raise HTTPException(status_code=503, detail="Sentiment API key not configured on server")
    if x_agent_key != expected:
        raise HTTPException(status_code=401, detail="Invalid agent key")


class SentimentPayload(BaseModel):
    symbol: str
    score: float = Field(..., ge=-1.0, le=1.0)
    label: str
    key_theme: str | None = None
    headline_count: int = Field(default=0, ge=0)


class SentimentResponse(BaseModel):
    symbol: str
    score: float
    label: str
    key_theme: str | None
    headline_count: int
    analyzed_at: datetime


@router.post("", status_code=201, dependencies=[Depends(_require_agent_key)])
async def push_sentiment(payload: SentimentPayload, db: Session = Depends(get_db)):
    svc = SentimentService(db)
    rec = svc.upsert(
        symbol=payload.symbol,
        score=payload.score,
        label=payload.label,
        key_theme=payload.key_theme,
        headline_count=payload.headline_count,
    )
    return SentimentResponse(
        symbol=rec.symbol,
        score=rec.score,
        label=rec.label,
        key_theme=rec.key_theme,
        headline_count=rec.headline_count,
        analyzed_at=rec.analyzed_at,
    )


@router.get("/{symbol}")
async def get_sentiment(
    symbol: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_agent_key),
):
    svc = SentimentService(db)
    rec = svc.get_latest(symbol)
    if not rec:
        raise HTTPException(status_code=404, detail=f"No recent sentiment data for {symbol}")
    return SentimentResponse(
        symbol=rec.symbol,
        score=rec.score,
        label=rec.label,
        key_theme=rec.key_theme,
        headline_count=rec.headline_count,
        analyzed_at=rec.analyzed_at,
    )


@router.get("")
async def list_sentiment(
    db: Session = Depends(get_db),
    _: None = Depends(_require_agent_key),
):
    """Return latest sentiment for all symbols with data in the last 6 hours."""
    from sqlalchemy import desc, func
    from src.database.models import SentimentRecord
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=6)
    subq = (
        db.query(SentimentRecord.symbol, func.max(SentimentRecord.analyzed_at).label("max_at"))
        .filter(SentimentRecord.analyzed_at >= cutoff)
        .group_by(SentimentRecord.symbol)
        .subquery()
    )
    records = db.query(SentimentRecord).join(
        subq,
        (SentimentRecord.symbol == subq.c.symbol)
        & (SentimentRecord.analyzed_at == subq.c.max_at),
    ).all()

    return [
        SentimentResponse(
            symbol=r.symbol,
            score=r.score,
            label=r.label,
            key_theme=r.key_theme,
            headline_count=r.headline_count,
            analyzed_at=r.analyzed_at,
        )
        for r in records
    ]
