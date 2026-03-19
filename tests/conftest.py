"""Pytest configuration and fixtures."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from main import app
from src.database.db import get_db
from src.database.models import Base


@pytest.fixture()
def test_db():
    """Create a file-based test database."""
    # Create a temporary file for the database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

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
    except:  # noqa: E722
        pass


@pytest.fixture()
def test_session(test_db):
    """Create a test database session."""
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = testing_session_local()

    yield session

    session.rollback()
    session.close()


@pytest.fixture()
def test_client(test_session):
    """Create a test client with test database."""

    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def mock_email_transport():
    """Auto-mock email transport mechanisms in tests."""
    # Mock SMTP
    with (
        patch("smtplib.SMTP") as mock_smtp_class,
        patch("src.services.email_service.requests.post") as mock_requests_post,
        patch("time.sleep") as mock_sleep,
    ):
        # Configure SMTP mock
        mock_smtp_instance = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance

        # Configure Mailgun mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_requests_post.return_value = mock_response

        yield {
            "smtp_class": mock_smtp_class,
            "smtp_instance": mock_smtp_instance,
            "requests_post": mock_requests_post,
            "sleep": mock_sleep,
        }


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Clear rate limiter state before each test."""
    from src.services.rate_limiter import rate_limiter

    rate_limiter.clear_all()
    yield
    rate_limiter.clear_all()
