"""Unit tests for authentication API routes."""

from fastapi import status

from src.services.auth_user_service import AuthUserService
from src.services.token_service import TokenService


class TestTokenRefreshEndpoint:
    """Tests for POST /auth/refresh endpoint."""

    def test_successful_token_refresh(self, test_client, test_session):
        """Test successful token refresh with valid refresh token."""
        user_service = AuthUserService(db_session=test_session)
        user = user_service.create_user(
            email="refreshuser@example.com", password_hash="hashed_pw", name="Refresh User"
        )
        token_service = TokenService()
        refresh_token = token_service.create_refresh_token(user.id)

        refresh_data = {"refresh_token": refresh_token}
        response = test_client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert data["refresh_token"] == refresh_token

    def test_token_refresh_with_invalid_token(self, test_client):
        """Test token refresh fails with invalid refresh token."""
        refresh_data = {"refresh_token": "invalid.token.here"}
        response = test_client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "invalid" in response_data["detail"]["message"].lower()

    def test_token_refresh_with_access_token(self, test_client, test_session):
        """Test token refresh fails when using access token instead of refresh token."""
        user_service = AuthUserService(db_session=test_session)
        user = user_service.create_user(
            email="wrongtoken@example.com", password_hash="hashed_pw", name="Wrong Token User"
        )
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        refresh_data = {"refresh_token": access_token}
        response = test_client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "invalid token type" in response_data["detail"]["message"].lower()


class TestLogoutEndpoint:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_success(self, test_client):
        """Test logout endpoint returns success message."""
        response = test_client.post("/auth/logout")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "logout successful" in data["message"].lower()
