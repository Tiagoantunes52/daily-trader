"""End-to-end tests for authentication flows."""

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.database.models import OAuthConnection, User


class TestRegistrationFlow:
    """End-to-end tests for complete registration flow."""

    def test_complete_registration_flow(self, test_client: TestClient, test_session: Session):
        """Test complete registration flow from start to finish.

        Requirements: 1.1
        """
        # Arrange
        user_data = {
            "email": "e2e_register@example.com",
            "password": "SecurePassword123!",
            "name": "E2E Test User",
        }

        # Act - Register user
        response = test_client.post("/auth/register", json=user_data)

        # Assert - Registration successful
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["email"] == user_data["email"]
        assert response_data["name"] == user_data["name"]
        assert "id" in response_data
        assert response_data["is_email_verified"] is False
        assert response_data["oauth_providers"] == []

        # Verify user exists in database
        user = test_session.query(User).filter_by(email=user_data["email"]).first()
        assert user is not None
        assert user.email == user_data["email"]
        assert user.name == user_data["name"]
        assert user.password_hash is not None
        assert user.is_email_verified is False

    def test_registration_flow_with_duplicate_email(self, test_client: TestClient):
        """Test registration flow fails with duplicate email.

        Requirements: 1.1
        """
        # Arrange
        user_data = {
            "email": "duplicate_e2e@example.com",
            "password": "SecurePassword123!",
            "name": "First User",
        }

        # Act - Register first user
        response1 = test_client.post("/auth/register", json=user_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Act - Try to register second user with same email
        duplicate_data = {
            "email": "duplicate_e2e@example.com",
            "password": "DifferentPassword123!",
            "name": "Second User",
        }
        response2 = test_client.post("/auth/register", json=duplicate_data)

        # Assert - Second registration fails
        assert response2.status_code == status.HTTP_409_CONFLICT
        response_data = response2.json()
        assert "detail" in response_data
        assert "already registered" in response_data["detail"]["message"].lower()

    def test_registration_flow_with_weak_password(self, test_client: TestClient):
        """Test registration flow fails with weak password.

        Requirements: 1.1
        """
        # Arrange
        user_data = {
            "email": "weak_password@example.com",
            "password": "weak",
            "name": "Test User",
        }

        # Act
        response = test_client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginFlow:
    """End-to-end tests for complete login flow."""

    def test_complete_login_flow(self, test_client: TestClient):
        """Test complete login flow from registration to login.

        Requirements: 2.1
        """
        # Arrange - Register user first
        user_data = {
            "email": "e2e_login@example.com",
            "password": "SecurePassword123!",
            "name": "E2E Login User",
        }
        register_response = test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        # Act - Login with correct credentials
        login_data = {"email": user_data["email"], "password": user_data["password"]}
        login_response = test_client.post("/auth/login", json=login_data)

        # Assert - Login successful
        assert login_response.status_code == status.HTTP_200_OK
        login_response_data = login_response.json()
        assert "access_token" in login_response_data
        assert "refresh_token" in login_response_data
        assert login_response_data["token_type"] == "bearer"
        assert len(login_response_data["access_token"]) > 0
        assert len(login_response_data["refresh_token"]) > 0

        # Verify tokens are different
        assert login_response_data["access_token"] != login_response_data["refresh_token"]

    def test_login_flow_with_invalid_credentials(self, test_client: TestClient):
        """Test login flow fails with invalid credentials.

        Requirements: 2.1
        """
        # Arrange - Register user first
        user_data = {
            "email": "e2e_invalid@example.com",
            "password": "CorrectPassword123!",
            "name": "E2E Invalid User",
        }
        register_response = test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        # Act - Login with wrong password
        login_data = {"email": user_data["email"], "password": "WrongPassword123!"}
        login_response = test_client.post("/auth/login", json=login_data)

        # Assert - Login fails with generic error
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = login_response.json()
        assert "detail" in response_data
        assert "invalid" in response_data["detail"]["message"].lower()

    def test_login_flow_with_nonexistent_email(self, test_client: TestClient):
        """Test login flow fails with non-existent email.

        Requirements: 2.1
        """
        # Act - Login with non-existent email
        login_data = {"email": "nonexistent_e2e@example.com", "password": "SomePassword123!"}
        login_response = test_client.post("/auth/login", json=login_data)

        # Assert - Login fails with generic error
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = login_response.json()
        assert "detail" in response_data
        assert "invalid" in response_data["detail"]["message"].lower()


class TestOAuthFlow:
    """End-to-end tests for OAuth functionality."""

    def test_oauth_callback_endpoint_exists(self, test_client: TestClient):
        """Test that OAuth callback endpoints exist and handle missing parameters correctly.

        Requirements: 3.1, 4.1
        """
        # Test Google callback without parameters
        response = test_client.get("/auth/google/callback")
        assert (
            response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        )  # Missing required query params

        # Test GitHub callback without parameters
        response = test_client.get("/auth/github/callback")
        assert (
            response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        )  # Missing required query params

    def test_oauth_callback_with_invalid_code(self, test_client: TestClient):
        """Test OAuth callback with invalid authorization code.

        Requirements: 3.1, 4.1
        """
        # Test Google callback with invalid code
        response = test_client.get("/auth/google/callback?code=invalid_code&state=test_state")
        # Should fail due to invalid code
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

        # Test GitHub callback with invalid code
        response = test_client.get("/auth/github/callback?code=invalid_code&state=test_state")
        # Should fail due to invalid code
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_oauth_user_creation_flow(self, test_client: TestClient, test_session: Session):
        """Test OAuth user creation flow with mocked service.

        Requirements: 3.1, 4.1
        """
        # Mock the authentication service to simulate successful OAuth
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

            # Test Google OAuth callback
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
        # Test Google authorization endpoint
        response = test_client.get("/auth/google/authorize")
        # May fail if OAuth not configured in test, but endpoint should exist
        assert response.status_code in [
            status.HTTP_302_FOUND,  # Success - redirects to Google
            status.HTTP_400_BAD_REQUEST,  # OAuth not configured
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # Configuration error
        ]

        # Test GitHub authorization endpoint
        response = test_client.get("/auth/github/authorize")
        # May fail if OAuth not configured in test, but endpoint should exist
        assert response.status_code in [
            status.HTTP_302_FOUND,  # Success - redirects to GitHub
            status.HTTP_400_BAD_REQUEST,  # OAuth not configured
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # Configuration error
        ]

    def test_oauth_database_integration(self, test_client: TestClient, test_session: Session):
        """Test OAuth database integration by creating OAuth connections manually.

        Requirements: 3.1, 4.1
        """
        # Create a user manually
        user = User(
            email="oauth_test@example.com",
            name="OAuth Test User",
            password_hash=None,  # OAuth-only user
            is_email_verified=True,
        )
        test_session.add(user)
        test_session.flush()

        # Create OAuth connection
        oauth_connection = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id="google_test_123",
            access_token="encrypted_access_token",
            refresh_token="encrypted_refresh_token",
        )
        test_session.add(oauth_connection)
        test_session.commit()

        # Verify OAuth connection was created
        created_connection = test_session.query(OAuthConnection).filter_by(user_id=user.id).first()
        assert created_connection is not None
        assert created_connection.provider == "google"
        assert created_connection.provider_user_id == "google_test_123"

        # Verify user can have multiple OAuth connections
        github_connection = OAuthConnection(
            user_id=user.id,
            provider="github",
            provider_user_id="github_test_456",
            access_token="encrypted_github_token",
            refresh_token=None,  # GitHub doesn't provide refresh tokens
        )
        test_session.add(github_connection)
        test_session.commit()

        # Verify both connections exist
        connections = test_session.query(OAuthConnection).filter_by(user_id=user.id).all()
        assert len(connections) == 2
        providers = [conn.provider for conn in connections]
        assert "google" in providers
        assert "github" in providers


