"""Pytest configuration and fixtures."""

import pytest
import tempfile
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.database.db import get_db
from main import app


@pytest.fixture(scope="function")
def test_db():
    """Create a file-based test database."""
    # Create a temporary file for the database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )
    
    # Enable foreign keys
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    engine.dispose()
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def test_session(test_db):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()
    
    yield session
    
    session.rollback()
    session.close()


@pytest.fixture
def test_client(test_session):
    """Create a test client with test database."""
    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client
    
    app.dependency_overrides.clear()
