"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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


def init_db():
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
