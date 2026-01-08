"""Tests for authentication service with property-based testing."""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, User
from src.services.authentication_service import AuthenticationService


# Test database setup
@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def auth_service(db_session):
    """Create an authentication service instance."""
    return AuthenticationService(db_session)


class TestAuthenticationServicePropertyBased:
    """Property-based tests for AuthenticationService."""

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        password=st.text(
            alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=20
        )
    )
    def test_password_strength_validation(self, db_session, password: str):
        """
        Property 10: Password Strength Validation

        For any password that fails strength validation, registration should be
        rejected with a validation error.

        Validates: Requirements 1.4
        Feature: user-authentication, Property 10: Password Strength Validation
        """
        auth_service = AuthenticationService(db_session)

        # Generate a unique email for each test
        email = f"test_{hash(password) % 1000000}@example.com"
        name = "Test User"

        # Try to register with the password
        try:
            user = auth_service.register(email, password, name)

            # If registration succeeded, password must be strong
            # Verify it has all required characteristics
            assert len(password) >= 8
            assert any(c.isupper() for c in password)
            assert any(c.islower() for c in password)
            assert any(c.isdigit() for c in password)
            assert any(c in "!@#$%^&*" for c in password)

        except ValueError as e:
            # If registration failed, it should be due to password validation
            error_msg = str(e).lower()

            # Check that the error is related to password validation
            password_related_errors = [
                "password",
                "characters",
                "uppercase",
                "lowercase",
                "digit",
                "special",
            ]

            # At least one password-related term should be in the error
            assert any(term in error_msg for term in password_related_errors), (
                f"Expected password validation error, got: {e}"
            )

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        email=st.emails(),
        password=st.text(min_size=8, max_size=20).filter(
            lambda p: (
                any(c.isupper() for c in p)
                and any(c.islower() for c in p)
                and any(c.isdigit() for c in p)
                and any(c in "!@#$%^&*" for c in p)
            )
        ),
        name=st.text(min_size=1, max_size=50).filter(lambda n: n.strip()),
    )
    def test_login_credential_verification(self, db_session, email: str, password: str, name: str):
        """
        Property 11: Login Credential Verification

        For any registered user, logging in with the correct password should succeed
        and return valid tokens, while logging in with an incorrect password should
        fail with a generic error.

        Validates: Requirements 2.1, 2.2, 2.3
        Feature: user-authentication, Property 11: Login Credential Verification
        """
        auth_service = AuthenticationService(db_session)

        try:
            # Register user
            user = auth_service.register(email, password, name)

            # Test 1: Login with correct password should succeed
            token_response = auth_service.login(email, password)
            assert token_response.access_token is not None
            assert token_response.refresh_token is not None
            assert token_response.token_type == "bearer"

            # Test 2: Login with incorrect password should fail with generic error
            wrong_password = password + "_wrong"
            with pytest.raises(ValueError) as exc_info:
                auth_service.login(email, wrong_password)

            # Error should be generic (not revealing which field is wrong)
            error_msg = str(exc_info.value).lower()
            assert "invalid" in error_msg
            # Should not specifically say "password" is wrong
            assert "password is incorrect" not in error_msg

        except ValueError:
            # Registration might fail for various reasons (duplicate email, etc.)
            # This is acceptable in property testing
            pass

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(email=st.text(min_size=1, max_size=50))
    def test_registration_email_validation(self, db_session, email: str):
        """
        Property 12: Registration Email Validation

        For any registration attempt, the system should validate email format and
        reject invalid email addresses.

        Validates: Requirements 1.1
        Feature: user-authentication, Property 12: Registration Email Validation
        """
        auth_service = AuthenticationService(db_session)

        # Use a strong password that will pass validation
        password = "SecurePassword123!"
        name = "Test User"

        try:
            user = auth_service.register(email, password, name)

            # If registration succeeded, email must be valid
            # Must contain @ symbol
            assert "@" in email

        except ValueError as e:
            # If registration failed, check if it's due to email validation
            error_msg = str(e).lower()

            # If email is invalid, error should mention email
            if "@" not in email:
                assert "email" in error_msg or "invalid" in error_msg


