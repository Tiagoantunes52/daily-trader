"""OAuth service for Google and GitHub authentication."""

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from src.utils.config import config


class OAuthService:
    """Service for OAuth provider integrations."""

    # OAuth endpoints
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    GITHUB_EMAIL_URL = "https://api.github.com/user/emails"

    @staticmethod
    def get_google_authorization_url(state: str | None = None) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection. If not provided,
                   a secure random state will be generated.

        Returns:
            The authorization URL to redirect the user to

        Raises:
            ValueError: If Google OAuth is not configured
        """
        if not config.oauth.google_client_id or not config.oauth.google_redirect_uri:
            raise ValueError("Google OAuth is not configured")

        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": config.oauth.google_client_id,
            "redirect_uri": config.oauth.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        return f"{OAuthService.GOOGLE_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_google_code(code: str) -> dict[str, Any]:
        """
        Exchange Google authorization code for access token and user info.

        Args:
            code: The authorization code received from Google

        Returns:
            A dictionary containing:
                - access_token: The OAuth access token
                - refresh_token: The OAuth refresh token (if available)
                - user_info: User profile information (email, name, etc.)

        Raises:
            ValueError: If Google OAuth is not configured or code is invalid
            httpx.HTTPError: If the API request fails
        """
        if not config.oauth.google_client_id or not config.oauth.google_client_secret:
            raise ValueError("Google OAuth is not configured")

        if not code:
            raise ValueError("Authorization code cannot be empty")

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                OAuthService.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": config.oauth.google_client_id,
                    "client_secret": config.oauth.google_client_secret,
                    "redirect_uri": config.oauth.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != 200:
                raise ValueError(f"Failed to exchange code: {token_response.text}")

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")

            if not access_token:
                raise ValueError("No access token received from Google")

            # Get user info
            userinfo_response = await client.get(
                OAuthService.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                raise ValueError(f"Failed to get user info: {userinfo_response.text}")

            user_info = userinfo_response.json()

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user_info": {
                    "provider_user_id": user_info.get("id"),
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture"),
                },
            }

    @staticmethod
    def get_github_authorization_url(state: str | None = None) -> str:
        """
        Generate GitHub OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection. If not provided,
                   a secure random state will be generated.

        Returns:
            The authorization URL to redirect the user to

        Raises:
            ValueError: If GitHub OAuth is not configured
        """
        if not config.oauth.github_client_id or not config.oauth.github_redirect_uri:
            raise ValueError("GitHub OAuth is not configured")

        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": config.oauth.github_client_id,
            "redirect_uri": config.oauth.github_redirect_uri,
            "scope": "user:email",
            "state": state,
        }

        return f"{OAuthService.GITHUB_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_github_code(code: str) -> dict[str, Any]:
        """
        Exchange GitHub authorization code for access token and user info.

        Args:
            code: The authorization code received from GitHub

        Returns:
            A dictionary containing:
                - access_token: The OAuth access token
                - refresh_token: The OAuth refresh token (if available)
                - user_info: User profile information (email, name, etc.)

        Raises:
            ValueError: If GitHub OAuth is not configured or code is invalid
            httpx.HTTPError: If the API request fails
        """
        if not config.oauth.github_client_id or not config.oauth.github_client_secret:
            raise ValueError("GitHub OAuth is not configured")

        if not code:
            raise ValueError("Authorization code cannot be empty")

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                OAuthService.GITHUB_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": config.oauth.github_client_id,
                    "client_secret": config.oauth.github_client_secret,
                    "redirect_uri": config.oauth.github_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if token_response.status_code != 200:
                raise ValueError(f"Failed to exchange code: {token_response.text}")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise ValueError("No access token received from GitHub")

            # Get user info
            userinfo_response = await client.get(
                OAuthService.GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )

            if userinfo_response.status_code != 200:
                raise ValueError(f"Failed to get user info: {userinfo_response.text}")

            user_info = userinfo_response.json()

            # Get user email (GitHub requires separate API call)
            email = user_info.get("email")
            if not email:
                email_response = await client.get(
                    OAuthService.GITHUB_EMAIL_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )

                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Find primary email
                    for email_data in emails:
                        if email_data.get("primary"):
                            email = email_data.get("email")
                            break
                    # Fallback to first email if no primary
                    if not email and emails:
                        email = emails[0].get("email")

            return {
                "access_token": access_token,
                "refresh_token": None,  # GitHub doesn't provide refresh tokens
                "user_info": {
                    "provider_user_id": str(user_info.get("id")),
                    "email": email,
                    "name": user_info.get("name") or user_info.get("login"),
                    "picture": user_info.get("avatar_url"),
                },
            }
