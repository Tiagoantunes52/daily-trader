"""Tests for CSRF service."""

import time
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st

from src.services.csrf_service import CSRFService


class TestCSRFService:
    """Test cases for CSRF service."""

    def test_generate_token_returns_string(self):
        """Test that generate_token returns a string."""
        csrf_service = CSRFService()
        token = csrf_service.generate_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_validate_token_with_valid_token(self):
        """Test that validate_token returns True for valid tokens."""
        csrf_service = CSRFService()
        token = csrf_service.generate_token()
        assert csrf_service.validate_token(token) is True

    def test_validate_token_with_invalid_token(self):
        """Test that validate_token returns False for invalid tokens."""
        csrf_service = CSRFService()
        assert csrf_service.validate_token("invalid_token") is False

    def test_validate_token_with_expired_token(self):
        """Test that validate_token returns False for expired tokens."""
        csrf_service = CSRFService(token_lifetime=1)  # 1 second lifetime
        token = csrf_service.generate_token()

        # Wait for token to expire
        time.sleep(2)

        assert csrf_service.validate_token(token) is False

    def test_validate_token_with_session_id(self):
        """Test that validate_token works with session IDs."""
        csrf_service = CSRFService()
        session_id = "test_session_123"
        token = csrf_service.generate_token(session_id)

        # Valid with correct session ID
        assert csrf_service.validate_token(token, session_id) is True

        # Invalid with wrong session ID
        assert csrf_service.validate_token(token, "wrong_session") is False

        # Invalid without session ID
        assert csrf_service.validate_token(token) is False

    def test_get_token_header_name(self):
        """Test that get_token_header_name returns correct header name."""
        csrf_service = CSRFService()
        assert csrf_service.get_token_header_name() == "X-CSRF-Token"

    @given(st.text(min_size=1, max_size=100))
    def test_csrf_token_validation_property(self, session_id: str):
        """
        Property test for CSRF token validation.

        **Property 22: CSRF Token Validation**
        **Validates: Requirements 9.6**

        For any valid session ID, a token generated with that session ID
        should validate successfully when checked with the same session ID,
        and should fail when checked with a different session ID.
        """
        csrf_service = CSRFService()

        # Generate token with session ID
        token = csrf_service.generate_token(session_id)

        # Token should validate with correct session ID
        assert csrf_service.validate_token(token, session_id) is True

        # Token should not validate with different session ID
        different_session = session_id + "_different"
        assert csrf_service.validate_token(token, different_session) is False

        # Token should not validate without session ID if it was generated with one
        assert csrf_service.validate_token(token) is False

    @given(st.integers(min_value=1, max_value=3600))
    def test_csrf_token_expiration_property(self, token_lifetime: int):
        """
        Property test for CSRF token expiration.

        For any valid token lifetime, tokens should validate within the lifetime
        and should not validate after the lifetime expires.
        """
        import src.services.csrf_service as csrf_module

        csrf_service = CSRFService(token_lifetime=token_lifetime)

        # Generate token
        token = csrf_service.generate_token()

        # Token should be valid immediately
        assert csrf_service.validate_token(token) is True

        # Mock time to simulate expiration
        with patch.object(csrf_module, "time") as mock_time_module:
            # Set time to just after expiration
            mock_time_module.time.return_value = time.time() + token_lifetime + 1

            # Token should be expired
            assert csrf_service.validate_token(token) is False

    @given(st.text())
    def test_csrf_malformed_token_rejection_property(self, malformed_token: str):
        """
        Property test for malformed token rejection.

        For any arbitrary string that is not a properly formatted CSRF token,
        validation should return False.
        """
        csrf_service = CSRFService()

        # Skip empty strings and valid base64 strings that might accidentally be valid
        if not malformed_token or len(malformed_token) < 10:
            return

        # Try to avoid accidentally valid tokens by ensuring it's not base64
        try:
            import base64

            base64.b64decode(malformed_token.encode())
            # If it decodes successfully, skip this test case
            return
        except Exception:
            # Good, it's not valid base64, so it should be rejected
            pass

        # Malformed token should always be rejected
        assert csrf_service.validate_token(malformed_token) is False

    def test_csrf_token_round_trip_consistency(self):
        """
        Test that CSRF tokens maintain consistency in round-trip operations.

        A token generated and immediately validated should always be valid.
        """
        csrf_service = CSRFService()

        # Test multiple round trips
        for _ in range(10):
            token = csrf_service.generate_token()
            assert csrf_service.validate_token(token) is True

            # Test with session ID
            session_id = f"session_{_}"
            token_with_session = csrf_service.generate_token(session_id)
            assert csrf_service.validate_token(token_with_session, session_id) is True


class TestCSRFServiceUnitTests:
    """Unit tests for CSRF service security features."""

    def test_csrf_token_validation_success(self):
        """Test CSRF token validation with valid token."""
        csrf_service = CSRFService()
        token = csrf_service.generate_token()

        # Valid token should pass validation
        assert csrf_service.validate_token(token) is True

    def test_csrf_token_validation_failure_invalid_token(self):
        """Test CSRF token validation with invalid token."""
        csrf_service = CSRFService()

        # Invalid token should fail validation
        assert csrf_service.validate_token("invalid_token") is False

    def test_csrf_token_validation_failure_empty_token(self):
        """Test CSRF token validation with empty token."""
        csrf_service = CSRFService()

        # Empty token should fail validation
        assert csrf_service.validate_token("") is False

    def test_csrf_token_validation_failure_malformed_base64(self):
        """Test CSRF token validation with malformed base64."""
        csrf_service = CSRFService()

        # Malformed base64 should fail validation
        assert csrf_service.validate_token("not_base64!@#") is False

    def test_csrf_token_validation_with_session_id_mismatch(self):
        """Test CSRF token validation with session ID mismatch."""
        csrf_service = CSRFService()
        session_id = "test_session"
        token = csrf_service.generate_token(session_id)

        # Token with wrong session ID should fail
        assert csrf_service.validate_token(token, "wrong_session") is False

    def test_csrf_token_validation_without_expected_session_id(self):
        """Test CSRF token validation without expected session ID."""
        csrf_service = CSRFService()
        session_id = "test_session"
        token = csrf_service.generate_token(session_id)

        # Token with session ID but validated without should fail
        assert csrf_service.validate_token(token) is False

    def test_csrf_token_expiration(self):
        """Test CSRF token expiration."""
        csrf_service = CSRFService(token_lifetime=1)  # 1 second
        token = csrf_service.generate_token()

        # Token should be valid immediately
        assert csrf_service.validate_token(token) is True

        # Wait for expiration
        import time

        time.sleep(2)

        # Token should be expired
        assert csrf_service.validate_token(token) is False

    def test_csrf_header_name(self):
        """Test CSRF header name is correct."""
        csrf_service = CSRFService()
        assert csrf_service.get_token_header_name() == "X-CSRF-Token"
