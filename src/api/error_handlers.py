"""Centralized error handling for authentication API endpoints."""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AuthError:
    """Standard error codes for authentication system."""

    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    UNAUTHORIZED = "UNAUTHORIZED"

    # Registration errors
    EMAIL_EXISTS = "EMAIL_EXISTS"
    WEAK_PASSWORD = "WEAK_PASSWORD"
    INVALID_EMAIL = "INVALID_EMAIL"
    INVALID_NAME = "INVALID_NAME"

    # OAuth errors
    OAUTH_ERROR = "OAUTH_ERROR"
    OAUTH_CONFIG_ERROR = "OAUTH_CONFIG_ERROR"
    OAUTH_PROVIDER_ERROR = "OAUTH_PROVIDER_ERROR"

    # User management errors
    USER_NOT_FOUND = "USER_NOT_FOUND"
    PROFILE_UPDATE_ERROR = "PROFILE_UPDATE_ERROR"
    PASSWORD_CHANGE_ERROR = "PASSWORD_CHANGE_ERROR"
    ACCOUNT_DELETION_ERROR = "ACCOUNT_DELETION_ERROR"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Security errors
    CSRF_ERROR = "CSRF_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Generic errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorResponse:
    """Standardized error response format."""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: dict[str, Any] | list[str] | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        """
        Initialize error response.

        Args:
            error_code: Standard error code from AuthError class
            message: Human-readable error message
            details: Additional error details (field-specific errors, etc.)
            status_code: HTTP status code
        """
        self.error_code = error_code
        self.message = message
        self.details = details
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        response = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            response["details"] = self.details
        return response

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict(),
        )


def create_validation_error_response(errors: list[dict[str, Any]]) -> ErrorResponse:
    """
    Create standardized validation error response from Pydantic validation errors.

    Args:
        errors: List of validation errors from Pydantic

    Returns:
        ErrorResponse with field-specific validation errors
    """
    field_errors = {}
    for error in errors:
        field_path = ".".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = error["msg"]

    return ErrorResponse(
        error_code=AuthError.VALIDATION_ERROR,
        message="Validation failed for one or more fields",
        details=field_errors,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def create_registration_validation_error(field: str, message: str) -> ErrorResponse:
    """
    Create registration-specific validation error.

    Args:
        field: Field name that failed validation
        message: Specific error message for the field

    Returns:
        ErrorResponse with field-specific error
    """
    return ErrorResponse(
        error_code=AuthError.VALIDATION_ERROR,
        message="Registration validation failed",
        details={field: message},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def create_login_error() -> ErrorResponse:
    """
    Create generic login error (security requirement - don't reveal which field is wrong).

    Returns:
        ErrorResponse with generic login error message
    """
    return ErrorResponse(
        error_code=AuthError.INVALID_CREDENTIALS,
        message="Invalid email or password",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def create_oauth_error(provider: str, message: str) -> ErrorResponse:
    """
    Create OAuth-specific error.

    Args:
        provider: OAuth provider name (google, github)
        message: Specific error message

    Returns:
        ErrorResponse with OAuth error details
    """
    return ErrorResponse(
        error_code=AuthError.OAUTH_ERROR,
        message=f"OAuth authentication failed for {provider}",
        details={"provider": provider, "error": message},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def create_token_error(message: str) -> ErrorResponse:
    """
    Create token-related error.

    Args:
        message: Specific error message

    Returns:
        ErrorResponse with token error
    """
    if "expired" in message.lower():
        error_code = AuthError.TOKEN_EXPIRED
    else:
        error_code = AuthError.INVALID_TOKEN

    return ErrorResponse(
        error_code=error_code,
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def create_conflict_error(resource: str, message: str) -> ErrorResponse:
    """
    Create conflict error (409).

    Args:
        resource: Resource that conflicts (email, etc.)
        message: Specific error message

    Returns:
        ErrorResponse with conflict error
    """
    if "email" in resource.lower():
        error_code = AuthError.EMAIL_EXISTS
    else:
        error_code = AuthError.VALIDATION_ERROR

    return ErrorResponse(
        error_code=error_code,
        message=message,
        status_code=status.HTTP_409_CONFLICT,
    )


def create_internal_error(message: str = "An unexpected error occurred") -> ErrorResponse:
    """
    Create internal server error.

    Args:
        message: Error message (should be generic for security)

    Returns:
        ErrorResponse with internal error
    """
    return ErrorResponse(
        error_code=AuthError.INTERNAL_ERROR,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI validation errors with standardized format.

    Args:
        request: FastAPI request object
        exc: RequestValidationError exception

    Returns:
        JSONResponse with standardized error format
    """
    error_response = create_validation_error_response(exc.errors())
    return JSONResponse(
        status_code=error_response.status_code,
        content=error_response.to_dict(),
    )


async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with standardized format.

    Args:
        request: FastAPI request object
        exc: ValidationError exception

    Returns:
        JSONResponse with standardized error format
    """
    error_response = create_validation_error_response(exc.errors())
    return JSONResponse(
        status_code=error_response.status_code,
        content=error_response.to_dict(),
    )


def handle_service_error(error: Exception, context: str = "operation") -> ErrorResponse:
    """
    Handle service layer errors and convert to appropriate error responses.

    Args:
        error: Exception from service layer
        context: Context of the operation (registration, login, etc.)

    Returns:
        ErrorResponse with appropriate error code and message
    """
    error_message = str(error)

    # Registration-specific errors
    if context == "registration":
        if (
            "already registered" in error_message.lower()
            or "already exists" in error_message.lower()
        ):
            return create_conflict_error("email", error_message)
        elif "password" in error_message.lower() and "validation" in error_message.lower():
            return create_registration_validation_error("password", error_message)
        elif "email" in error_message.lower() and "format" in error_message.lower():
            return create_registration_validation_error("email", error_message)
        elif "name" in error_message.lower() and "empty" in error_message.lower():
            return create_registration_validation_error("name", error_message)

    # Login-specific errors
    elif context == "login":
        if "invalid" in error_message.lower() and (
            "email" in error_message.lower() or "password" in error_message.lower()
        ):
            return create_login_error()

    # Token-specific errors
    elif context == "token":
        return create_token_error(error_message)

    # OAuth-specific errors
    elif context.startswith("oauth_"):
        provider = context.split("_")[1]
        return create_oauth_error(provider, error_message)

    # Profile update errors
    elif context == "profile_update":
        if "already in use" in error_message.lower():
            return create_conflict_error("email", error_message)

    # Default to validation error for ValueError, internal error for others
    if isinstance(error, ValueError):
        return ErrorResponse(
            error_code=AuthError.VALIDATION_ERROR,
            message=error_message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    else:
        return create_internal_error()
