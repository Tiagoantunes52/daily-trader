"""Pydantic schemas for authentication request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserRegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Validate password has minimum length."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class UserLoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response model for token endpoints."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class UserResponse(BaseModel):
    """Response model for user profile."""

    id: int
    email: str
    name: str
    created_at: datetime
    is_email_verified: bool
    oauth_providers: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""

    name: str | None = None
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str | None) -> str | None:
        """Validate name is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty")
        return v.strip() if v else None


class PasswordChangeRequest(BaseModel):
    """Request model for password change."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password_length(cls, v: str) -> str:
        """Validate new password has minimum length."""
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long")
        return v


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback."""

    code: str
    state: str


class OAuthDisconnectRequest(BaseModel):
    """Request model for disconnecting OAuth provider."""

    provider: str
