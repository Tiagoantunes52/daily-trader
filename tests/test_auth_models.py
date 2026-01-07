"""Tests for authentication models and schemas."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, OAuthConnection, User
from src.models.auth_schemas import (
    PasswordChangeRequest,
    TokenResponse,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
    UserResponse,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, test_db):
        """Test creating a user record."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
        )
        test_db.add(user)
        test_db.commit()

        retrieved_user = test_db.query(User).filter_by(email="test@example.com").first()
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.name == "Test User"
        assert retrieved_user.password_hash == "hashed_password"
        assert retrieved_user.is_email_verified is False

    def test_user_email_unique(self, test_db):
        """Test that email is unique."""
        user1 = User(
            email="test@example.com",
            password_hash="hash1",
            name="User 1",
        )
        user2 = User(
            email="test@example.com",
            password_hash="hash2",
            name="User 2",
        )
        test_db.add(user1)
        test_db.commit()

        test_db.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()

    def test_user_timestamps(self, test_db):
        """Test that timestamps are set correctly."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
        )
        test_db.add(user)
        test_db.commit()

        retrieved_user = test_db.query(User).filter_by(email="test@example.com").first()
        assert retrieved_user.created_at is not None
        assert retrieved_user.updated_at is not None
        assert isinstance(retrieved_user.created_at, datetime)
        assert isinstance(retrieved_user.updated_at, datetime)

    def test_user_oauth_nullable_password(self, test_db):
        """Test that password_hash can be null for OAuth-only users."""
        user = User(
            email="oauth@example.com",
            password_hash=None,
            name="OAuth User",
        )
        test_db.add(user)
        test_db.commit()

        retrieved_user = test_db.query(User).filter_by(email="oauth@example.com").first()
        assert retrieved_user.password_hash is None


class TestOAuthConnectionModel:
    """Tests for OAuthConnection model."""

    def test_create_oauth_connection(self, test_db):
        """Test creating an OAuth connection."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
        )
        test_db.add(user)
        test_db.commit()

        oauth_conn = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id="google_123",
            access_token="access_token_123",
            refresh_token="refresh_token_123",
        )
        test_db.add(oauth_conn)
        test_db.commit()

        retrieved_conn = (
            test_db.query(OAuthConnection)
            .filter_by(provider="google", provider_user_id="google_123")
            .first()
        )
        assert retrieved_conn is not None
        assert retrieved_conn.user_id == user.id
        assert retrieved_conn.provider == "google"
        assert retrieved_conn.access_token == "access_token_123"

    def test_oauth_connection_cascade_delete(self, test_db):
        """Test that OAuth connections are deleted when user is deleted."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
        )
        test_db.add(user)
        test_db.commit()

        oauth_conn = OAuthConnection(
            user_id=user.id,
            provider="github",
            provider_user_id="github_456",
        )
        test_db.add(oauth_conn)
        test_db.commit()

        user_id = user.id
        test_db.delete(user)
        test_db.commit()

        # Verify OAuth connection is also deleted
        remaining_conn = test_db.query(OAuthConnection).filter_by(user_id=user_id).first()
        assert remaining_conn is None

    def test_user_multiple_oauth_connections(self, test_db):
        """Test that a user can have multiple OAuth connections."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
        )
        test_db.add(user)
        test_db.commit()

        google_conn = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id="google_123",
        )
        github_conn = OAuthConnection(
            user_id=user.id,
            provider="github",
            provider_user_id="github_456",
        )
        test_db.add(google_conn)
        test_db.add(github_conn)
        test_db.commit()

        retrieved_user = test_db.query(User).filter_by(email="test@example.com").first()
        assert len(retrieved_user.oauth_connections) == 2
        providers = {conn.provider for conn in retrieved_user.oauth_connections}
        assert providers == {"google", "github"}


class TestAuthSchemas:
    """Tests for authentication Pydantic schemas."""

    def test_user_register_request_valid(self):
        """Test valid user registration request."""
        req = UserRegisterRequest(
            email="test@example.com",
            password="SecurePassword123",
            name="Test User",
        )
        assert req.email == "test@example.com"
        assert req.password == "SecurePassword123"
        assert req.name == "Test User"

    def test_user_register_request_invalid_email(self):
        """Test registration with invalid email."""
        with pytest.raises(ValueError):
            UserRegisterRequest(
                email="invalid-email",
                password="SecurePassword123",
                name="Test User",
            )

    def test_user_register_request_short_password(self):
        """Test registration with short password."""
        with pytest.raises(ValueError):
            UserRegisterRequest(
                email="test@example.com",
                password="short",
                name="Test User",
            )

    def test_user_register_request_empty_name(self):
        """Test registration with empty name."""
        with pytest.raises(ValueError):
            UserRegisterRequest(
                email="test@example.com",
                password="SecurePassword123",
                name="",
            )

    def test_user_login_request_valid(self):
        """Test valid user login request."""
        req = UserLoginRequest(
            email="test@example.com",
            password="SecurePassword123",
        )
        assert req.email == "test@example.com"
        assert req.password == "SecurePassword123"

    def test_token_response(self):
        """Test token response model."""
        resp = TokenResponse(
            access_token="access_123",
            refresh_token="refresh_456",
        )
        assert resp.access_token == "access_123"
        assert resp.refresh_token == "refresh_456"
        assert resp.token_type == "bearer"

    def test_user_response(self):
        """Test user response model."""
        now = datetime.now(UTC)
        resp = UserResponse(
            id=1,
            email="test@example.com",
            name="Test User",
            created_at=now,
            is_email_verified=False,
            oauth_providers=["google"],
        )
        assert resp.id == 1
        assert resp.email == "test@example.com"
        assert resp.name == "Test User"
        assert resp.oauth_providers == ["google"]

    def test_user_profile_update_request_valid(self):
        """Test valid profile update request."""
        req = UserProfileUpdateRequest(
            name="Updated Name",
            email="updated@example.com",
        )
        assert req.name == "Updated Name"
        assert req.email == "updated@example.com"

    def test_user_profile_update_request_partial(self):
        """Test partial profile update request."""
        req = UserProfileUpdateRequest(name="Updated Name")
        assert req.name == "Updated Name"
        assert req.email is None

    def test_password_change_request_valid(self):
        """Test valid password change request."""
        req = PasswordChangeRequest(
            current_password="OldPassword123",
            new_password="NewPassword456",
        )
        assert req.current_password == "OldPassword123"
        assert req.new_password == "NewPassword456"

    def test_password_change_request_short_new_password(self):
        """Test password change with short new password."""
        with pytest.raises(ValueError):
            PasswordChangeRequest(
                current_password="OldPassword123",
                new_password="short",
            )
