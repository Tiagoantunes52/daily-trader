"""Database migration utilities for authentication tables."""

from sqlalchemy import inspect

from src.database.db import engine
from src.database.models import Base, OAuthConnection, User


def create_auth_tables():
    """Create authentication-related tables if they don't exist."""
    # Get existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Create User table if it doesn't exist
    if "users" not in existing_tables:
        User.__table__.create(engine, checkfirst=True)
        print("Created 'users' table")
    else:
        print("'users' table already exists")

    # Create OAuthConnection table if it doesn't exist
    if "oauth_connections" not in existing_tables:
        OAuthConnection.__table__.create(engine, checkfirst=True)
        print("Created 'oauth_connections' table")
    else:
        print("'oauth_connections' table already exists")


def init_auth_db():
    """Initialize authentication database schema."""
    Base.metadata.create_all(bind=engine, tables=[User.__table__, OAuthConnection.__table__])
    print("Authentication tables initialized")


def drop_auth_tables():
    """Drop authentication tables (for testing/cleanup)."""
    User.__table__.drop(engine, checkfirst=True)
    OAuthConnection.__table__.drop(engine, checkfirst=True)
    print("Authentication tables dropped")
