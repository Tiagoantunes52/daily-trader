"""End-to-end tests for authentication flows."""

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.database.models import OAuthConnection, User
from src.services.auth_user_service import AuthUserService
from src.services.token_service import TokenService


class TestOAuthFlow:
    """End-to-end tests for OAuth functionality."""

    def test_oauth_callback_endpoint_exists(self, test_client: TestClient):
        """Test that OAuth callback endpoints exist and handle missing parameters correctly.

        Requirements: 3.1, 4.1
        """
        response = test_client.get("/auth/google/callback")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = test_client.get("/auth/github/callback")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_oauth_callback_with_invalid_code(self, test_client: TestClient):
        """Test OAuth callback with invalid authorization code.

        Requirements: 3.1, 4.1
        """
        response = test_client.get("/auth/google/callback?code=invalid_code&state=test_state")
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

        response = test_client.get("/auth/github/callback?code=invalid_code&state=test_state")
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_oauth_user_creation_flow(self, test_client: TestClient, test_session: Session):
        """Test OAuth user creation flow with mocked service.

        Requirements: 3.1, 4.1
        """
        with patch(
            "src.services.authentication_service.AuthenticationService.handle_google_callback"
        ) as mock_callback:
            from src.models.auth_schemas import TokenResponse

            mock_token_response = TokenResponse(
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                token_type="bearer",
            )
            mock_callback.return_value = mock_token_response

            response = test_client.get("/auth/google/callback?code=test_code&state=test_state")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

    def test_oauth_authorization_endpoints_exist(self, test_client: TestClient):
        """Test that OAuth authorization endpoints exist.

        Requirements: 3.1, 4.1
        """
        response = test_client.get("/auth/google/authorize", follow_redirects=False)
        assert response.status_code in [
            status.HTTP_302_FOUND,
            status.HTTP_307_TEMPORARY_REDIRECT,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

        response = test_client.get("/auth/github/authorize", follow_redirects=False)
        assert response.status_code in [
            status.HTTP_302_FOUND,
            status.HTTP_307_TEMPORARY_REDIRECT,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_oauth_database_integration(self, test_client: TestClient, test_session: Session):
        """Test OAuth database integration by creating OAuth connections manually.

        Requirements: 3.1, 4.1
        """
        user = User(
            email="oauth_test@example.com",
            name="OAuth Test User",
            password_hash=None,
            is_email_verified=True,
        )
        test_session.add(user)
        test_session.flush()

        oauth_connection = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id="google_test_123",
            access_token="encrypted_access_token",
            refresh_token="encrypted_refresh_token",
        )
        test_session.add(oauth_connection)
        test_session.commit()

        created_connection = test_session.query(OAuthConnection).filter_by(user_id=user.id).first()
        assert created_connection is not None
        assert created_connection.provider == "google"
        assert created_connection.provider_user_id == "google_test_123"

        github_connection = OAuthConnection(
            user_id=user.id,
            provider="github",
            provider_user_id="github_test_456",
            access_token="encrypted_github_token",
            refresh_token=None,
        )
        test_session.add(github_connection)
        test_session.commit()

        connections = test_session.query(OAuthConnection).filter_by(user_id=user.id).all()
        assert len(connections) == 2
        providers = [conn.provider for conn in connections]
        assert "google" in providers
        assert "github" in providers


class TestTokenRefreshFlow:
    """End-to-end tests for token refresh flow."""

    def test_complete_token_refresh_flow(self, test_client: TestClient, test_session: Session):
        """Test complete token refresh flow.

        Requirements: 5.1
        """
        user_service = AuthUserService(db_session=test_session)
        user = user_service.create_user(
            email="e2e_refresh@example.com",
            password_hash="hashed_pw",
            name="E2E Refresh User",
        )
        token_service = TokenService()
        refresh_token = token_service.create_refresh_token(user.id)

        refresh_response = test_client.post("/auth/refresh", json={"refresh_token": refresh_token})

        assert refresh_response.status_code == status.HTTP_200_OK
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"
        assert len(refresh_data["access_token"]) > 0

        headers = {"Authorization": f"Bearer {refresh_data['access_token']}"}
        profile_response = test_client.get("/api/user/profile", headers=headers)
        assert profile_response.status_code == status.HTTP_200_OK

    def test_token_refresh_flow_with_invalid_token(self, test_client: TestClient):
        """Test token refresh flow fails with invalid refresh token.

        Requirements: 5.1
        """
        refresh_data = {"refresh_token": "invalid.refresh.token"}
        refresh_response = test_client.post("/auth/refresh", json=refresh_data)

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = refresh_response.json()
        assert "detail" in response_data
        assert "invalid" in response_data["detail"]["message"].lower()

    def test_token_refresh_flow_with_access_token(
        self, test_client: TestClient, test_session: Session
    ):
        """Test token refresh flow fails when using access token instead of refresh token.

        Requirements: 5.1
        """
        user_service = AuthUserService(db_session=test_session)
        user = user_service.create_user(
            email="e2e_wrong_token@example.com",
            password_hash="hashed_pw",
            name="E2E Wrong Token User",
        )
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        refresh_response = test_client.post(
            "/auth/refresh", json={"refresh_token": access_token}
        )

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = refresh_response.json()
        assert "detail" in response_data
        assert "invalid token type" in response_data["detail"]["message"].lower()


class TestLogoutFlow:
    """End-to-end tests for logout flow."""

    def test_complete_logout_flow(self, test_client: TestClient, test_session: Session):
        """Test complete logout flow.

        Requirements: 5.1
        """
        user_service = AuthUserService(db_session=test_session)
        user = user_service.create_user(
            email="e2e_logout@example.com",
            password_hash="hashed_pw",
            name="E2E Logout User",
        )
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = test_client.get("/api/user/profile", headers=headers)
        assert profile_response.status_code == status.HTTP_200_OK

        logout_response = test_client.post("/auth/logout")

        assert logout_response.status_code == status.HTTP_200_OK
        logout_data = logout_response.json()
        assert "message" in logout_data
        assert "logout successful" in logout_data["message"].lower()


class TestCompleteAuthenticationWorkflow:
    """End-to-end tests for complete authentication workflows."""

    def test_complete_token_refresh_workflow(
        self, test_client: TestClient, test_session: Session
    ):
        """Test complete token refresh workflow: create tokens -> refresh -> protected access.

        Requirements: 2.1, 5.1
        """
        user_service = AuthUserService(db_session=test_session)
        user = user_service.create_user(
            email="e2e_refresh_workflow@example.com",
            password_hash="hashed_pw",
            name="E2E Refresh Workflow User",
        )
        token_service = TokenService()
        original_access_token = token_service.create_access_token(user.id)
        original_refresh_token = token_service.create_refresh_token(user.id)

        refresh_response = test_client.post(
            "/auth/refresh", json={"refresh_token": original_refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()

        headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        profile_response = test_client.get("/api/user/profile", headers=headers)
        assert profile_response.status_code == status.HTTP_200_OK
        profile_data = profile_response.json()
        assert profile_data["email"] == "e2e_refresh_workflow@example.com"

        old_headers = {"Authorization": f"Bearer {original_access_token}"}
        old_profile_response = test_client.get("/api/user/profile", headers=old_headers)
        assert old_profile_response.status_code == status.HTTP_200_OK

    def test_authentication_error_scenarios_workflow(self, test_client: TestClient):
        """Test various authentication error scenarios in workflow.

        Requirements: 1.1, 2.1, 5.1
        """
        # Scenario 1: Access protected endpoint without token
        response = test_client.get("/api/user/profile")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Scenario 2: Access protected endpoint with invalid token
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = test_client.get("/api/user/profile", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Scenario 3: Refresh with invalid token
        refresh_response = test_client.post(
            "/auth/refresh", json={"refresh_token": "invalid.refresh.token"}
        )
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
