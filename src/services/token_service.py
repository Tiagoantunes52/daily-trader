"""JWT token generation and validation service."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from src.utils.config import config


class TokenService:
    """Service for JWT token generation and validation."""

    @staticmethod
    def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: The user ID to encode in the token
            expires_delta: Optional custom expiration time delta. If not provided,
                          uses the configured access token expiration time.

        Returns:
            The encoded JWT token as a string

        Raises:
            ValueError: If user_id is invalid
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        if expires_delta is None:
            expires_delta = timedelta(minutes=config.jwt.access_token_expire_minutes)

        now = datetime.now(UTC)
        expire = now + expires_delta

        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": expire,
        }

        token = jwt.encode(
            payload,
            config.jwt.secret_key,
            algorithm=config.jwt.algorithm,
        )

        return token

    @staticmethod
    def create_refresh_token(user_id: int, expires_delta: timedelta | None = None) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_id: The user ID to encode in the token
            expires_delta: Optional custom expiration time delta. If not provided,
                          uses the configured refresh token expiration time.

        Returns:
            The encoded JWT token as a string

        Raises:
            ValueError: If user_id is invalid
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        if expires_delta is None:
            expires_delta = timedelta(days=config.jwt.refresh_token_expire_days)

        now = datetime.now(UTC)
        expire = now + expires_delta

        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }

        token = jwt.encode(
            payload,
            config.jwt.secret_key,
            algorithm=config.jwt.algorithm,
        )

        return token

    @staticmethod
    def verify_token(token: str) -> dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT token to verify

        Returns:
            The decoded token payload as a dictionary

        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid or malformed
            ValueError: If token is empty or None
        """
        if not token:
            raise ValueError("Token cannot be empty")

        try:
            payload = jwt.decode(
                token,
                config.jwt.secret_key,
                algorithms=[config.jwt.algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError as e:
            raise jwt.ExpiredSignatureError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {e!s}") from e

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        """
        Decode a JWT token without verification (for inspection only).

        Args:
            token: The JWT token to decode

        Returns:
            The decoded token payload as a dictionary

        Raises:
            jwt.DecodeError: If token cannot be decoded
            ValueError: If token is empty or None
        """
        if not token:
            raise ValueError("Token cannot be empty")

        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )
            return payload
        except jwt.DecodeError as e:
            raise jwt.DecodeError(f"Cannot decode token: {e!s}") from e
