"""Unit tests for error handling and validation."""

from fastapi import status

from src.api.error_handlers import (
    AuthError,
    ErrorResponse,
    create_login_error,
    create_oauth_error,
    create_registration_validation_error,
    create_validation_error_response,
    handle_service_error,
)


class TestErrorHandlers:
    """Unit tests for error handler functions."""

    def test_create_login_error(self):
        """Test creation of generic login error."""
        error_response = create_login_error()

        assert error_response.error_code == AuthError.INVALID_CREDENTIALS
        assert error_response.message == "Invalid email or password"
        assert error_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert error_response.details is None

    def test_create_oauth_error(self):
        """Test creation of OAuth error."""
        provider = "google"
        message = "Authorization failed"

        error_response = create_oauth_error(provider, message)

        assert error_response.error_code == AuthError.OAUTH_ERROR
        assert error_response.message == f"OAuth authentication failed for {provider}"
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert error_response.details == {"provider": provider, "error": message}

    def test_create_registration_validation_error(self):
        """Test creation of registration validation error."""
        field = "password"
        message = "Password too weak"

        error_response = create_registration_validation_error(field, message)

        assert error_response.error_code == AuthError.VALIDATION_ERROR
        assert error_response.message == "Registration validation failed"
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert error_response.details == {field: message}

    def test_create_validation_error_response(self):
        """Test creation of validation error response from Pydantic errors."""
        pydantic_errors = [
            {"loc": ["email"], "msg": "Invalid email format", "type": "value_error"},
            {"loc": ["password"], "msg": "Password too short", "type": "value_error"},
        ]

        error_response = create_validation_error_response(pydantic_errors)

        assert error_response.error_code == AuthError.VALIDATION_ERROR
        assert error_response.message == "Validation failed for one or more fields"
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert error_response.details == {
            "email": "Invalid email format",
            "password": "Password too short",
        }

    def test_handle_service_error_registration_duplicate_email(self):
        """Test handling of duplicate email error during registration."""
        error = ValueError("Email already registered: test@example.com")

        error_response = handle_service_error(error, "registration")

        assert error_response.error_code == AuthError.EMAIL_EXISTS
        assert error_response.status_code == status.HTTP_409_CONFLICT
        assert "already registered" in error_response.message.lower()

    def test_handle_service_error_registration_password_validation(self):
        """Test handling of password validation error during registration."""
        error = ValueError("Password validation failed: too weak")

        error_response = handle_service_error(error, "registration")

        assert error_response.error_code == AuthError.VALIDATION_ERROR
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in error_response.details["password"].lower()

    def test_handle_service_error_login_invalid_credentials(self):
        """Test handling of invalid credentials error during login."""
        error = ValueError("Invalid email or password")

        error_response = handle_service_error(error, "login")

        assert error_response.error_code == AuthError.INVALID_CREDENTIALS
        assert error_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert error_response.message == "Invalid email or password"

    def test_handle_service_error_oauth_google(self):
        """Test handling of OAuth error for Google."""
        error = ValueError("Authorization code expired")

        error_response = handle_service_error(error, "oauth_google")

        assert error_response.error_code == AuthError.OAUTH_ERROR
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "google" in error_response.message.lower()
        assert error_response.details["provider"] == "google"

    def test_handle_service_error_profile_update_duplicate_email(self):
        """Test handling of duplicate email error during profile update."""
        error = ValueError("Email already in use by another user")

        error_response = handle_service_error(error, "profile_update")

        assert error_response.error_code == AuthError.EMAIL_EXISTS
        assert error_response.status_code == status.HTTP_409_CONFLICT
        assert "already in use" in error_response.message.lower()

    def test_handle_service_error_generic_value_error(self):
        """Test handling of generic ValueError."""
        error = ValueError("Some validation error")

        error_response = handle_service_error(error, "unknown_context")

        assert error_response.error_code == AuthError.VALIDATION_ERROR
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert error_response.message == "Some validation error"

    def test_handle_service_error_generic_exception(self):
        """Test handling of generic Exception."""
        error = RuntimeError("Unexpected error")

        error_response = handle_service_error(error, "unknown_context")

        assert error_response.error_code == AuthError.INTERNAL_ERROR
        assert error_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error_response.message == "An unexpected error occurred"

    def test_error_response_to_dict(self):
        """Test ErrorResponse to_dict method."""
        error_response = ErrorResponse(
            error_code=AuthError.VALIDATION_ERROR,
            message="Test error",
            details={"field": "error message"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        result = error_response.to_dict()

        assert result == {
            "error": AuthError.VALIDATION_ERROR,
            "message": "Test error",
            "details": {"field": "error message"},
        }

    def test_error_response_to_dict_no_details(self):
        """Test ErrorResponse to_dict method without details."""
        error_response = ErrorResponse(
            error_code=AuthError.INVALID_CREDENTIALS,
            message="Test error",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

        result = error_response.to_dict()

        assert result == {
            "error": AuthError.INVALID_CREDENTIALS,
            "message": "Test error",
        }

    def test_error_response_to_http_exception(self):
        """Test ErrorResponse to_http_exception method."""
        error_response = ErrorResponse(
            error_code=AuthError.VALIDATION_ERROR,
            message="Test error",
            details={"field": "error message"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        http_exception = error_response.to_http_exception()

        assert http_exception.status_code == status.HTTP_400_BAD_REQUEST
        assert http_exception.detail == {
            "error": AuthError.VALIDATION_ERROR,
            "message": "Test error",
            "details": {"field": "error message"},
        }


class TestValidationErrorMessages:
    """Unit tests for validation error messages."""

    def test_registration_with_invalid_email_format(self, test_client):
        """Test registration with invalid email format returns specific error."""
        user_data = {
            "email": "not-an-email",
            "password": "SecurePass123!",
            "name": "Test User",
        }

        response = test_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

        # Should have email validation error
        if isinstance(data["detail"], list):
            email_errors = [
                error for error in data["detail"] if "email" in str(error.get("loc", []))
            ]
            assert len(email_errors) > 0
            assert any("email" in error["msg"].lower() for error in email_errors)

    def test_registration_with_short_password(self, test_client):
        """Test registration with short password returns specific error."""
        user_data = {
            "email": "test@example.com",
            "password": "short",
            "name": "Test User",
        }

        response = test_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

        # Should have password validation error
        if isinstance(data["detail"], list):
            password_errors = [
                error for error in data["detail"] if "password" in str(error.get("loc", []))
            ]
            assert len(password_errors) > 0
            assert any("characters" in error["msg"].lower() for error in password_errors)

    def test_registration_with_empty_name(self, test_client):
        """Test registration with empty name returns specific error."""
        user_data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "name": "",
        }

        response = test_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

        # Should have name validation error
        if isinstance(data["detail"], list):
            name_errors = [error for error in data["detail"] if "name" in str(error.get("loc", []))]
            assert len(name_errors) > 0
            assert any("empty" in error["msg"].lower() for error in name_errors)

    def test_registration_with_duplicate_email(self, test_client):
        """Test registration with duplicate email returns conflict error."""
        # Register first user
        user_data = {
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
            "name": "First User",
        }
        first_response = test_client.post("/auth/register", json=user_data)
        assert first_response.status_code == status.HTTP_201_CREATED

        # Try to register with same email
        duplicate_data = {
            "email": "duplicate@example.com",
            "password": "DifferentPass123!",
            "name": "Second User",
        }
        response = test_client.post("/auth/register", json=duplicate_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data

        # Should contain email conflict message
        if isinstance(data["detail"], dict):
            assert data["detail"]["error"] == AuthError.EMAIL_EXISTS
            assert "email" in data["detail"]["message"].lower()
        else:
            assert "already" in data["detail"].lower()


class TestLoginGenericErrorMessages:
    """Unit tests for login generic error messages."""

    def test_login_with_nonexistent_email(self, test_client):
        """Test login with non-existent email returns generic error."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        }

        response = test_client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

        # Should be generic error message
        if isinstance(data["detail"], dict):
            assert data["detail"]["error"] == AuthError.INVALID_CREDENTIALS
            error_msg = data["detail"]["message"].lower()
        else:
            error_msg = data["detail"].lower()

        assert "invalid email or password" in error_msg

        # Should NOT reveal that email doesn't exist
        assert not any(
            specific in error_msg
            for specific in [
                "email not found",
                "user not found",
                "email does not exist",
            ]
        )

    def test_login_with_wrong_password(self, test_client):
        """Test login with wrong password returns generic error."""
        # Register user first
        user_data = {
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "name": "Test User",
        }
        test_client.post("/auth/register", json=user_data)

        # Try to login with wrong password
        login_data = {
            "email": "wrongpass@example.com",
            "password": "WrongPass123!",
        }
        response = test_client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

        # Should be generic error message
        if isinstance(data["detail"], dict):
            assert data["detail"]["error"] == AuthError.INVALID_CREDENTIALS
            error_msg = data["detail"]["message"].lower()
        else:
            error_msg = data["detail"].lower()

        assert "invalid email or password" in error_msg

        # Should NOT reveal that password is wrong
        assert not any(
            specific in error_msg
            for specific in [
                "password incorrect",
                "wrong password",
                "password is wrong",
            ]
        )

    def test_login_with_malformed_email(self, test_client):
        """Test login with malformed email returns validation error."""
        login_data = {
            "email": "not-an-email",
            "password": "SomePassword123!",
        }

        response = test_client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

        # Should have email validation error
        if isinstance(data["detail"], list):
            email_errors = [
                error for error in data["detail"] if "email" in str(error.get("loc", []))
            ]
            assert len(email_errors) > 0


class TestOAuthErrorHandling:
    """Unit tests for OAuth error handling."""

    def test_google_oauth_configuration_error(self, test_client):
        """Test Google OAuth with configuration error."""
        # This test would require mocking the OAuth service to simulate config error
        # For now, we'll test the error handler function directly
        error = ValueError("Google OAuth not configured")
        error_response = handle_service_error(error, "oauth_google")

        assert error_response.error_code == AuthError.OAUTH_ERROR
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "google" in error_response.message.lower()

    def test_github_oauth_configuration_error(self, test_client):
        """Test GitHub OAuth with configuration error."""
        # This test would require mocking the OAuth service to simulate config error
        # For now, we'll test the error handler function directly
        error = ValueError("GitHub OAuth not configured")
        error_response = handle_service_error(error, "oauth_github")

        assert error_response.error_code == AuthError.OAUTH_ERROR
        assert error_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "github" in error_response.message.lower()

    def test_oauth_callback_invalid_code(self, test_client):
        """Test OAuth callback with invalid authorization code."""
        # Test Google callback with invalid code
        response = test_client.get("/auth/google/callback?code=invalid_code&state=test_state")

        # Should return error (exact status depends on OAuth service implementation)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

        data = response.json()
        assert "detail" in data

        # Should contain OAuth-related error
        if isinstance(data["detail"], dict):
            error_msg = data["detail"]["message"].lower()
        else:
            error_msg = data["detail"].lower()

        assert any(keyword in error_msg for keyword in ["oauth", "google", "error"])

    def test_oauth_callback_missing_parameters(self, test_client):
        """Test OAuth callback with missing required parameters."""
        # Test Google callback without code parameter
        response = test_client.get("/auth/google/callback?state=test_state")

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

        # Should have parameter validation error
        if isinstance(data["detail"], list):
            code_errors = [error for error in data["detail"] if "code" in str(error.get("loc", []))]
            assert len(code_errors) > 0
