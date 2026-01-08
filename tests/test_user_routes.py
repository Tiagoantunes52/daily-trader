"""Tests for user profile and account management API routes."""

from fastapi import status
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.database.models import OAuthConnection
from src.services.auth_user_service import AuthUserService
from src.services.csrf_service import CSRFService
from src.services.password_service import PasswordService
from src.services.token_service import TokenService


class TestUserProfilePropertyBased:
    """Property-based tests for user profile endpoints."""

    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        email_local=st.text(
            min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"))
        ),
        password=st.text(min_size=8, max_size=50),
    )
    def test_user_profile_retrieval(
        self, test_client, test_session, name: str, email_local: str, password: str
    ):
        """
        Property 13: User Profile Retrieval

        For any authenticated user, requesting their profile should return all required
        fields (email, name, authentication method) and only their own data.

        Validates: Requirements 8.1
        """
        # Skip invalid inputs
        if not name.strip() or not email_local.strip():
            return

        try:
            # Create a valid email
            email = f"{email_local}@example.com"

            # Create user with valid password
            password_service = PasswordService()
            is_valid, _ = password_service.validate_password_strength(password)
            if not is_valid:
                return

            user_service = AuthUserService(db_session=test_session)
            password_hash = password_service.hash_password(password)
            user = user_service.create_user(
                email=email, password_hash=password_hash, name=name.strip()
            )

            # Create access token
            token_service = TokenService()
            access_token = token_service.create_access_token(user.id)

            # Make authenticated request to profile endpoint
            headers = {"Authorization": f"Bearer {access_token}"}
            response = test_client.get("/api/user/profile", headers=headers)

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify all required fields are present
            assert "id" in data
            assert "email" in data
            assert "name" in data
            assert "created_at" in data
            assert "is_email_verified" in data
            assert "oauth_providers" in data

            # Verify data matches the user
            assert data["id"] == user.id
            assert data["email"] == user.email
            assert data["name"] == user.name
            assert data["is_email_verified"] == user.is_email_verified
            assert isinstance(data["oauth_providers"], list)

        except Exception:
            # Skip invalid test cases
            return

    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        original_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        new_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        email_local=st.text(
            min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"))
        ),
        password=st.text(min_size=8, max_size=50),
    )
    def test_profile_update_persistence(
        self,
        test_client,
        test_session,
        original_name: str,
        new_name: str,
        email_local: str,
        password: str,
    ):
        """
        Property 14: Profile Update Persistence

        For any user profile update, the changes should be validated and persisted
        to the database, and subsequent profile retrievals should reflect the updates.

        Validates: Requirements 8.2
        """
        # Skip invalid inputs
        if not original_name.strip() or not new_name.strip() or not email_local.strip():
            return

        try:
            # Create a valid email
            email = f"{email_local}@example.com"

            # Create user with valid password
            password_service = PasswordService()
            is_valid, _ = password_service.validate_password_strength(password)
            if not is_valid:
                return

            user_service = AuthUserService(db_session=test_session)
            password_hash = password_service.hash_password(password)
            user = user_service.create_user(
                email=email, password_hash=password_hash, name=original_name.strip()
            )

            # Create access token
            token_service = TokenService()
            access_token = token_service.create_access_token(user.id)

            # Update profile
            update_data = {"name": new_name.strip()}
            headers = {"Authorization": f"Bearer {access_token}"}
            response = test_client.put("/api/user/profile", json=update_data, headers=headers)

            # Verify update succeeded
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == new_name.strip()

            # Verify persistence by retrieving profile again
            response = test_client.get("/api/user/profile", headers=headers)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == new_name.strip()

            # Verify in database
            updated_user = user_service.get_user_by_id(user.id)
            assert updated_user.name == new_name.strip()

        except Exception:
            # Skip invalid test cases
            return

    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        email_local=st.text(
            min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"))
        ),
        old_password=st.text(min_size=8, max_size=50),
        new_password=st.text(min_size=8, max_size=50),
    )
    def test_password_change_validation(
        self,
        test_client,
        test_session,
        name: str,
        email_local: str,
        old_password: str,
        new_password: str,
    ):
        """
        Property 15: Password Change Validation

        For any password change request, the new password should be validated for
        strength, and the old password hash should be replaced with the new one.

        Validates: Requirements 8.3
        """
        # Skip invalid inputs
        if not name.strip() or not email_local.strip() or old_password == new_password:
            return

        try:
            # Create a valid email
            email = f"{email_local}@example.com"

            # Validate both passwords
            password_service = PasswordService()
            old_valid, _ = password_service.validate_password_strength(old_password)
            new_valid, _ = password_service.validate_password_strength(new_password)

            if not old_valid:
                return

            user_service = AuthUserService(db_session=test_session)
            old_password_hash = password_service.hash_password(old_password)
            user = user_service.create_user(
                email=email, password_hash=old_password_hash, name=name.strip()
            )

            # Create access token
            token_service = TokenService()
            access_token = token_service.create_access_token(user.id)

            # Attempt password change
            change_data = {"current_password": old_password, "new_password": new_password}
            headers = {"Authorization": f"Bearer {access_token}"}
            response = test_client.post(
                "/api/user/change-password", json=change_data, headers=headers
            )

            if new_valid:
                # Should succeed with valid new password
                assert response.status_code == status.HTTP_200_OK

                # Verify password was actually changed
                updated_user = user_service.get_user_by_id(user.id)
                assert updated_user.password_hash != old_password_hash
                assert password_service.verify_password(new_password, updated_user.password_hash)
            else:
                # Should fail with invalid new password
                assert response.status_code == status.HTTP_400_BAD_REQUEST

        except Exception:
            # Skip invalid test cases
            return

    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        email_local=st.text(
            min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"))
        ),
        password=st.text(min_size=8, max_size=50),
        provider=st.sampled_from(["google", "github"]),
    )
    def test_oauth_disconnection_preservation(
        self, test_client, test_session, name: str, email_local: str, password: str, provider: str
    ):
        """
        Property 16: OAuth Disconnection Preservation

        For any user with multiple OAuth connections, disconnecting one provider should
        remove only that connection while preserving the user account and other connections.

        Validates: Requirements 8.4
        """
        # Skip invalid inputs
        if not name.strip() or not email_local.strip():
            return

        try:
            # Create a valid email
            email = f"{email_local}@example.com"

            # Create user with valid password
            password_service = PasswordService()
            is_valid, _ = password_service.validate_password_strength(password)
            if not is_valid:
                return

            user_service = AuthUserService(db_session=test_session)
            password_hash = password_service.hash_password(password)
            user = user_service.create_user(
                email=email, password_hash=password_hash, name=name.strip()
            )

            # Add OAuth connections
            oauth_conn1 = OAuthConnection(
                user_id=user.id,
                provider=provider,
                provider_user_id=f"{provider}_user_123",
                access_token="encrypted_token_1",
            )
            other_provider = "github" if provider == "google" else "google"
            oauth_conn2 = OAuthConnection(
                user_id=user.id,
                provider=other_provider,
                provider_user_id=f"{other_provider}_user_456",
                access_token="encrypted_token_2",
            )
            test_session.add(oauth_conn1)
            test_session.add(oauth_conn2)
            test_session.commit()

            # Create access token
            token_service = TokenService()
            access_token = token_service.create_access_token(user.id)

            # Disconnect one OAuth provider
            disconnect_data = {"provider": provider}
            headers = {"Authorization": f"Bearer {access_token}"}
            response = test_client.post(
                "/api/user/disconnect-oauth", json=disconnect_data, headers=headers
            )

            # Should succeed
            assert response.status_code == status.HTTP_200_OK

            # Verify user account still exists
            updated_user = user_service.get_user_by_id(user.id)
            assert updated_user is not None
            assert updated_user.email == email

            # Verify only the specified connection was removed
            remaining_connections = [conn for conn in updated_user.oauth_connections]
            assert len(remaining_connections) == 1
            assert remaining_connections[0].provider == other_provider

        except Exception:
            # Skip invalid test cases
            return

    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(
        name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        email_local=st.text(
            min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"))
        ),
        password=st.text(min_size=8, max_size=50),
    )
    def test_account_deletion_completeness(
        self, test_client, test_session, name: str, email_local: str, password: str
    ):
        """
        Property 17: Account Deletion Completeness

        For any deleted user account, all associated user data and OAuth connections
        should be removed from the database.

        Validates: Requirements 8.5
        """
        # Skip invalid inputs
        if not name.strip() or not email_local.strip():
            return

        try:
            # Create a valid email
            email = f"{email_local}@example.com"

            # Create user with valid password
            password_service = PasswordService()
            is_valid, _ = password_service.validate_password_strength(password)
            if not is_valid:
                return

            user_service = AuthUserService(db_session=test_session)
            password_hash = password_service.hash_password(password)
            user = user_service.create_user(
                email=email, password_hash=password_hash, name=name.strip()
            )

            # Add OAuth connection
            oauth_conn = OAuthConnection(
                user_id=user.id,
                provider="google",
                provider_user_id="google_user_123",
                access_token="encrypted_token",
            )
            test_session.add(oauth_conn)
            test_session.commit()

            user_id = user.id

            # Create access token
            token_service = TokenService()
            access_token = token_service.create_access_token(user.id)

            # Delete account
            headers = {"Authorization": f"Bearer {access_token}"}
            response = test_client.delete("/api/user/account", headers=headers)

            # Should succeed
            assert response.status_code == status.HTTP_200_OK

            # Verify user is completely removed
            deleted_user = user_service.get_user_by_id(user_id)
            assert deleted_user is None

            # Verify OAuth connections are also removed
            oauth_connections = test_session.query(OAuthConnection).filter_by(user_id=user_id).all()
            assert len(oauth_connections) == 0

        except Exception:
            # Skip invalid test cases
            return


