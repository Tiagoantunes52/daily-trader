"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import User
from src.services.auth_user_service import AuthUserService
from src.services.csrf_service import CSRFService
from src.services.rate_limiter import rate_limiter
from src.services.token_service import TokenService
from src.utils.config import config

# HTTP Bearer token security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Validates the JWT token from the Authorization header and returns
    the corresponding user from the database.

    Args:
        credentials: HTTP Bearer token credentials from request header
        db: Database session

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found
    """
    token = credentials.credentials

    try:
        # Verify and decode the token
        token_service = TokenService()
        payload = token_service.verify_token(token)

        # Check token type (must be access token)
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract user ID from token
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = int(user_id_str)

        # Retrieve user from database
        user_service = AuthUserService(db_session=db)
        user = user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle any other errors (expired token, invalid signature, etc.)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_csrf_service() -> CSRFService:
    """
    FastAPI dependency to get CSRF service instance.

    Returns:
        CSRFService instance
    """
    return CSRFService()


def validate_csrf_token(
    request: Request,
    csrf_service: CSRFService = Depends(get_csrf_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    FastAPI dependency to validate CSRF token for state-changing operations.

    Args:
        request: FastAPI request object
        csrf_service: CSRF service instance
        current_user: Current authenticated user (ensures authentication first)

    Raises:
        HTTPException: 403 if CSRF token is missing or invalid
    """
    # Get CSRF token from header
    csrf_token = request.headers.get(csrf_service.get_token_header_name())

    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is required for this operation",
        )

    # Use user ID as session identifier for additional security
    session_id = str(current_user.id)

    if not csrf_service.validate_token(csrf_token, session_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired CSRF token",
        )


def check_rate_limit(
    request: Request,
    limit: int,
    window_seconds: int,
) -> None:
    """
    FastAPI dependency to check rate limits for endpoints.

    Args:
        request: FastAPI request object
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds

    Raises:
        HTTPException: 429 if rate limit is exceeded
    """
    # Use client IP as the rate limit key
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    is_allowed, rate_info = rate_limiter.is_allowed(
        key=f"ip:{client_ip}",
        limit=limit,
        window_seconds=window_seconds,
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": str(rate_info["remaining"]),
                "X-RateLimit-Reset": str(rate_info["reset_time"]),
                "Retry-After": str(rate_info.get("retry_after", window_seconds)),
            },
        )


def check_login_rate_limit(request: Request) -> None:
    """
    FastAPI dependency to check rate limits for login endpoint.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 429 if rate limit is exceeded
    """
    check_rate_limit(request, config.rate_limit.login_limit, config.rate_limit.login_window)


def check_register_rate_limit(request: Request) -> None:
    """
    FastAPI dependency to check rate limits for registration endpoint.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 429 if rate limit is exceeded
    """
    check_rate_limit(request, config.rate_limit.register_limit, config.rate_limit.register_window)
