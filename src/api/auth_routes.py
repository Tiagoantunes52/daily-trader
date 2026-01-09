"""Authentication API routes for registration, login, and token management."""

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.api.dependencies import (
    check_login_rate_limit,
    check_register_rate_limit,
    get_csrf_service,
    get_current_user,
)
from src.api.error_handlers import handle_service_error
from src.database.db import get_db
from src.database.models import User
from src.models.auth_schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from src.services.authentication_service import AuthenticationService
from src.services.csrf_service import CSRFService
from src.services.oauth_service import OAuthService
from src.services.token_service import TokenService

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthenticationService:
    """
    Dependency to get authentication service instance.

    Args:
        db: Database session

    Returns:
        AuthenticationService instance
    """
    return AuthenticationService(db_session=db)


def get_token_service() -> TokenService:
    """
    Dependency to get token service instance.

    Returns:
        TokenService instance
    """
    return TokenService()


def get_oauth_service() -> OAuthService:
    """
    Dependency to get OAuth service instance.

    Returns:
        OAuthService instance
    """
    return OAuthService()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Register a new user with email and password.

    Args:
        user_data: User registration data (email, password, name)
        request: FastAPI request object
        auth_service: Authentication service instance

    Returns:
        Created user profile

    Raises:
        HTTPException: 400 for validation errors, 409 for duplicate email, 429 for rate limit exceeded
    """
    # Check rate limit first
    check_register_rate_limit(request)

    try:
        user = auth_service.register(
            email=user_data.email, password=user_data.password, name=user_data.name
        )

        # Return user response without OAuth providers (new user)
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
            is_email_verified=user.is_email_verified,
            oauth_providers=[],
        )
    except Exception as e:
        error_response = handle_service_error(e, "registration")
        raise error_response.to_http_exception() from e


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLoginRequest,
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Authenticate user with email and password.

    Args:
        credentials: User login credentials (email, password)
        request: FastAPI request object
        auth_service: Authentication service instance

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: 401 for invalid credentials, 400 for validation errors, 429 for rate limit exceeded
    """
    # Check rate limit first
    check_login_rate_limit(request)

    try:
        token_response = auth_service.login(email=credentials.email, password=credentials.password)
        return token_response
    except Exception as e:
        error_response = handle_service_error(e, "login")
        raise error_response.to_http_exception() from e


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    token_service: TokenService = Depends(get_token_service),
):
    """
    Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token
        token_service: Token service instance

    Returns:
        New access token and same refresh token

    Raises:
        HTTPException: 401 for invalid or expired refresh token
    """
    try:
        # Verify and decode refresh token
        payload = token_service.verify_token(refresh_data.refresh_token)

        # Check token type
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")

        # Generate new access token
        new_access_token = token_service.create_access_token(int(user_id))

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_data.refresh_token,
            token_type="bearer",
        )
    except Exception as e:
        error_response = handle_service_error(e, "token")
        raise error_response.to_http_exception() from e


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Logout user by invalidating their session.

    Note: In a stateless JWT implementation, logout is typically handled
    client-side by removing tokens. This endpoint is a placeholder for
    future token blacklisting or session management.

    Args:
        auth_service: Authentication service instance

    Returns:
        Success message

    Raises:
        HTTPException: 401 if not authenticated
    """
    # In a stateless JWT system, logout is handled client-side
    # This endpoint exists for API completeness and future enhancements
    return {"message": "Logout successful. Please remove tokens from client."}


@router.get("/google/authorize")
async def google_authorize(
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """
    Initiate Google OAuth authorization flow.

    Returns:
        Redirect to Google OAuth consent screen

    Raises:
        HTTPException: 500 if Google OAuth is not configured
    """
    try:
        authorization_url = oauth_service.get_google_authorization_url()
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        error_response = handle_service_error(e, "oauth_google")
        raise error_response.to_http_exception() from e


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Handle Google OAuth callback.

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        auth_service: Authentication service instance

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: 400 for invalid code, 500 for OAuth errors
    """
    try:
        token_response = await auth_service.handle_google_callback(code, state)
        return token_response
    except Exception as e:
        error_response = handle_service_error(e, "oauth_google")
        raise error_response.to_http_exception() from e


@router.get("/github/authorize")
async def github_authorize(
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """
    Initiate GitHub OAuth authorization flow.

    Returns:
        Redirect to GitHub OAuth authorization endpoint

    Raises:
        HTTPException: 500 if GitHub OAuth is not configured
    """
    try:
        authorization_url = oauth_service.get_github_authorization_url()
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        error_response = handle_service_error(e, "oauth_github")
        raise error_response.to_http_exception() from e


@router.get("/github/callback", response_model=TokenResponse)
async def github_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Handle GitHub OAuth callback.

    Args:
        code: Authorization code from GitHub
        state: State parameter for CSRF protection
        auth_service: Authentication service instance

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: 400 for invalid code, 500 for OAuth errors
    """
    try:
        token_response = await auth_service.handle_github_callback(code, state)
        return token_response
    except Exception as e:
        error_response = handle_service_error(e, "oauth_github")
        raise error_response.to_http_exception() from e


@router.get("/csrf-token")
async def get_csrf_token(
    current_user: User = Depends(get_current_user),
    csrf_service: CSRFService = Depends(get_csrf_service),
):
    """
    Generate a CSRF token for the authenticated user.

    Args:
        current_user: Current authenticated user
        csrf_service: CSRF service instance

    Returns:
        CSRF token and header name

    Raises:
        HTTPException: 401 if not authenticated
    """
    # Use user ID as session identifier
    session_id = str(current_user.id)
    csrf_token = csrf_service.generate_token(session_id)

    return {
        "csrf_token": csrf_token,
        "header_name": csrf_service.get_token_header_name(),
        "expires_in": 3600,  # 1 hour
    }
