"""Property-based tests for error handling and validation."""

from fastapi import status
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.api.error_handlers import AuthError


class TestLoginGenericErrorMessages:
    """Property-based tests for login generic error messages."""

    @given(
        email=st.emails(),  # Valid email format
        password=st.text(min_size=1, max_size=100),  # Any password
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_login_generic_error_messages_property(self, test_client, email, password):
        """
        Property 24: Login Generic Error Messages

        For any failed login attempt, the system should return a generic error message
        that does not reveal whether the email or password is incorrect.

        **Validates: Requirements 10.2**
        """
        # Arrange
        login_data = {
            "email": email,
            "password": password,
        }

        # Act
        response = test_client.post("/auth/login", json=login_data)

        # Assert
        # Should return unauthorized error for invalid credentials
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            data = response.json()

            # Should have error details
            assert "detail" in data

            if isinstance(data["detail"], dict):
                # Custom error format
                if "error" in data["detail"]:
                    assert data["detail"]["error"] == AuthError.INVALID_CREDENTIALS
                assert "message" in data["detail"]
                error_msg = data["detail"]["message"].lower()
            else:
                # String error format
                error_msg = data["detail"].lower()

            # Should be generic error message (security requirement)
            assert "invalid email or password" in error_msg or "invalid credentials" in error_msg

            # Should NOT reveal which field is wrong
            assert not any(
                specific in error_msg
                for specific in [
                    "email not found",
                    "user not found",
                    "password incorrect",
                    "wrong password",
                    "email does not exist",
                    "password is wrong",
                ]
            )
