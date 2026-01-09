"""Property-based tests for error handling and validation."""

from fastapi import status
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.api.error_handlers import AuthError


class TestRegistrationValidationErrorMessages:
    """Property-based tests for registration validation error messages."""

    @given(
        email=st.one_of(
            st.text(min_size=1, max_size=50).filter(
                lambda x: "@" not in x
            ),  # Invalid emails without @
            st.just(""),  # Empty email
            st.just("@"),  # Just @ symbol
            st.just("test@"),  # Missing domain
            st.just("@example.com"),  # Missing local part
        ),
        password=st.text(min_size=1, max_size=100),
        name=st.text(min_size=1, max_size=100),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_registration_validation_error_messages_property(
        self, test_client, email, password, name
    ):
        """
        Property 23: Registration Validation Error Messages

        For any registration attempt with invalid data, the system should return
        specific error messages for each invalid field.

        **Validates: Requirements 10.1**
        """
        # Arrange
        user_data = {
            "email": email,
            "password": password,
            "name": name,
        }

        # Act
        response = test_client.post("/auth/register", json=user_data)

        # Assert
        # Should return validation error (422) for invalid email format
        if (
            "@" not in email
            or email == ""
            or email == "@"
            or email.startswith("@")
            or email.endswith("@")
        ):
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            data = response.json()

            # Should have error details structure
            assert "detail" in data

            # For Pydantic validation errors, detail is a list
            if isinstance(data["detail"], list):
                # Find email validation error
                email_errors = [
                    error for error in data["detail"] if "email" in str(error.get("loc", []))
                ]
                assert len(email_errors) > 0, "Should have email validation error"

                # Should have specific error message
                for error in email_errors:
                    assert "msg" in error
                    assert len(error["msg"]) > 0
            else:
                # For custom error format
                assert isinstance(data["detail"], (str, dict))


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