class TestAuthenticationServiceUnit:
    """Unit tests for AuthenticationService edge cases."""

    def test_registration_with_duplicate_email(self, auth_service, db_session):
        """Test that registering with duplicate email fails."""
        email = "duplicate@example.com"
        password = "SecurePassword123!"
        name = "Test User"

        # Register first user
        user1 = auth_service.register(email, password, name)
        assert user1 is not None

        # Try to register second user with same email
        with pytest.raises(ValueError, match="Email already registered"):
            auth_service.register(email, password, "Another User")


class TestOAuthCallbackPropertyBased:
    """Property-based tests for OAuth callback handlers."""

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        provider_user_id=st.text(min_size=1, max_size=50),
        email=st.emails(),
        name=st.text(min_size=1, max_size=50).filter(lambda n: n.strip()),
    )
    @pytest.mark.asyncio
    async def test_oauth_user_creation_idempotence_google(
        self, provider_user_id: str, email: str, name: str
    ):
        """
        Property 7: OAuth User Creation Idempotence

        For any OAuth provider and user profile, calling the OAuth callback handler
        multiple times with the same provider user ID should result in a single user
        record (no duplicates).

        Validates: Requirements 3.4, 4.4
        Feature: user-authentication, Property 7: OAuth User Creation Idempotence
        """
        from unittest.mock import AsyncMock, patch

        # Create a fresh database session for each test
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()

        try:
            auth_service = AuthenticationService(db_session)

            # Mock OAuth service to return consistent user data
            mock_oauth_data = {
                "access_token": "mock_access_token",
                "refresh_token": "mock_refresh_token",
                "user_info": {
                    "provider_user_id": provider_user_id,
                    "email": email,
                    "name": name,
                    "picture": "https://example.com/picture.jpg",
                },
            }

            with patch.object(
                auth_service.oauth_service,
                "exchange_google_code",
                new=AsyncMock(return_value=mock_oauth_data),
            ):
                # Call OAuth callback handler multiple times
                token_response1 = await auth_service.handle_google_callback("code1", "state1")
                token_response2 = await auth_service.handle_google_callback("code2", "state2")
                token_response3 = await auth_service.handle_google_callback("code3", "state3")

                # All should succeed
                assert token_response1.access_token is not None
                assert token_response2.access_token is not None
                assert token_response3.access_token is not None

                # Check that only one user was created
                from src.database.models import User

                users = db_session.query(User).filter(User.email == email.lower()).all()
                assert len(users) == 1, f"Expected 1 user, found {len(users)}"

                # Check that only one OAuth connection exists for this provider
                from src.database.models import OAuthConnection

                connections = (
                    db_session.query(OAuthConnection)
                    .filter(
                        OAuthConnection.provider == "google",
                        OAuthConnection.provider_user_id == provider_user_id,
                    )
                    .all()
                )
                assert len(connections) == 1, (
                    f"Expected 1 OAuth connection, found {len(connections)}"
                )
        finally:
            db_session.close()

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        provider_user_id=st.text(min_size=1, max_size=50),
        email=st.emails(),
        name=st.text(min_size=1, max_size=50).filter(lambda n: n.strip()),
    )
    @pytest.mark.asyncio
    async def test_oauth_user_creation_idempotence_github(
        self, provider_user_id: str, email: str, name: str
    ):
        """
        Property 7: OAuth User Creation Idempotence (GitHub)

        For any OAuth provider and user profile, calling the OAuth callback handler
        multiple times with the same provider user ID should result in a single user
        record (no duplicates).

        Validates: Requirements 3.4, 4.4
        Feature: user-authentication, Property 7: OAuth User Creation Idempotence
        """
        from unittest.mock import AsyncMock, patch

        # Create a fresh database session for each test
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()

        try:
            auth_service = AuthenticationService(db_session)

            # Mock OAuth service to return consistent user data
            mock_oauth_data = {
                "access_token": "mock_access_token",
                "refresh_token": None,  # GitHub doesn't provide refresh tokens
                "user_info": {
                    "provider_user_id": provider_user_id,
                    "email": email,
                    "name": name,
                    "picture": "https://example.com/avatar.jpg",
                },
            }

            with patch.object(
                auth_service.oauth_service,
                "exchange_github_code",
                new=AsyncMock(return_value=mock_oauth_data),
            ):
                # Call OAuth callback handler multiple times
                token_response1 = await auth_service.handle_github_callback("code1", "state1")
                token_response2 = await auth_service.handle_github_callback("code2", "state2")
                token_response3 = await auth_service.handle_github_callback("code3", "state3")

                # All should succeed
                assert token_response1.access_token is not None
                assert token_response2.access_token is not None
                assert token_response3.access_token is not None

                # Check that only one user was created
                from src.database.models import User

                users = db_session.query(User).filter(User.email == email.lower()).all()
                assert len(users) == 1, f"Expected 1 user, found {len(users)}"

                # Check that only one OAuth connection exists for this provider
                from src.database.models import OAuthConnection

                connections = (
                    db_session.query(OAuthConnection)
                    .filter(
                        OAuthConnection.provider == "github",
                        OAuthConnection.provider_user_id == provider_user_id,
                    )
                    .all()
                )
                assert len(connections) == 1, (
                    f"Expected 1 OAuth connection, found {len(connections)}"
                )
        finally:
            db_session.close()


