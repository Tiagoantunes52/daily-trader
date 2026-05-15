"""Sentiment data service — read/write agent-supplied sentiment records."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.database.models import SentimentRecord


class SentimentService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def upsert(self, symbol: str, score: float, label: str, key_theme: str | None, headline_count: int) -> SentimentRecord:
        record = SentimentRecord(
            id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            score=max(-1.0, min(1.0, score)),
            label=label,
            key_theme=key_theme,
            headline_count=headline_count,
            analyzed_at=datetime.now(UTC),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest(self, symbol: str, max_age_hours: int = 6) -> SentimentRecord | None:
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
        return (
            self.db.query(SentimentRecord)
            .filter(
                SentimentRecord.symbol == symbol.upper(),
                SentimentRecord.analyzed_at >= cutoff,
            )
            .order_by(desc(SentimentRecord.analyzed_at))
            .first()
        )

    def get_latest_map(self, symbols: list[str], max_age_hours: int = 6) -> dict[str, SentimentRecord]:
        """Return {symbol: latest_record} for all symbols that have fresh data."""
        result = {}
        for sym in symbols:
            rec = self.get_latest(sym, max_age_hours)
            if rec:
                result[sym.upper()] = rec
        return result
