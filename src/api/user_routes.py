"""User profile and account management API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, validate_csrf_token
from src.api.error_handlers import handle_service_error
from src.database.db import get_db
from src.database.models import User
from src.models.auth_schemas import (
    OAuthDisconnectRequest,
    PasswordChangeRequest,
    UserProfileUpdateRequest,
    UserResponse,
)
from src.services.auth_user_service import AuthUserService
from src.services.password_service import PasswordService

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


def get_password_service() -> PasswordService:
    """
    Dependency to get password service instance.

    Returns:
        PasswordService instance
    """
    return PasswordService()


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
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at,
        is_email_verified=current_user.is_email_verified,
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
        updated_user = user_service.update_user(current_user.id, **update_data)

        # Get OAuth providers for response
        oauth_providers = [conn.provider for conn in updated_user.oauth_connections]

        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            name=updated_user.name,
            created_at=updated_user.created_at,
            is_email_verified=updated_user.is_email_verified,
            oauth_providers=oauth_providers,
        )
    except Exception as e:
        error_response = handle_service_error(e, "profile_update")
        raise error_response.to_http_exception() from e


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    user_service: AuthUserService = Depends(get_user_service),
    password_service: PasswordService = Depends(get_password_service),
    _csrf_validation: None = Depends(validate_csrf_token),
):
    """
    Change current user's password.

    Args:
        password_data: Password change data (current_password, new_password)
        current_user: Authenticated user from JWT token
        user_service: User service instance
        password_service: Password service instance

    Returns:
        Success message

    Raises:
        HTTPException: 401 if not authenticated, 400 if current password is wrong
    """
    try:
        # Check if user has a password (OAuth-only users don't have passwords)
        if not current_user.password_hash:
            raise ValueError("Cannot change password for OAuth-only account")

        # Verify current password
        if not password_service.verify_password(
            password_data.current_password, current_user.password_hash
        ):
            raise ValueError("Current password is incorrect")

        # Validate new password strength
        is_valid, errors = password_service.validate_password_strength(password_data.new_password)
        if not is_valid:
            raise ValueError(
                f"New password does not meet strength requirements: {'; '.join(errors)}"
            )

        # Hash new password
        new_password_hash = password_service.hash_password(password_data.new_password)

        # Update password in database
        user_service.update_user(current_user.id, password_hash=new_password_hash)

        return {"message": "Password changed successfully"}

    except Exception as e:
        error_response = handle_service_error(e, "password_change")
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

        # Check if user has other authentication methods
        has_password = bool(current_user.password_hash)
        has_other_oauth = len(current_user.oauth_connections) > 1

        if not has_password and not has_other_oauth:
            raise ValueError("Cannot disconnect last authentication method. Set a password first.")

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
        success = user_service.delete_user(current_user.id)

        if not success:
            raise ValueError("Failed to delete account")

        return {"message": "Account deleted successfully"}

    except Exception as e:
        error_response = handle_service_error(e, "account_deletion")
        raise error_response.to_http_exception() from e