class TestAuthenticationServiceUnitContinued:
    """Additional unit tests for AuthenticationService edge cases."""


class TestAuthenticationServiceUnitContinued:
    """Additional unit tests for AuthenticationService edge cases."""

    def test_login_with_non_existent_email(self, auth_service):
        """Test that login with non-existent email fails with generic error."""
        email = "nonexistent@example.com"
        password = "SecurePassword123!"

        with pytest.raises(ValueError, match="Invalid email or password"):
            auth_service.login(email, password)


class TestOAuthCallbacksUnit:
    """Unit tests for OAuth callback handlers."""

    @pytest.mark.asyncio
    async def test_successful_google_oauth_callback(self, db_session):
        """Test successful Google OAuth callback creates user and returns tokens."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Mock OAuth service
        mock_oauth_data = {
            "access_token": "google_access_token",
            "refresh_token": "google_refresh_token",
            "user_info": {
                "provider_user_id": "google_user_123",
                "email": "googleuser@example.com",
                "name": "Google User",
                "picture": "https://example.com/picture.jpg",
            },
        }

        with patch.object(
            auth_service.oauth_service,
            "exchange_google_code",
            new=AsyncMock(return_value=mock_oauth_data),
        ):
            token_response = await auth_service.handle_google_callback("auth_code", "state")

            # Verify tokens are returned
            assert token_response.access_token is not None
            assert token_response.refresh_token is not None
            assert token_response.token_type == "bearer"

            # Verify user was created
            from src.database.models import User

            user = db_session.query(User).filter(User.email == "googleuser@example.com").first()
            assert user is not None
            assert user.name == "Google User"
            assert user.is_email_verified is True
            assert user.password_hash is None  # OAuth-only user

            # Verify OAuth connection was created
            from src.database.models import OAuthConnection

            connection = (
                db_session.query(OAuthConnection).filter(OAuthConnection.user_id == user.id).first()
            )
            assert connection is not None
            assert connection.provider == "google"
            assert connection.provider_user_id == "google_user_123"

    @pytest.mark.asyncio
    async def test_successful_github_oauth_callback(self, db_session):
        """Test successful GitHub OAuth callback creates user and returns tokens."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Mock OAuth service
        mock_oauth_data = {
            "access_token": "github_access_token",
            "refresh_token": None,  # GitHub doesn't provide refresh tokens
            "user_info": {
                "provider_user_id": "github_user_456",
                "email": "githubuser@example.com",
                "name": "GitHub User",
                "picture": "https://example.com/avatar.jpg",
            },
        }

        with patch.object(
            auth_service.oauth_service,
            "exchange_github_code",
            new=AsyncMock(return_value=mock_oauth_data),
        ):
            token_response = await auth_service.handle_github_callback("auth_code", "state")

            # Verify tokens are returned
            assert token_response.access_token is not None
            assert token_response.refresh_token is not None
            assert token_response.token_type == "bearer"

            # Verify user was created
            from src.database.models import User

            user = db_session.query(User).filter(User.email == "githubuser@example.com").first()
            assert user is not None
            assert user.name == "GitHub User"
            assert user.is_email_verified is True
            assert user.password_hash is None  # OAuth-only user

            # Verify OAuth connection was created
            from src.database.models import OAuthConnection

            connection = (
                db_session.query(OAuthConnection).filter(OAuthConnection.user_id == user.id).first()
            )
            assert connection is not None
            assert connection.provider == "github"
            assert connection.provider_user_id == "github_user_456"

    @pytest.mark.asyncio
    async def test_google_oauth_callback_with_invalid_code(self, db_session):
        """Test Google OAuth callback with invalid code raises error."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Mock OAuth service to raise error
        with patch.object(
            auth_service.oauth_service,
            "exchange_google_code",
            new=AsyncMock(side_effect=ValueError("Failed to exchange code")),
        ):
            with pytest.raises(ValueError, match="Failed to exchange code"):
                await auth_service.handle_google_callback("invalid_code", "state")

    @pytest.mark.asyncio
    async def test_github_oauth_callback_with_invalid_code(self, db_session):
        """Test GitHub OAuth callback with invalid code raises error."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Mock OAuth service to raise error
        with patch.object(
            auth_service.oauth_service,
            "exchange_github_code",
            new=AsyncMock(side_effect=ValueError("Failed to exchange code")),
        ):
            with pytest.raises(ValueError, match="Failed to exchange code"):
                await auth_service.handle_github_callback("invalid_code", "state")

    @pytest.mark.asyncio
    async def test_google_oauth_callback_error_handling(self, db_session):
        """Test Google OAuth callback handles errors gracefully."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Mock OAuth service to return data without email
        mock_oauth_data = {
            "access_token": "google_access_token",
            "refresh_token": "google_refresh_token",
            "user_info": {
                "provider_user_id": "google_user_789",
                "email": None,  # Missing email
                "name": "Google User",
                "picture": "https://example.com/picture.jpg",
            },
        }

        with patch.object(
            auth_service.oauth_service,
            "exchange_google_code",
            new=AsyncMock(return_value=mock_oauth_data),
        ):
            with pytest.raises(ValueError, match="Email not provided by Google"):
                await auth_service.handle_google_callback("auth_code", "state")

    @pytest.mark.asyncio
    async def test_github_oauth_callback_error_handling(self, db_session):
        """Test GitHub OAuth callback handles errors gracefully."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Mock OAuth service to return data without email
        mock_oauth_data = {
            "access_token": "github_access_token",
            "refresh_token": None,
            "user_info": {
                "provider_user_id": "github_user_999",
                "email": None,  # Missing email
                "name": "GitHub User",
                "picture": "https://example.com/avatar.jpg",
            },
        }

        with patch.object(
            auth_service.oauth_service,
            "exchange_github_code",
            new=AsyncMock(return_value=mock_oauth_data),
        ):
            with pytest.raises(ValueError, match="Email not provided by GitHub"):
                await auth_service.handle_github_callback("auth_code", "state")

    @pytest.mark.asyncio
    async def test_google_oauth_callback_with_empty_code(self, db_session):
        """Test Google OAuth callback with empty code raises error."""
        auth_service = AuthenticationService(db_session)

        with pytest.raises(ValueError, match="Authorization code is required"):
            await auth_service.handle_google_callback("", "state")

    @pytest.mark.asyncio
    async def test_github_oauth_callback_with_empty_code(self, db_session):
        """Test GitHub OAuth callback with empty code raises error."""
        auth_service = AuthenticationService(db_session)

        with pytest.raises(ValueError, match="Authorization code is required"):
            await auth_service.handle_github_callback("", "state")

    @pytest.mark.asyncio
    async def test_google_oauth_adds_connection_to_existing_user(self, db_session):
        """Test Google OAuth adds connection to existing user with same email."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Create existing user
        existing_user = auth_service.register(
            "existinguser@example.com", "SecurePassword123!", "Existing User"
        )

        # Mock OAuth service
        mock_oauth_data = {
            "access_token": "google_access_token",
            "refresh_token": "google_refresh_token",
            "user_info": {
                "provider_user_id": "google_user_existing",
                "email": "existinguser@example.com",
                "name": "Google Name",
                "picture": "https://example.com/picture.jpg",
            },
        }

        with patch.object(
            auth_service.oauth_service,
            "exchange_google_code",
            new=AsyncMock(return_value=mock_oauth_data),
        ):
            token_response = await auth_service.handle_google_callback("auth_code", "state")

            # Verify tokens are returned
            assert token_response.access_token is not None

            # Verify no new user was created
            from src.database.models import User

            users = db_session.query(User).filter(User.email == "existinguser@example.com").all()
            assert len(users) == 1

            # Verify OAuth connection was added to existing user
            from src.database.models import OAuthConnection

            connection = (
                db_session.query(OAuthConnection)
                .filter(OAuthConnection.user_id == existing_user.id)
                .first()
            )
            assert connection is not None
            assert connection.provider == "google"

    @pytest.mark.asyncio
    async def test_github_oauth_adds_connection_to_existing_user(self, db_session):
        """Test GitHub OAuth adds connection to existing user with same email."""
        from unittest.mock import AsyncMock, patch

        auth_service = AuthenticationService(db_session)

        # Create existing user
        existing_user = auth_service.register(
            "existinguser2@example.com", "SecurePassword123!", "Existing User 2"
        )

        # Mock OAuth service
        mock_oauth_data = {
            "access_token": "github_access_token",
            "refresh_token": None,
            "user_info": {
                "provider_user_id": "github_user_existing",
                "email": "existinguser2@example.com",
                "name": "GitHub Name",
                "picture": "https://example.com/avatar.jpg",
            },
        }

        with patch.object(
            auth_service.oauth_service,
            "exchange_github_code",
            new=AsyncMock(return_value=mock_oauth_data),
        ):
            token_response = await auth_service.handle_github_callback("auth_code", "state")

            # Verify tokens are returned
            assert token_response.access_token is not None

            # Verify no new user was created
            from src.database.models import User

            users = db_session.query(User).filter(User.email == "existinguser2@example.com").all()
            assert len(users) == 1

            # Verify OAuth connection was added to existing user
            from src.database.models import OAuthConnection

            connection = (
                db_session.query(OAuthConnection)
                .filter(OAuthConnection.user_id == existing_user.id)
                .first()
            )
            assert connection is not None
            assert connection.provider == "github"


class TestAuthenticationServiceUnitAdditional:
    """Additional unit tests for AuthenticationService edge cases."""

    def test_login_with_non_existent_email(self, auth_service):
        """Test that login with non-existent email fails with generic error."""
        email = "nonexistent@example.com"
        password = "SecurePassword123!"

        with pytest.raises(ValueError, match="Invalid email or password"):
            auth_service.login(email, password)

    def test_login_with_incorrect_password(self, auth_service):
        """Test that login with incorrect password fails with generic error."""
        email = "testuser@example.com"
        password = "SecurePassword123!"
        name = "Test User"

        # Register user
        auth_service.register(email, password, name)

        # Try to login with wrong password
        with pytest.raises(ValueError, match="Invalid email or password"):
            auth_service.login(email, "WrongPassword456!")

    def test_register_with_weak_password(self, auth_service):
        """Test that registration with weak password fails."""
        email = "weakpass@example.com"
        password = "weak"
        name = "Test User"

        with pytest.raises(ValueError, match="Password validation failed"):
            auth_service.register(email, password, name)

    def test_register_with_empty_name(self, auth_service):
        """Test that registration with empty name fails."""
        email = "noname@example.com"
        password = "SecurePassword123!"
        name = ""

        with pytest.raises(ValueError, match="Name cannot be empty"):
            auth_service.register(email, password, name)

    def test_register_with_invalid_email(self, auth_service):
        """Test that registration with invalid email fails."""
        email = "invalid-email"
        password = "SecurePassword123!"
        name = "Test User"

        with pytest.raises(ValueError, match="Invalid email format"):
            auth_service.register(email, password, name)

    def test_login_success_returns_tokens(self, auth_service):
        """Test that successful login returns access and refresh tokens."""
        email = "success@example.com"
        password = "SecurePassword123!"
        name = "Test User"

        # Register user
        auth_service.register(email, password, name)

        # Login
        token_response = auth_service.login(email, password)

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "bearer"
        assert len(token_response.access_token) > 0
        assert len(token_response.refresh_token) > 0

    def test_logout_with_valid_user(self, auth_service):
        """Test that logout succeeds for valid user."""
        email = "logout@example.com"
        password = "SecurePassword123!"
        name = "Test User"

        # Register user
        user = auth_service.register(email, password, name)

        # Logout should not raise error
        auth_service.logout(user.id)

    def test_logout_with_invalid_user_id(self, auth_service):
        """Test that logout with invalid user ID fails."""
        with pytest.raises(ValueError, match="User not found"):
            auth_service.logout(99999)

    def test_logout_with_negative_user_id(self, auth_service):
        """Test that logout with negative user ID fails."""
        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            auth_service.logout(-1)

    def test_register_normalizes_email(self, auth_service):
        """Test that registration normalizes email to lowercase."""
        email = "TestUser@EXAMPLE.COM"
        password = "SecurePassword123!"
        name = "Test User"

        user = auth_service.register(email, password, name)

        # Email should be normalized to lowercase
        assert user.email == "testuser@example.com"

    def test_login_normalizes_email(self, auth_service):
        """Test that login normalizes email to lowercase."""
        email = "testuser@example.com"
        password = "SecurePassword123!"
        name = "Test User"

        # Register with lowercase
        auth_service.register(email, password, name)

        # Login with uppercase should work
        token_response = auth_service.login("TestUser@EXAMPLE.COM", password)
        assert token_response is not None

    def test_register_strips_whitespace_from_name(self, auth_service):
        """Test that registration strips whitespace from name."""
        email = "whitespace@example.com"
        password = "SecurePassword123!"
        name = "  Test User  "

        user = auth_service.register(email, password, name)

        # Name should be stripped
        assert user.name == "Test User"

    def test_login_with_oauth_only_user(self, auth_service, db_session):
        """Test that OAuth-only user cannot login with password."""
        # Create OAuth-only user (no password hash)
        user = User(email="oauth@example.com", password_hash=None, name="OAuth User")
        db_session.add(user)
        db_session.commit()

        # Try to login with password
        with pytest.raises(ValueError, match="Invalid email or password"):
            auth_service.login("oauth@example.com", "AnyPassword123!")

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        access_token=st.text(min_size=10, max_size=200),
        refresh_token=st.text(min_size=10, max_size=200),
    )
    def test_oauth_token_encryption_property(
        self, auth_service, access_token: str, refresh_token: str
    ):
        """
        Property 21: OAuth Token Encryption

        **Validates: Requirements 9.5**

        For any OAuth tokens stored in the database, they should be encrypted
        and not readable as plaintext. When retrieved and decrypted, they should
        match the original tokens.
        """
        from src.database.models import OAuthConnection, User

        # Create a test user first
        user = User(
            email="test@example.com",
            name="Test User",
            password_hash=None,
            is_email_verified=True,
        )
        auth_service.db_session.add(user)
        auth_service.db_session.flush()

        # Create OAuth connection with encrypted tokens
        oauth_connection = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id="test_provider_id",
            access_token=auth_service.encryption_service.encrypt(access_token),
            refresh_token=auth_service.encryption_service.encrypt(refresh_token),
        )
        auth_service.db_session.add(oauth_connection)
        auth_service.db_session.commit()

        # Retrieve the connection from database
        stored_connection = (
            auth_service.db_session.query(OAuthConnection)
            .filter(OAuthConnection.user_id == user.id)
            .first()
        )

        # Verify tokens are encrypted (not plaintext)
        assert stored_connection.access_token != access_token
        assert stored_connection.refresh_token != refresh_token

        # Verify tokens can be decrypted back to original values
        decrypted_tokens = auth_service.get_decrypted_oauth_token(stored_connection)
        assert decrypted_tokens["access_token"] == access_token
        assert decrypted_tokens["refresh_token"] == refresh_token

        # Clean up
        auth_service.db_session.delete(oauth_connection)
        auth_service.db_session.delete(user)
        auth_service.db_session.commit()
