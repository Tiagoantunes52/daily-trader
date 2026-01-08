"""Unit tests for authentication API routes."""

from fastapi import status

from src.database.models import User


class TestRegistrationEndpoint:
    """Tests for POST /auth/register endpoint."""

    def test_successful_registration(self, test_client, test_session):
        """Test successful user registration with valid data."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "name": "New User",
        }

        # Act
        response = test_client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["name"] == user_data["name"]
        assert "id" in data
        assert data["is_email_verified"] is False
        assert data["oauth_providers"] == []

        # Verify user was created in database
        user = test_session.query(User).filter_by(email=user_data["email"]).first()
        assert user is not None
        assert user.email == user_data["email"]
        assert user.name == user_data["name"]
        assert user.password_hash is not None

    def test_registration_with_invalid_email(self, test_client):
        """Test registration fails with invalid email format."""
        # Arrange
        user_data = {
            "email": "not-an-email",
            "password": "SecurePass123!",
            "name": "Test User",
        }

        # Act
        response = test_client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_registration_with_weak_password(self, test_client):
        """Test registration fails with weak password."""
        # Arrange
        user_data = {
            "email": "test@example.com",
            "password": "weak",
            "name": "Test User",
        }

        # Act
        response = test_client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_registration_with_duplicate_email(self, test_client, test_session):
        """Test registration fails when email already exists."""
        # Arrange - Create first user
        user_data = {
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
            "name": "First User",
        }
        test_client.post("/auth/register", json=user_data)

        # Act - Try to register with same email
        duplicate_data = {
            "email": "duplicate@example.com",
            "password": "DifferentPass123!",
            "name": "Second User",
        }
        response = test_client.post("/auth/register", json=duplicate_data)

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "already registered" in response_data["detail"]["message"].lower()

    def test_registration_with_empty_name(self, test_client):
        """Test registration fails with empty name."""
        # Arrange
        user_data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "name": "",
        }

        # Act
        response = test_client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginEndpoint:
    """Tests for POST /auth/login endpoint."""

    def test_successful_login(self, test_client):
        """Test successful login with valid credentials."""
        # Arrange - Register a user first
        user_data = {
            "email": "loginuser@example.com",
            "password": "SecurePass123!",
            "name": "Login User",
        }
        test_client.post("/auth/register", json=user_data)

        # Act - Login with correct credentials
        login_data = {"email": "loginuser@example.com", "password": "SecurePass123!"}
        response = test_client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_login_with_invalid_email(self, test_client):
        """Test login fails with non-existent email."""
        # Arrange
        login_data = {"email": "nonexistent@example.com", "password": "SomePassword123!"}

        # Act
        response = test_client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "invalid" in response_data["detail"]["message"].lower()

    def test_login_with_incorrect_password(self, test_client):
        """Test login fails with incorrect password."""
        # Arrange - Register a user first
        user_data = {
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "name": "Test User",
        }
        test_client.post("/auth/register", json=user_data)

        # Act - Login with wrong password
        login_data = {"email": "wrongpass@example.com", "password": "WrongPass123!"}
        response = test_client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "invalid" in response_data["detail"]["message"].lower()

    def test_login_with_malformed_email(self, test_client):
        """Test login fails with malformed email."""
        # Arrange
        login_data = {"email": "not-an-email", "password": "SomePassword123!"}

        # Act
        response = test_client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTokenRefreshEndpoint:
    """Tests for POST /auth/refresh endpoint."""

    def test_successful_token_refresh(self, test_client):
        """Test successful token refresh with valid refresh token."""
        # Arrange - Register and login to get tokens
        user_data = {
            "email": "refreshuser@example.com",
            "password": "SecurePass123!",
            "name": "Refresh User",
        }
        test_client.post("/auth/register", json=user_data)

        login_response = test_client.post(
            "/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
        )
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]

        # Act - Refresh the token
        refresh_data = {"refresh_token": refresh_token}
        response = test_client.post("/auth/refresh", json=refresh_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # Access token should be valid (may be same if generated at same second)
        assert len(data["access_token"]) > 0
        # Refresh token should be the same
        assert data["refresh_token"] == refresh_token

    def test_token_refresh_with_invalid_token(self, test_client):
        """Test token refresh fails with invalid refresh token."""
        # Arrange
        refresh_data = {"refresh_token": "invalid.token.here"}

        # Act
        response = test_client.post("/auth/refresh", json=refresh_data)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "invalid" in response_data["detail"]["message"].lower()

    def test_token_refresh_with_access_token(self, test_client):
        """Test token refresh fails when using access token instead of refresh token."""
        # Arrange - Register and login to get tokens
        user_data = {
            "email": "wrongtoken@example.com",
            "password": "SecurePass123!",
            "name": "Wrong Token User",
        }
        test_client.post("/auth/register", json=user_data)

        login_response = test_client.post(
            "/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
        )
        tokens = login_response.json()
        access_token = tokens["access_token"]

        # Act - Try to refresh using access token
        refresh_data = {"refresh_token": access_token}
        response = test_client.post("/auth/refresh", json=refresh_data)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "invalid token type" in response_data["detail"]["message"].lower()


class TestLogoutEndpoint:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_success(self, test_client):
        """Test logout endpoint returns success message."""
        # Act
        response = test_client.post("/auth/logout")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "logout successful" in data["message"].lower()


class TestRateLimiting:
    """Tests for rate limiting on authentication endpoints."""

    def test_login_rate_limiting(self, test_client):
        """Test login endpoint rate limiting after multiple failed attempts."""
        # Arrange - Register a user first
        user_data = {
            "email": "ratelimit@example.com",
            "password": "SecurePass123!",
            "name": "Rate Limit User",
        }
        test_client.post("/auth/register", json=user_data)

        # Clear any existing rate limit state
        from src.services.rate_limiter import rate_limiter

        rate_limiter.clear_all()

        # Act - Make multiple login attempts (should exceed rate limit)
        login_data = {"email": "ratelimit@example.com", "password": "WrongPassword123!"}

        # First 5 attempts should be allowed (but fail due to wrong password)
        for i in range(5):
            response = test_client.post("/auth/login", json=login_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # 6th attempt should be rate limited
        response = test_client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "rate limit exceeded" in response.json()["detail"].lower()

        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers

    def test_registration_rate_limiting(self, test_client):
        """Test registration endpoint rate limiting after multiple attempts."""
        # Clear any existing rate limit state
        from src.services.rate_limiter import rate_limiter

        rate_limiter.clear_all()

        # Act - Make multiple registration attempts (should exceed rate limit)
        # First 3 attempts should be allowed (but may fail due to validation)
        for i in range(3):
            user_data = {
                "email": f"ratelimit{i}@example.com",
                "password": "SecurePass123!",
                "name": f"Rate Limit User {i}",
            }
            response = test_client.post("/auth/register", json=user_data)
            # Should succeed or fail with validation, but not rate limit
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

        # 4th attempt should be rate limited
        user_data = {
            "email": "ratelimit4@example.com",
            "password": "SecurePass123!",
            "name": "Rate Limit User 4",
        }
        response = test_client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "rate limit exceeded" in response.json()["detail"].lower()

        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers

    def test_rate_limit_per_ip(self, test_client):
        """Test that rate limiting is applied per IP address."""
        # This test verifies that different IPs have separate rate limits
        # Note: In test environment, all requests come from same IP,
        # so this test mainly verifies the rate limiting logic works

        # Clear any existing rate limit state
        from src.services.rate_limiter import rate_limiter

        rate_limiter.clear_all()

        # Register a user for login tests
        user_data = {
            "email": "iptest@example.com",
            "password": "SecurePass123!",
            "name": "IP Test User",
        }
        test_client.post("/auth/register", json=user_data)

        # Clear rate limit state after registration
        rate_limiter.clear_all()

        # Make login attempts up to the limit
        login_data = {"email": "iptest@example.com", "password": "WrongPassword123!"}

        for i in range(5):
            response = test_client.post("/auth/login", json=login_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Next attempt should be rate limited
        response = test_client.post("/auth/login", json=login_data)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Verify rate limit info is returned
        data = response.json()
        assert "rate limit exceeded" in data["detail"].lower()
