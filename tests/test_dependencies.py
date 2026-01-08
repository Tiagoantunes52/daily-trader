"""Tests for authentication dependencies with property-based testing."""

import pytest
from fastapi import HTTPException
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.api.dependencies import get_current_user
from src.services.auth_user_service import AuthUserService
from src.services.password_service import PasswordService
from src.services.token_service import TokenService


class MockCredentials:
    """Mock HTTPAuthorizationCredentials for testing."""

    def __init__(self, token: str):
        self.credentials = token


class TestProtectedEndpointPropertyBased:
    """Property-based tests for protected endpoint authorization."""

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        email=st.emails(),
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    def test_protected_endpoint_authorization_no_token(self, test_session, email: str, name: str):
        """
        Property 5: Protected Endpoint Authorization

        For any protected endpoint and any request without a valid token,
        the endpoint should return 401 Unauthorized status.

        Validates: Requirements 6.1, 6.2, 6.3

        Feature: user-authentication, Property 5: Protected Endpoint Authorization
        """
        # Test with empty token
        credentials = MockCredentials("")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=test_session)

        assert exc_info.value.status_code == 401

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        invalid_token=st.text(min_size=1, max_size=100).filter(
            lambda x: not x.startswith("eyJ")  # Filter out potential valid JWT tokens
        ),
    )
    def test_protected_endpoint_authorization_invalid_token(self, test_session, invalid_token: str):
        """
        Property 5: Protected Endpoint Authorization (Invalid Token)

        For any protected endpoint and any request with an invalid token,
        the endpoint should return 401 Unauthorized status.

        Validates: Requirements 6.1, 6.2, 6.3

        Feature: user-authentication, Property 5: Protected Endpoint Authorization
        """
        credentials = MockCredentials(invalid_token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=test_session)

        assert exc_info.value.status_code == 401

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        email=st.emails(),
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        password=st.text(min_size=8, max_size=50),
    )
    def test_authenticated_request_processing(
        self, test_session, email: str, name: str, password: str
    ):
        """
        Property 6: Authenticated Request Processing

        For any protected endpoint and any request with a valid token,
        the endpoint should process the request and extract the correct
        user information from the token.

        Validates: Requirements 6.4, 6.5

        Feature: user-authentication, Property 6: Authenticated Request Processing
        """
        # Create a user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()

        password_hash = password_service.hash_password(password)

        try:
            user = user_service.create_user(
                email=email, password_hash=password_hash, name=name.strip()
            )
        except ValueError:
            # Email might already exist in this test run, skip
            pytest.skip("Email already exists")

        # Create a valid access token for the user
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Create credentials with valid token
        credentials = MockCredentials(access_token)

        # Get current user should succeed and return the correct user
        retrieved_user = get_current_user(credentials=credentials, db=test_session)

        # Verify the correct user was retrieved
        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email
        assert retrieved_user.name == user.name


class TestProtectedEndpointUnit:
    """Unit tests for protected endpoint authorization."""

    def test_request_without_token(self, test_session):
        """Test request without token returns 401."""
        credentials = MockCredentials("")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=test_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_request_with_invalid_token(self, test_session):
        """Test request with invalid token returns 401."""
        credentials = MockCredentials("invalid.token.here")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=test_session)

        assert exc_info.value.status_code == 401

    def test_request_with_expired_token(self, test_session):
        """Test request with expired token returns 401."""
        from datetime import timedelta

        # Create a user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()

        user = user_service.create_user(
            email="expired@example.com",
            password_hash=password_service.hash_password("password123"),
            name="Expired User",
        )

        # Create an expired token (1 millisecond expiration)
        token_service = TokenService()
        expired_token = token_service.create_access_token(
            user.id, expires_delta=timedelta(milliseconds=1)
        )

        # Wait for token to expire
        import time

        time.sleep(0.01)

        credentials = MockCredentials(expired_token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=test_session)

        assert exc_info.value.status_code == 401

    def test_request_with_valid_token(self, test_session):
        """Test request with valid token returns user."""
        # Create a user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()

        user = user_service.create_user(
            email="valid@example.com",
            password_hash=password_service.hash_password("password123"),
            name="Valid User",
        )

        # Create a valid token
        token_service = TokenService()
        valid_token = token_service.create_access_token(user.id)

        credentials = MockCredentials(valid_token)

        # Should successfully return the user
        retrieved_user = get_current_user(credentials=credentials, db=test_session)

        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email
        assert retrieved_user.name == user.name

    def test_request_with_refresh_token_type(self, test_session):
        """Test request with refresh token (wrong type) returns 401."""
        # Create a user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()

        user = user_service.create_user(
            email="refresh@example.com",
            password_hash=password_service.hash_password("password123"),
            name="Refresh User",
        )

        # Create a refresh token (wrong type for protected endpoints)
        token_service = TokenService()
        refresh_token = token_service.create_refresh_token(user.id)

        credentials = MockCredentials(refresh_token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=test_session)

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    def test_request_with_nonexistent_user_id(self, test_session):
        """Test request with token for non-existent user returns 401."""
        # Create a token for a user ID that doesn't exist
        token_service = TokenService()
        token = token_service.create_access_token(999999)

        credentials = MockCredentials(token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=credentials, db=test_session)

        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail
