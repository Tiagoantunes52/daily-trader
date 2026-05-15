"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy import inspect, text

from src.database.models import Base
from src.utils.config import config

# Create database engine
engine = create_engine(
    config.database.database_url,
    echo=config.database.echo,
    connect_args={"check_same_thread": False} if "sqlite" in config.database.database_url else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_user_preferences():
    """Add preference columns to the users table for pre-existing databases."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    stmts = []
    if "morning_time" not in existing:
        stmts.append("ALTER TABLE users ADD COLUMN morning_time VARCHAR(5)")
    if "evening_time" not in existing:
        stmts.append("ALTER TABLE users ADD COLUMN evening_time VARCHAR(5)")
    if "asset_preferences" not in existing:
        stmts.append("ALTER TABLE users ADD COLUMN asset_preferences TEXT")
    if stmts:
        with engine.connect() as conn:
            for stmt in stmts:
                conn.execute(text(stmt))
            conn.commit()


def _migrate_sentiment():
    """Create sentiment table for pre-existing databases that lack it."""
    inspector = inspect(engine)
    if "sentiment" not in inspector.get_table_names():
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE sentiment ("
                "  id VARCHAR PRIMARY KEY,"
                "  symbol VARCHAR NOT NULL,"
                "  score FLOAT NOT NULL,"
                "  label VARCHAR NOT NULL,"
                "  key_theme TEXT,"
                "  headline_count INTEGER NOT NULL DEFAULT 0,"
                "  analyzed_at DATETIME NOT NULL"
                ")"
            ))
            conn.execute(text("CREATE INDEX ix_sentiment_symbol ON sentiment (symbol)"))
            conn.commit()


def init_db():
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)
    _migrate_user_preferences()
    _migrate_sentiment()


def get_db():
    """Get database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