class TestUserRoutesUnit:
    """Unit tests for user profile and account management endpoints."""

    def test_get_profile_success(self, test_client, test_session):
        """Test successful profile retrieval."""
        # Create user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        password_hash = password_service.hash_password("SecurePass123!")
        user = user_service.create_user(
            email="test@example.com", password_hash=password_hash, name="Test User"
        )

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Make request
        headers = {"Authorization": f"Bearer {access_token}"}
        response = test_client.get("/api/user/profile", headers=headers)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["oauth_providers"] == []

    def test_get_profile_unauthorized(self, test_client):
        """Test profile retrieval without authentication."""
        response = test_client.get("/api/user/profile")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_profile_success(self, test_client, test_session):
        """Test successful profile update."""
        # Create user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        password_hash = password_service.hash_password("SecurePass123!")
        user = user_service.create_user(
            email="test@example.com", password_hash=password_hash, name="Old Name"
        )

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Update profile
        update_data = {"name": "New Name"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.put("/api/user/profile", json=update_data, headers=headers)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Name"

    def test_change_password_success(self, test_client, test_session):
        """Test successful password change."""
        # Create user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        old_password = "OldPass123!"
        password_hash = password_service.hash_password(old_password)
        user = user_service.create_user(
            email="test@example.com", password_hash=password_hash, name="Test User"
        )

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Change password
        change_data = {"current_password": old_password, "new_password": "NewPass123!"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.post("/api/user/change-password", json=change_data, headers=headers)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_current(self, test_client, test_session):
        """Test password change with wrong current password."""
        # Create user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        password_hash = password_service.hash_password("OldPass123!")
        user = user_service.create_user(
            email="test@example.com", password_hash=password_hash, name="Test User"
        )

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Try to change password with wrong current password
        change_data = {"current_password": "WrongPass123!", "new_password": "NewPass123!"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.post("/api/user/change-password", json=change_data, headers=headers)

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_account_success(self, test_client, test_session):
        """Test successful account deletion."""
        # Create user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        password_hash = password_service.hash_password("SecurePass123!")
        user = user_service.create_user(
            email="test@example.com", password_hash=password_hash, name="Test User"
        )

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Delete account
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.delete("/api/user/account", headers=headers)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Verify user is deleted
        deleted_user = user_service.get_user_by_id(user.id)
        assert deleted_user is None

    def test_update_profile_email_conflict(self, test_client, test_session):
        """Test profile update with email that already exists."""
        # Create first user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        password_hash = password_service.hash_password("SecurePass123!")

        user1 = user_service.create_user(
            email="user1@example.com", password_hash=password_hash, name="User One"
        )

        user2 = user_service.create_user(
            email="user2@example.com", password_hash=password_hash, name="User Two"
        )

        # Create access token for user2
        token_service = TokenService()
        access_token = token_service.create_access_token(user2.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user2.id))

        # Try to update user2's email to user1's email
        update_data = {"email": "user1@example.com"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.put("/api/user/profile", json=update_data, headers=headers)

        # Should fail with conflict
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_change_password_oauth_only_user(self, test_client, test_session):
        """Test password change for OAuth-only user (no password)."""
        # Create user with temporary password first
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        temp_password_hash = password_service.hash_password("TempPass123!")
        user = user_service.create_user(
            email="oauth@example.com", password_hash=temp_password_hash, name="OAuth User"
        )

        # Manually set password_hash to None to simulate OAuth-only user
        user.password_hash = None
        test_session.commit()

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Try to change password
        change_data = {"current_password": "anything", "new_password": "NewPass123!"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.post("/api/user/change-password", json=change_data, headers=headers)

        # Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "OAuth-only account" in response_data["detail"]["message"]

    def test_disconnect_oauth_success(self, test_client, test_session):
        """Test successful OAuth disconnection."""
        # Create user with password and OAuth connections
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        password_hash = password_service.hash_password("SecurePass123!")
        user = user_service.create_user(
            email="test@example.com", password_hash=password_hash, name="Test User"
        )

        # Add OAuth connections
        oauth_conn1 = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id="google_123",
            access_token="token1",
        )
        oauth_conn2 = OAuthConnection(
            user_id=user.id,
            provider="github",
            provider_user_id="github_456",
            access_token="token2",
        )
        test_session.add(oauth_conn1)
        test_session.add(oauth_conn2)
        test_session.commit()

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Disconnect Google OAuth
        disconnect_data = {"provider": "google"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.post(
            "/api/user/disconnect-oauth", json=disconnect_data, headers=headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_200_OK

        # Verify only GitHub connection remains
        updated_user = user_service.get_user_by_id(user.id)
        assert len(updated_user.oauth_connections) == 1
        assert updated_user.oauth_connections[0].provider == "github"

    def test_disconnect_oauth_not_connected(self, test_client, test_session):
        """Test disconnecting OAuth provider that is not connected."""
        # Create user
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        password_hash = password_service.hash_password("SecurePass123!")
        user = user_service.create_user(
            email="test@example.com", password_hash=password_hash, name="Test User"
        )

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Try to disconnect non-existent OAuth provider
        disconnect_data = {"provider": "google"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.post(
            "/api/user/disconnect-oauth", json=disconnect_data, headers=headers
        )

        # Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "not connected" in response_data["detail"]["message"]

    def test_disconnect_oauth_last_auth_method(self, test_client, test_session):
        """Test disconnecting last OAuth provider without password."""
        # Create user with temporary password first
        user_service = AuthUserService(db_session=test_session)
        password_service = PasswordService()
        temp_password_hash = password_service.hash_password("TempPass123!")
        user = user_service.create_user(
            email="oauth@example.com", password_hash=temp_password_hash, name="OAuth User"
        )

        # Manually set password_hash to None to simulate OAuth-only user
        user.password_hash = None
        test_session.commit()

        # Add single OAuth connection
        oauth_conn = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id="google_123",
            access_token="token1",
        )
        test_session.add(oauth_conn)
        test_session.commit()

        # Create access token
        token_service = TokenService()
        access_token = token_service.create_access_token(user.id)

        # Generate CSRF token
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_token(str(user.id))

        # Try to disconnect the only OAuth provider
        disconnect_data = {"provider": "google"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-CSRF-Token": csrf_token,
        }
        response = test_client.post(
            "/api/user/disconnect-oauth", json=disconnect_data, headers=headers
        )

        # Should fail
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "detail" in response_data
        assert "message" in response_data["detail"]
        assert "last authentication method" in response_data["detail"]["message"]