class TestTokenRefreshFlow:
    """End-to-end tests for token refresh flow."""

    def test_complete_token_refresh_flow(self, test_client: TestClient):
        """Test complete token refresh flow.

        Requirements: 5.1
        """
        # Arrange - Register and login to get tokens
        user_data = {
            "email": "e2e_refresh@example.com",
            "password": "SecurePassword123!",
            "name": "E2E Refresh User",
        }
        register_response = test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        login_response = test_client.post(
            "/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()

        # Act - Refresh the token
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        refresh_response = test_client.post("/auth/refresh", json=refresh_data)

        # Assert - Refresh successful
        assert refresh_response.status_code == status.HTTP_200_OK
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"
        assert len(refresh_data["access_token"]) > 0

        # Verify new access token is valid by using it
        headers = {"Authorization": f"Bearer {refresh_data['access_token']}"}
        profile_response = test_client.get("/api/user/profile", headers=headers)
        assert profile_response.status_code == status.HTTP_200_OK

    def test_token_refresh_flow_with_invalid_token(self, test_client: TestClient):
        """Test token refresh flow fails with invalid refresh token.

        Requirements: 5.1
        """
        # Act - Try to refresh with invalid token
        refresh_data = {"refresh_token": "invalid.refresh.token"}
        refresh_response = test_client.post("/auth/refresh", json=refresh_data)

        # Assert - Refresh fails
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = refresh_response.json()
        assert "detail" in response_data
        assert "invalid" in response_data["detail"]["message"].lower()

    def test_token_refresh_flow_with_access_token(self, test_client: TestClient):
        """Test token refresh flow fails when using access token instead of refresh token.

        Requirements: 5.1
        """
        # Arrange - Register and login to get tokens
        user_data = {
            "email": "e2e_wrong_token@example.com",
            "password": "SecurePassword123!",
            "name": "E2E Wrong Token User",
        }
        register_response = test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        login_response = test_client.post(
            "/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()

        # Act - Try to refresh using access token
        refresh_data = {"refresh_token": tokens["access_token"]}
        refresh_response = test_client.post("/auth/refresh", json=refresh_data)

        # Assert - Refresh fails
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = refresh_response.json()
        assert "detail" in response_data
        assert "invalid token type" in response_data["detail"]["message"].lower()


class TestLogoutFlow:
    """End-to-end tests for logout flow."""

    def test_complete_logout_flow(self, test_client: TestClient):
        """Test complete logout flow.

        Requirements: 5.1
        """
        # Arrange - Register and login to get tokens
        user_data = {
            "email": "e2e_logout@example.com",
            "password": "SecurePassword123!",
            "name": "E2E Logout User",
        }
        register_response = test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        login_response = test_client.post(
            "/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()

        # Verify tokens work before logout
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        profile_response = test_client.get("/api/user/profile", headers=headers)
        assert profile_response.status_code == status.HTTP_200_OK

        # Act - Logout
        logout_response = test_client.post("/auth/logout")

        # Assert - Logout successful
        assert logout_response.status_code == status.HTTP_200_OK
        logout_data = logout_response.json()
        assert "message" in logout_data
        assert "logout successful" in logout_data["message"].lower()

        # Note: In a stateless JWT system, tokens remain valid until expiration
        # The logout endpoint mainly clears cookies and provides confirmation
        # Token invalidation would require a token blacklist or database tracking


class TestCompleteAuthenticationWorkflow:
    """End-to-end tests for complete authentication workflows."""

    def test_complete_registration_login_protected_access_workflow(self, test_client: TestClient):
        """Test complete workflow: registration -> login -> protected endpoint access.

        Requirements: 1.1, 2.1, 5.1
        """
        # Step 1: Register user
        user_data = {
            "email": "e2e_complete@example.com",
            "password": "SecurePassword123!",
            "name": "E2E Complete User",
        }
        register_response = test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        # Step 2: Login to get tokens
        login_response = test_client.post(
            "/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()

        # Step 3: Access protected endpoint
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        profile_response = test_client.get("/api/user/profile", headers=headers)
        assert profile_response.status_code == status.HTTP_200_OK
        profile_data = profile_response.json()
        assert profile_data["email"] == user_data["email"]
        assert profile_data["name"] == user_data["name"]

        # Step 4: Access another protected endpoint
        tips_response = test_client.get("/api/tips", headers=headers)
        assert tips_response.status_code == status.HTTP_200_OK
        tips_data = tips_response.json()
        assert "tips" in tips_data
        assert "total" in tips_data

    def test_complete_token_refresh_workflow(self, test_client: TestClient):
        """Test complete token refresh workflow: login -> refresh -> protected access.

        Requirements: 2.1, 5.1
        """
        # Step 1: Register and login
        user_data = {
            "email": "e2e_refresh_workflow@example.com",
            "password": "SecurePassword123!",
            "name": "E2E Refresh Workflow User",
        }
        register_response = test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        login_response = test_client.post(
            "/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
        )
        assert login_response.status_code == status.HTTP_200_OK
        original_tokens = login_response.json()

        # Step 2: Refresh tokens
        refresh_response = test_client.post(
            "/auth/refresh", json={"refresh_token": original_tokens["refresh_token"]}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()

        # Step 3: Use new access token for protected endpoint
        headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        profile_response = test_client.get("/api/user/profile", headers=headers)
        assert profile_response.status_code == status.HTTP_200_OK
        profile_data = profile_response.json()
        assert profile_data["email"] == user_data["email"]

        # Step 4: Verify old access token still works (JWT tokens don't get invalidated)
        old_headers = {"Authorization": f"Bearer {original_tokens['access_token']}"}
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

        # Scenario 3: Login with non-existent user
        login_response = test_client.post(
            "/auth/login", json={"email": "nonexistent@example.com", "password": "password"}
        )
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED

        # Scenario 4: Register with invalid email
        register_response = test_client.post(
            "/auth/register",
            json={"email": "invalid-email", "password": "SecurePassword123!", "name": "Test"},
        )
        assert register_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Scenario 5: Refresh with invalid token
        refresh_response = test_client.post(
            "/auth/refresh", json={"refresh_token": "invalid.refresh.token"}
        )
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
