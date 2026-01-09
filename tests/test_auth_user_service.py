"""Tests for authentication user service with property-based testing."""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy.orm import Session

from src.database.models import User
from src.services.auth_user_service import AuthUserService


class TestAuthUserServicePropertyBased:
    """Property-based tests for AuthUserService."""

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(email=st.emails())
    def test_email_uniqueness_enforcement(self, email: str, test_session: Session):
        """
        Property 9: Email Uniqueness Enforcement

        For any email address, attempting to register two different users with the same
        email should fail on the second attempt with a conflict error.

        Validates: Requirements 1.2
        """
        # Clear any existing data from previous examples
        test_session.query(User).delete()
        test_session.commit()

        service = AuthUserService(db_session=test_session)

        # Create first user with the email
        user1 = service.create_user(email=email, password_hash="hash1", name="User One")
        assert user1 is not None
        assert user1.email == email

        # Attempt to create second user with same email should fail
        with pytest.raises(ValueError, match="Email already registered"):
            service.create_user(email=email, password_hash="hash2", name="User Two")

        # Verify only first user exists
        retrieved_user = service.get_user_by_email(email)
        assert retrieved_user is not None
        assert retrieved_user.id == user1.id


class TestAuthUserServiceUnit:
    """Unit tests for AuthUserService."""

    def test_create_user_success(self, test_session: Session):
        """Test successful user creation."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(
            email="test@example.com", password_hash="hashed_password", name="Test User"
        )

        assert user is not None
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.name == "Test User"
        assert user.is_email_verified is False

    def test_create_user_without_session_raises_error(self):
        """Test that creating user without session raises error."""
        with pytest.raises(ValueError, match="Database session is required"):
            AuthUserService(db_session=None)

    def test_create_user_invalid_email_empty(self, test_session: Session):
        """Test that empty email is rejected."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="Email must be a non-empty string"):
            service.create_user(email="", password_hash="hash", name="User")

    def test_create_user_invalid_email_none(self, test_session: Session):
        """Test that None email is rejected."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="Email must be a non-empty string"):
            service.create_user(email=None, password_hash="hash", name="User")  # type: ignore

    def test_create_user_invalid_password_hash_empty(self, test_session: Session):
        """Test that empty password hash is rejected."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="Password hash must be a non-empty string"):
            service.create_user(email="test@example.com", password_hash="", name="User")

    def test_create_user_invalid_password_hash_none(self, test_session: Session):
        """Test that None password hash is rejected."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="Password hash must be a non-empty string"):
            service.create_user(
                email="test@example.com",
                password_hash=None,
                name="User",  # type: ignore
            )

    def test_create_user_invalid_name_empty(self, test_session: Session):
        """Test that empty name is rejected."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="Name must be a non-empty string"):
            service.create_user(email="test@example.com", password_hash="hash", name="")

    def test_create_user_invalid_name_none(self, test_session: Session):
        """Test that None name is rejected."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="Name must be a non-empty string"):
            service.create_user(
                email="test@example.com",
                password_hash="hash",
                name=None,  # type: ignore
            )

    def test_create_user_duplicate_email(self, test_session: Session):
        """Test that duplicate email is rejected."""
        service = AuthUserService(db_session=test_session)

        service.create_user(email="test@example.com", password_hash="hash1", name="User One")

        with pytest.raises(ValueError, match="Email already registered"):
            service.create_user(email="test@example.com", password_hash="hash2", name="User Two")

    def test_create_user_name_trimmed(self, test_session: Session):
        """Test that user name is trimmed of whitespace."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(
            email="test@example.com", password_hash="hash", name="  Test User  "
        )

        assert user.name == "Test User"

    def test_get_user_by_email_success(self, test_session: Session):
        """Test retrieving user by email."""
        service = AuthUserService(db_session=test_session)

        created_user = service.create_user(
            email="test@example.com", password_hash="hash", name="Test User"
        )

        retrieved_user = service.get_user_by_email("test@example.com")

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == "test@example.com"

    def test_get_user_by_email_not_found(self, test_session: Session):
        """Test retrieving non-existent user by email."""
        service = AuthUserService(db_session=test_session)

        user = service.get_user_by_email("nonexistent@example.com")

        assert user is None

    def test_get_user_by_email_invalid_email_empty(self, test_session: Session):
        """Test that empty email returns None."""
        service = AuthUserService(db_session=test_session)

        user = service.get_user_by_email("")

        assert user is None

    def test_get_user_by_email_invalid_email_none(self, test_session: Session):
        """Test that None email returns None."""
        service = AuthUserService(db_session=test_session)

        user = service.get_user_by_email(None)  # type: ignore

        assert user is None

    def test_get_user_by_id_success(self, test_session: Session):
        """Test retrieving user by ID."""
        service = AuthUserService(db_session=test_session)

        created_user = service.create_user(
            email="test@example.com", password_hash="hash", name="Test User"
        )

        retrieved_user = service.get_user_by_id(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id

    def test_get_user_by_id_not_found(self, test_session: Session):
        """Test retrieving non-existent user by ID."""
        service = AuthUserService(db_session=test_session)

        user = service.get_user_by_id(99999)

        assert user is None

    def test_get_user_by_id_invalid_id_zero(self, test_session: Session):
        """Test that ID of 0 returns None."""
        service = AuthUserService(db_session=test_session)

        user = service.get_user_by_id(0)

        assert user is None

    def test_get_user_by_id_invalid_id_negative(self, test_session: Session):
        """Test that negative ID returns None."""
        service = AuthUserService(db_session=test_session)

        user = service.get_user_by_id(-1)

        assert user is None

    def test_update_user_name(self, test_session: Session):
        """Test updating user name."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="test@example.com", password_hash="hash", name="Old Name")

        updated_user = service.update_user(user.id, name="New Name")

        assert updated_user.name == "New Name"
        assert updated_user.id == user.id

    def test_update_user_email(self, test_session: Session):
        """Test updating user email."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="old@example.com", password_hash="hash", name="User")

        updated_user = service.update_user(user.id, email="new@example.com")

        assert updated_user.email == "new@example.com"

        # Verify old email no longer retrieves user
        old_user = service.get_user_by_email("old@example.com")
        assert old_user is None

        # Verify new email retrieves user
        new_user = service.get_user_by_email("new@example.com")
        assert new_user is not None
        assert new_user.id == user.id

    def test_update_user_password_hash(self, test_session: Session):
        """Test updating user password hash."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="test@example.com", password_hash="old_hash", name="User")

        updated_user = service.update_user(user.id, password_hash="new_hash")

        assert updated_user.password_hash == "new_hash"

    def test_update_user_is_email_verified(self, test_session: Session):
        """Test updating email verification status."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="test@example.com", password_hash="hash", name="User")

        assert user.is_email_verified is False

        updated_user = service.update_user(user.id, is_email_verified=True)

        assert updated_user.is_email_verified is True

    def test_update_user_multiple_fields(self, test_session: Session):
        """Test updating multiple user fields at once."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="test@example.com", password_hash="hash", name="User")

        updated_user = service.update_user(
            user.id, name="New Name", email="new@example.com", is_email_verified=True
        )

        assert updated_user.name == "New Name"
        assert updated_user.email == "new@example.com"
        assert updated_user.is_email_verified is True

    def test_update_user_not_found(self, test_session: Session):
        """Test updating non-existent user."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="User not found"):
            service.update_user(99999, name="New Name")

    def test_update_user_invalid_id_zero(self, test_session: Session):
        """Test updating with ID of 0."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            service.update_user(0, name="New Name")

    def test_update_user_invalid_id_negative(self, test_session: Session):
        """Test updating with negative ID."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            service.update_user(-1, name="New Name")

    def test_update_user_duplicate_email(self, test_session: Session):
        """Test that updating to duplicate email is rejected."""
        service = AuthUserService(db_session=test_session)

        user1 = service.create_user(
            email="user1@example.com", password_hash="hash1", name="User One"
        )
        service.create_user(email="user2@example.com", password_hash="hash2", name="User Two")

        with pytest.raises(ValueError, match="Email already in use"):
            service.update_user(user1.id, email="user2@example.com")

    def test_update_user_invalid_field(self, test_session: Session):
        """Test that updating invalid field is rejected."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="test@example.com", password_hash="hash", name="User")

        with pytest.raises(ValueError, match="Cannot update field"):
            service.update_user(user.id, invalid_field="value")  # type: ignore

    def test_update_user_name_trimmed(self, test_session: Session):
        """Test that updated name is trimmed."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="test@example.com", password_hash="hash", name="User")

        updated_user = service.update_user(user.id, name="  New Name  ")

        assert updated_user.name == "New Name"

    def test_delete_user_success(self, test_session: Session):
        """Test successful user deletion."""
        service = AuthUserService(db_session=test_session)

        user = service.create_user(email="test@example.com", password_hash="hash", name="User")

        success = service.delete_user(user.id)

        assert success is True

        # Verify user is deleted
        retrieved_user = service.get_user_by_id(user.id)
        assert retrieved_user is None

    def test_delete_user_not_found(self, test_session: Session):
        """Test deleting non-existent user."""
        service = AuthUserService(db_session=test_session)

        success = service.delete_user(99999)

        assert success is False

    def test_delete_user_invalid_id_zero(self, test_session: Session):
        """Test deleting with ID of 0."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            service.delete_user(0)

    def test_delete_user_invalid_id_negative(self, test_session: Session):
        """Test deleting with negative ID."""
        service = AuthUserService(db_session=test_session)

        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            service.delete_user(-1)

    def test_user_exists_true(self, test_session: Session):
        """Test user_exists returns True for existing user."""
        service = AuthUserService(db_session=test_session)

        service.create_user(email="test@example.com", password_hash="hash", name="User")

        exists = service.user_exists("test@example.com")

        assert exists is True

    def test_user_exists_false(self, test_session: Session):
        """Test user_exists returns False for non-existent user."""
        service = AuthUserService(db_session=test_session)

        exists = service.user_exists("nonexistent@example.com")

        assert exists is False

    def test_user_exists_invalid_email_empty(self, test_session: Session):
        """Test user_exists with empty email."""
        service = AuthUserService(db_session=test_session)

        exists = service.user_exists("")

        assert exists is False

    def test_user_exists_invalid_email_none(self, test_session: Session):
        """Test user_exists with None email."""
        service = AuthUserService(db_session=test_session)

        exists = service.user_exists(None)  # type: ignore

        assert exists is False
