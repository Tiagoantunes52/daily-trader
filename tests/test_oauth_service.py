"""Tests for OAuth service."""

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from src.services.oauth_service import OAuthService


class TestOAuthServiceUnit:
    """Unit tests for OAuthService."""

    def test_get_google_authorization_url_with_state(self):
        """Test Google authorization URL generation with provided state."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = "test_client_id"
            mock_config.oauth.google_redirect_uri = "http://localhost:8000/auth/google/callback"

            state = "test_state_123"
            url = OAuthService.get_google_authorization_url(state)

            # Parse URL
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Verify URL structure
            assert parsed.scheme == "https"
            assert parsed.netloc == "accounts.google.com"
            assert parsed.path == "/o/oauth2/v2/auth"

            # Verify parameters
            assert params["client_id"][0] == "test_client_id"
            assert params["redirect_uri"][0] == "http://localhost:8000/auth/google/callback"
            assert params["response_type"][0] == "code"
            assert params["scope"][0] == "openid email profile"
            assert params["state"][0] == state
            assert params["access_type"][0] == "offline"
            assert params["prompt"][0] == "consent"

    def test_get_google_authorization_url_without_state(self):
        """Test Google authorization URL generation without provided state (auto-generated)."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = "test_client_id"
            mock_config.oauth.google_redirect_uri = "http://localhost:8000/auth/google/callback"

            url = OAuthService.get_google_authorization_url()

            # Parse URL
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Verify state was auto-generated
            assert "state" in params
            assert len(params["state"][0]) > 0

    def test_get_google_authorization_url_not_configured(self):
        """Test Google authorization URL generation when OAuth is not configured."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = None
            mock_config.oauth.google_redirect_uri = None

            with pytest.raises(ValueError, match="Google OAuth is not configured"):
                OAuthService.get_google_authorization_url()

    def test_get_github_authorization_url_with_state(self):
        """Test GitHub authorization URL generation with provided state."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = "test_github_client_id"
            mock_config.oauth.github_redirect_uri = "http://localhost:8000/auth/github/callback"

            state = "test_state_456"
            url = OAuthService.get_github_authorization_url(state)

            # Parse URL
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Verify URL structure
            assert parsed.scheme == "https"
            assert parsed.netloc == "github.com"
            assert parsed.path == "/login/oauth/authorize"

            # Verify parameters
            assert params["client_id"][0] == "test_github_client_id"
            assert params["redirect_uri"][0] == "http://localhost:8000/auth/github/callback"
            assert params["scope"][0] == "user:email"
            assert params["state"][0] == state

    def test_get_github_authorization_url_without_state(self):
        """Test GitHub authorization URL generation without provided state (auto-generated)."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = "test_github_client_id"
            mock_config.oauth.github_redirect_uri = "http://localhost:8000/auth/github/callback"

            url = OAuthService.get_github_authorization_url()

            # Parse URL
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Verify state was auto-generated
            assert "state" in params
            assert len(params["state"][0]) > 0

    def test_get_github_authorization_url_not_configured(self):
        """Test GitHub authorization URL generation when OAuth is not configured."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = None
            mock_config.oauth.github_redirect_uri = None

            with pytest.raises(ValueError, match="GitHub OAuth is not configured"):
                OAuthService.get_github_authorization_url()

    @pytest.mark.asyncio
    async def test_exchange_google_code_success(self):
        """Test successful Google OAuth code exchange."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = "test_client_id"
            mock_config.oauth.google_client_secret = "test_client_secret"
            mock_config.oauth.google_redirect_uri = "http://localhost:8000/auth/google/callback"

            # Mock HTTP responses
            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
            }

            mock_userinfo_response = MagicMock()
            mock_userinfo_response.status_code = 200
            mock_userinfo_response.json.return_value = {
                "id": "google_user_123",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/picture.jpg",
            }

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_token_response
                mock_instance.get.return_value = mock_userinfo_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await OAuthService.exchange_google_code("test_code")

                # Verify result structure
                assert result["access_token"] == "test_access_token"
                assert result["refresh_token"] == "test_refresh_token"
                assert result["user_info"]["provider_user_id"] == "google_user_123"
                assert result["user_info"]["email"] == "test@example.com"
                assert result["user_info"]["name"] == "Test User"
                assert result["user_info"]["picture"] == "https://example.com/picture.jpg"

    @pytest.mark.asyncio
    async def test_exchange_google_code_empty_code(self):
        """Test Google OAuth code exchange with empty code."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = "test_client_id"
            mock_config.oauth.google_client_secret = "test_client_secret"

            with pytest.raises(ValueError, match="Authorization code cannot be empty"):
                await OAuthService.exchange_google_code("")

    @pytest.mark.asyncio
    async def test_exchange_google_code_not_configured(self):
        """Test Google OAuth code exchange when OAuth is not configured."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = None
            mock_config.oauth.google_client_secret = None

            with pytest.raises(ValueError, match="Google OAuth is not configured"):
                await OAuthService.exchange_google_code("test_code")

    @pytest.mark.asyncio
    async def test_exchange_google_code_token_request_fails(self):
        """Test Google OAuth code exchange when token request fails."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = "test_client_id"
            mock_config.oauth.google_client_secret = "test_client_secret"
            mock_config.oauth.google_redirect_uri = "http://localhost:8000/auth/google/callback"

            # Mock failed token response
            mock_token_response = MagicMock()
            mock_token_response.status_code = 400
            mock_token_response.text = "Invalid code"

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_token_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                with pytest.raises(ValueError, match="Failed to exchange code"):
                    await OAuthService.exchange_google_code("invalid_code")

    @pytest.mark.asyncio
    async def test_exchange_google_code_no_access_token(self):
        """Test Google OAuth code exchange when no access token is returned."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.google_client_id = "test_client_id"
            mock_config.oauth.google_client_secret = "test_client_secret"
            mock_config.oauth.google_redirect_uri = "http://localhost:8000/auth/google/callback"

            # Mock token response without access_token
            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {}

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_token_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                with pytest.raises(ValueError, match="No access token received from Google"):
                    await OAuthService.exchange_google_code("test_code")

    @pytest.mark.asyncio
    async def test_exchange_github_code_success(self):
        """Test successful GitHub OAuth code exchange."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = "test_github_client_id"
            mock_config.oauth.github_client_secret = "test_github_client_secret"
            mock_config.oauth.github_redirect_uri = "http://localhost:8000/auth/github/callback"

            # Mock HTTP responses
            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "test_github_access_token",
            }

            mock_userinfo_response = MagicMock()
            mock_userinfo_response.status_code = 200
            mock_userinfo_response.json.return_value = {
                "id": 12345,
                "email": "github@example.com",
                "name": "GitHub User",
                "login": "githubuser",
                "avatar_url": "https://github.com/avatar.jpg",
            }

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_token_response
                mock_instance.get.return_value = mock_userinfo_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await OAuthService.exchange_github_code("test_code")

                # Verify result structure
                assert result["access_token"] == "test_github_access_token"
                assert result["refresh_token"] is None  # GitHub doesn't provide refresh tokens
                assert result["user_info"]["provider_user_id"] == "12345"
                assert result["user_info"]["email"] == "github@example.com"
                assert result["user_info"]["name"] == "GitHub User"
                assert result["user_info"]["picture"] == "https://github.com/avatar.jpg"

    @pytest.mark.asyncio
    async def test_exchange_github_code_with_email_fetch(self):
        """Test GitHub OAuth code exchange when email needs to be fetched separately."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = "test_github_client_id"
            mock_config.oauth.github_client_secret = "test_github_client_secret"
            mock_config.oauth.github_redirect_uri = "http://localhost:8000/auth/github/callback"

            # Mock HTTP responses
            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "test_github_access_token",
            }

            # User info without email
            mock_userinfo_response = MagicMock()
            mock_userinfo_response.status_code = 200
            mock_userinfo_response.json.return_value = {
                "id": 12345,
                "email": None,
                "name": "GitHub User",
                "login": "githubuser",
                "avatar_url": "https://github.com/avatar.jpg",
            }

            # Email endpoint response
            mock_email_response = MagicMock()
            mock_email_response.status_code = 200
            mock_email_response.json.return_value = [
                {"email": "secondary@example.com", "primary": False},
                {"email": "primary@example.com", "primary": True},
            ]

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_token_response

                # Setup get to return different responses based on URL
                async def mock_get(url, **kwargs):
                    if "user/emails" in url:
                        return mock_email_response
                    return mock_userinfo_response

                mock_instance.get.side_effect = mock_get
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await OAuthService.exchange_github_code("test_code")

                # Verify primary email was selected
                assert result["user_info"]["email"] == "primary@example.com"

    @pytest.mark.asyncio
    async def test_exchange_github_code_empty_code(self):
        """Test GitHub OAuth code exchange with empty code."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = "test_github_client_id"
            mock_config.oauth.github_client_secret = "test_github_client_secret"

            with pytest.raises(ValueError, match="Authorization code cannot be empty"):
                await OAuthService.exchange_github_code("")

    @pytest.mark.asyncio
    async def test_exchange_github_code_not_configured(self):
        """Test GitHub OAuth code exchange when OAuth is not configured."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = None
            mock_config.oauth.github_client_secret = None

            with pytest.raises(ValueError, match="GitHub OAuth is not configured"):
                await OAuthService.exchange_github_code("test_code")

    @pytest.mark.asyncio
    async def test_exchange_github_code_token_request_fails(self):
        """Test GitHub OAuth code exchange when token request fails."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = "test_github_client_id"
            mock_config.oauth.github_client_secret = "test_github_client_secret"
            mock_config.oauth.github_redirect_uri = "http://localhost:8000/auth/github/callback"

            # Mock failed token response
            mock_token_response = MagicMock()
            mock_token_response.status_code = 400
            mock_token_response.text = "Invalid code"

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_token_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                with pytest.raises(ValueError, match="Failed to exchange code"):
                    await OAuthService.exchange_github_code("invalid_code")

    @pytest.mark.asyncio
    async def test_exchange_github_code_no_access_token(self):
        """Test GitHub OAuth code exchange when no access token is returned."""
        with patch("src.services.oauth_service.config") as mock_config:
            mock_config.oauth.github_client_id = "test_github_client_id"
            mock_config.oauth.github_client_secret = "test_github_client_secret"
            mock_config.oauth.github_redirect_uri = "http://localhost:8000/auth/github/callback"

            # Mock token response without access_token
            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {}

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_token_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                with pytest.raises(ValueError, match="No access token received from GitHub"):
                    await OAuthService.exchange_github_code("test_code")
