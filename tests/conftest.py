"""Pytest configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.database.db import get_db
from main import app


@pytest.fixture(scope="session")
def test_db():
    """Create an in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_db):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()
    yield session
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
