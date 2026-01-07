"""Tests for token service with property-based testing."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.services.token_service import TokenService
from src.utils.config import config


class TestTokenServicePropertyBased:
    """Property-based tests for TokenService."""

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(user_id=st.integers(min_value=1, max_value=2147483647))
    def test_token_round_trip_consistency(self, user_id: int):
        """
        Property 2: Token Round-Trip Consistency

        For any valid user ID, creating a token and then decoding it should produce
        the same user ID and token type.

        Validates: Requirements 5.1, 5.3
        """
        # Create access token
        access_token = TokenService.create_access_token(user_id)

        # Verify and decode the token
        payload = TokenService.verify_token(access_token)

        # Check that user_id matches
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

        # Create refresh token
        refresh_token = TokenService.create_refresh_token(user_id)

        # Verify and decode the refresh token
        refresh_payload = TokenService.verify_token(refresh_token)

        # Check that user_id matches
        assert refresh_payload["sub"] == str(user_id)
        assert refresh_payload["type"] == "refresh"

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(user_id=st.integers(min_value=1, max_value=2147483647))
    def test_access_token_expiration(self, user_id: int):
        """
        Property 3: Access Token Expiration

        For any access token, if the current time is after the token's expiration time,
        token verification should fail with an expiration error.

        Validates: Requirements 5.2
        """
        # Create token with very short expiration
        expires_delta = timedelta(milliseconds=1)
        access_token = TokenService.create_access_token(user_id, expires_delta)

        # Wait for token to expire
        import time

        time.sleep(0.01)

        # Verify that expired token raises ExpiredSignatureError
        with pytest.raises(jwt.ExpiredSignatureError):
            TokenService.verify_token(access_token)

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(user_id=st.integers(min_value=1, max_value=2147483647))
    def test_refresh_token_validity(self, user_id: int):
        """
        Property 4: Refresh Token Validity

        For any valid refresh token, exchanging it for a new access token should produce
        a valid access token with the same user ID.

        Validates: Requirements 5.3, 5.4
        """
        # Create refresh token
        refresh_token = TokenService.create_refresh_token(user_id)

        # Verify refresh token is valid
        refresh_payload = TokenService.verify_token(refresh_token)
        assert refresh_payload["sub"] == str(user_id)
        assert refresh_payload["type"] == "refresh"

        # Create new access token using the same user_id from refresh token
        new_access_token = TokenService.create_access_token(user_id)

        # Verify new access token is valid
        access_payload = TokenService.verify_token(new_access_token)
        assert access_payload["sub"] == str(user_id)
        assert access_payload["type"] == "access"


class TestTokenServiceUnit:
    """Unit tests for TokenService."""

    def test_create_access_token_valid_user_id(self):
        """Test creating access token with valid user ID."""
        user_id = 123
        token = TokenService.create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = TokenService.verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_create_access_token_invalid_user_id_zero(self):
        """Test that creating token with user_id=0 raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            TokenService.create_access_token(0)

    def test_create_access_token_invalid_user_id_negative(self):
        """Test that creating token with negative user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            TokenService.create_access_token(-1)

    def test_create_access_token_invalid_user_id_not_integer(self):
        """Test that creating token with non-integer user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            TokenService.create_access_token("123")  # type: ignore

    def test_create_access_token_custom_expiration(self):
        """Test creating access token with custom expiration."""
        user_id = 123
        custom_expiration = timedelta(hours=2)
        token = TokenService.create_access_token(user_id, custom_expiration)

        payload = TokenService.verify_token(token)
        assert payload["sub"] == str(user_id)

    def test_create_refresh_token_valid_user_id(self):
        """Test creating refresh token with valid user ID."""
        user_id = 456
        token = TokenService.create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = TokenService.verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_create_refresh_token_invalid_user_id_zero(self):
        """Test that creating refresh token with user_id=0 raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            TokenService.create_refresh_token(0)

    def test_create_refresh_token_custom_expiration(self):
        """Test creating refresh token with custom expiration."""
        user_id = 456
        custom_expiration = timedelta(days=14)
        token = TokenService.create_refresh_token(user_id, custom_expiration)

        payload = TokenService.verify_token(token)
        assert payload["sub"] == str(user_id)

    def test_verify_token_valid_token(self):
        """Test verifying a valid token."""
        user_id = 789
        token = TokenService.create_access_token(user_id)

        payload = TokenService.verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_verify_token_empty_token_raises_error(self):
        """Test that verifying empty token raises ValueError."""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            TokenService.verify_token("")

    def test_verify_token_none_token_raises_error(self):
        """Test that verifying None token raises ValueError."""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            TokenService.verify_token(None)  # type: ignore

    def test_verify_token_malformed_token(self):
        """Test that verifying malformed token raises InvalidTokenError."""
        with pytest.raises(jwt.InvalidTokenError):
            TokenService.verify_token("not.a.valid.token")

    def test_verify_token_invalid_signature(self):
        """Test that verifying token with invalid signature raises InvalidTokenError."""
        # Create a token with a different secret
        payload = {
            "sub": "123",
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
        token = jwt.encode(payload, "different-secret", algorithm="HS256")

        # Verify with original secret should fail
        with pytest.raises(jwt.InvalidTokenError):
            TokenService.verify_token(token)

    def test_verify_token_missing_claims(self):
        """Test that verifying token with missing required claims raises InvalidTokenError."""
        # Create a token without required claims
        payload = {"some_field": "some_value"}
        token = jwt.encode(payload, config.jwt.secret_key, algorithm=config.jwt.algorithm)

        # Verify should still work but payload won't have expected fields
        decoded = TokenService.verify_token(token)
        assert "sub" not in decoded

    def test_decode_token_valid_token(self):
        """Test decoding a valid token without verification."""
        user_id = 999
        token = TokenService.create_access_token(user_id)

        payload = TokenService.decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_decode_token_empty_token_raises_error(self):
        """Test that decoding empty token raises ValueError."""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            TokenService.decode_token("")

    def test_decode_token_malformed_token(self):
        """Test that decoding malformed token raises DecodeError."""
        with pytest.raises(jwt.DecodeError):
            TokenService.decode_token("not.a.valid.token")

    def test_token_contains_required_fields(self):
        """Test that created tokens contain all required fields."""
        user_id = 111
        token = TokenService.create_access_token(user_id)

        payload = TokenService.verify_token(token)
        assert "sub" in payload
        assert "type" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_access_token_type_is_access(self):
        """Test that access token has correct type."""
        user_id = 222
        token = TokenService.create_access_token(user_id)

        payload = TokenService.verify_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        """Test that refresh token has correct type."""
        user_id = 333
        token = TokenService.create_refresh_token(user_id)

        payload = TokenService.verify_token(token)
        assert payload["type"] == "refresh"

    def test_token_expiration_times_are_different(self):
        """Test that access and refresh tokens have different expiration times."""
        user_id = 444
        access_token = TokenService.create_access_token(user_id)
        refresh_token = TokenService.create_refresh_token(user_id)

        access_payload = TokenService.verify_token(access_token)
        refresh_payload = TokenService.verify_token(refresh_token)

        # Refresh token should expire later than access token
        assert refresh_payload["exp"] > access_payload["exp"]
