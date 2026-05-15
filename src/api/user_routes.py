"""User profile and account management API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, validate_csrf_token
from src.api.error_handlers import handle_service_error
from src.database.db import get_db
from src.database.models import User
from src.models.auth_schemas import (
    OAuthDisconnectRequest,
    UserProfileUpdateRequest,
    UserResponse,
)
from src.services.auth_user_service import AuthUserService

router = APIRouter(prefix="/api/user", tags=["user"])


def get_user_service(db: Session = Depends(get_db)) -> AuthUserService:
    """
    Dependency to get user service instance.

    Args:
        db: Database session

    Returns:
        AuthUserService instance
    """
    return AuthUserService(db_session=db)


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's profile information.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        User profile with OAuth providers list

    Raises:
        HTTPException: 401 if not authenticated
    """
    # Get OAuth providers for this user
    oauth_providers = [conn.provider for conn in current_user.oauth_connections]

    return UserResponse(
        id=int(current_user.id),  # type: ignore
        email=str(current_user.email),
        name=str(current_user.name),
        created_at=current_user.created_at,  # type: ignore
        is_email_verified=bool(current_user.is_email_verified),
        oauth_providers=oauth_providers,
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: AuthUserService = Depends(get_user_service),
    _csrf_validation: None = Depends(validate_csrf_token),
):
    """
    Update current user's profile information.

    Args:
        profile_data: Profile update data (name, email)
        current_user: Authenticated user from JWT token
        user_service: User service instance

    Returns:
        Updated user profile

    Raises:
        HTTPException: 401 if not authenticated, 409 if email already exists
    """
    try:
        # Prepare update data (only include non-None values)
        update_data = {}
        if profile_data.name is not None:
            update_data["name"] = profile_data.name
        if profile_data.email is not None:
            update_data["email"] = profile_data.email

        # Update user profile
        updated_user = user_service.update_user(int(current_user.id), **update_data)  # type: ignore

        # Get OAuth providers for response
        oauth_providers = [conn.provider for conn in updated_user.oauth_connections]

        return UserResponse(
            id=int(updated_user.id),  # type: ignore
            email=str(updated_user.email),
            name=str(updated_user.name),
            created_at=updated_user.created_at,  # type: ignore
            is_email_verified=bool(updated_user.is_email_verified),
            oauth_providers=oauth_providers,
        )
    except Exception as e:
        error_response = handle_service_error(e, "profile_update")
        raise error_response.to_http_exception() from e


@router.post("/disconnect-oauth", status_code=status.HTTP_200_OK)
async def disconnect_oauth(
    disconnect_data: OAuthDisconnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf_validation: None = Depends(validate_csrf_token),
):
    """
    Disconnect an OAuth provider from user account.

    Args:
        disconnect_data: OAuth disconnect data (provider)
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 401 if not authenticated, 400 if provider not connected
    """
    try:
        # Find the OAuth connection to remove
        oauth_connection = None
        for conn in current_user.oauth_connections:
            if conn.provider == disconnect_data.provider:
                oauth_connection = conn
                break

        if not oauth_connection:
            raise ValueError(f"OAuth provider '{disconnect_data.provider}' is not connected")

        if len(current_user.oauth_connections) <= 1:
            raise ValueError("Cannot disconnect last authentication method.")

        # Remove the OAuth connection
        db.delete(oauth_connection)
        db.commit()

        return {"message": f"OAuth provider '{disconnect_data.provider}' disconnected successfully"}

    except Exception as e:
        error_response = handle_service_error(e, "disconnect")
        raise error_response.to_http_exception() from e


@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(
    current_user: User = Depends(get_current_user),
    user_service: AuthUserService = Depends(get_user_service),
    _csrf_validation: None = Depends(validate_csrf_token),
):
    """
    Delete current user's account and all associated data.

    Args:
        current_user: Authenticated user from JWT token
        user_service: User service instance

    Returns:
        Success message

    Raises:
        HTTPException: 401 if not authenticated, 500 if deletion fails
    """
    try:
        # Delete user account (cascades to OAuth connections)
        success = user_service.delete_user(int(current_user.id))  # type: ignore

        if not success:
            raise ValueError("Failed to delete account")

        return {"message": "Account deleted successfully"}

    except Exception as e:
        error_response = handle_service_error(e, "account_deletion")
        raise error_response.to_http_exception() from e
