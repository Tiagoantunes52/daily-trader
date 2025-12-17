"""Tests for user profile and configuration management."""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from sqlalchemy.orm import Session, sessionmaker
import uuid

from src.services.user_service import UserService
from src.database.models import UserProfile


class TestUserService:
    """Test suite for UserService."""
    
    def test_user_service_initialization(self):
        """Test that user service initializes correctly."""
        service = UserService(db_session=None)
        assert service is not None
    
    def test_create_user_success(self, test_session: Session):
        """Test successful user creation."""
        service = UserService(db_session=test_session)
        
        user = service.create_user(
            email="test@example.com",
            morning_time="06:00",
            evening_time="18:00",
            asset_preferences=["crypto", "stock"]
        )
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.morning_time == "06:00"
        assert user.evening_time == "18:00"
        assert user.id is not None
    
    def test_create_user_without_session_raises_error(self):
        """Test that creating user without session raises error."""
        service = UserService(db_session=None)
        
        with pytest.raises(ValueError, match="Database session required"):
            service.create_user(email="test@example.com")
    
    def test_create_user_invalid_email(self, test_session: Session):
        """Test that invalid email is rejected."""
        service = UserService(db_session=test_session)
        
        with pytest.raises(ValueError, match="Invalid email format"):
            service.create_user(email="invalid-email")
    
    def test_create_user_invalid_morning_time(self, test_session: Session):
        """Test that invalid morning time is rejected."""
        service = UserService(db_session=test_session)
        
        with pytest.raises(ValueError, match="Invalid morning time format"):
            service.create_user(
                email="test@example.com",
                morning_time="25:00"
            )
    
    def test_create_user_invalid_evening_time(self, test_session: Session):
        """Test that invalid evening time is rejected."""
        service = UserService(db_session=test_session)
        
        with pytest.raises(ValueError, match="Invalid evening time format"):
            service.create_user(
                email="test@example.com",
                evening_time="18:60"
            )
    
    def test_get_user_by_email(self, test_session: Session):
        """Test retrieving user by email."""
        service = UserService(db_session=test_session)
        
        created_user = service.create_user(email="test@example.com")
        retrieved_user = service.get_user_by_email("test@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == "test@example.com"
    
    def test_get_user_by_email_not_found(self, test_session: Session):
        """Test retrieving non-existent user by email."""
        service = UserService(db_session=test_session)
        
        user = service.get_user_by_email("nonexistent@example.com")
        assert user is None
    
    def test_get_user_by_id(self, test_session: Session):
        """Test retrieving user by ID."""
        service = UserService(db_session=test_session)
        
        created_user = service.create_user(email="test@example.com")
        retrieved_user = service.get_user_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
    
    def test_get_user_by_id_not_found(self, test_session: Session):
        """Test retrieving non-existent user by ID."""
        service = UserService(db_session=test_session)
        
        user = service.get_user_by_id(str(uuid.uuid4()))
        assert user is None
    
    def test_update_email_success(self, test_session: Session):
        """Test successful email update."""
        service = UserService(db_session=test_session)
        
        user = service.create_user(email="old@example.com")
        updated_user = service.update_email(user.id, "new@example.com")
        
        assert updated_user.email == "new@example.com"
        
        # Verify the change persisted
        retrieved_user = service.get_user_by_email("new@example.com")
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
    
    def test_update_email_invalid_format(self, test_session: Session):
        """Test that invalid email format is rejected."""
        service = UserService(db_session=test_session)
        
        user = service.create_user(email="test@example.com")
        
        with pytest.raises(ValueError, match="Invalid email format"):
            service.update_email(user.id, "invalid-email")
    
    def test_update_email_duplicate(self, test_session: Session):
        """Test that duplicate email is rejected."""
        service = UserService(db_session=test_session)
        
        user1 = service.create_user(email="user1@example.com")
        user2 = service.create_user(email="user2@example.com")
        
        with pytest.raises(ValueError, match="Email already in use"):
            service.update_email(user1.id, "user2@example.com")
    
    def test_update_email_user_not_found(self, test_session: Session):
        """Test updating email for non-existent user."""
        service = UserService(db_session=test_session)
        
        with pytest.raises(ValueError, match="User not found"):
            service.update_email(str(uuid.uuid4()), "new@example.com")
    
    def test_update_delivery_times(self, test_session: Session):
        """Test updating delivery times."""
        service = UserService(db_session=test_session)
        
        user = service.create_user(email="test@example.com")
        updated_user = service.update_delivery_times(
            user.id,
            morning_time="07:00",
            evening_time="19:00"
        )
        
        assert updated_user.morning_time == "07:00"
        assert updated_user.evening_time == "19:00"
    
    def test_update_asset_preferences(self, test_session: Session):
        """Test updating asset preferences."""
        service = UserService(db_session=test_session)
        
        user = service.create_user(email="test@example.com")
        updated_user = service.update_asset_preferences(
            user.id,
            asset_preferences=["crypto"]
        )
        
        prefs = service.get_asset_preferences(user.id)
        assert prefs == ["crypto"]
    
    def test_get_asset_preferences(self, test_session: Session):
        """Test retrieving asset preferences."""
        service = UserService(db_session=test_session)
        
        user = service.create_user(
            email="test@example.com",
            asset_preferences=["crypto", "stock"]
        )
        
        prefs = service.get_asset_preferences(user.id)
        assert prefs == ["crypto", "stock"]
    
    def test_delete_user(self, test_session: Session):
        """Test user deletion."""
        service = UserService(db_session=test_session)
        
        user = service.create_user(email="test@example.com")
        success = service.delete_user(user.id)
        
        assert success is True
        
        # Verify user is deleted
        retrieved_user = service.get_user_by_id(user.id)
        assert retrieved_user is None
    
    def test_delete_user_not_found(self, test_session: Session):
        """Test deleting non-existent user."""
        service = UserService(db_session=test_session)
        
        success = service.delete_user(str(uuid.uuid4()))
        assert success is False
    
    @given(st.emails())
    @settings(max_examples=100, deadline=None)
    def test_email_address_updates_are_used(self, new_email: str):
        """
        **Feature: daily-market-tips, Property 8: Updated email addresses are used**
        
        For any user email address update, all subsequent deliveries SHALL use the new
        email address. When a user's email is updated in the system, the new email
        should be persisted and retrievable, ensuring that future email deliveries
        use the updated address.
        
        **Validates: Requirements 3.4**
        """
        # Create a fresh database session for each example
        from sqlalchemy import create_engine
        import tempfile
        import os
        
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False}
        )
        
        from src.database.models import Base
        Base.metadata.create_all(bind=engine)
        
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = TestingSessionLocal()
        
        try:
            service = UserService(db_session=session)
            
            # Create initial user with a valid email
            initial_email = "initial@example.com"
            user = service.create_user(email=initial_email)
            user_id = user.id
            
            # Update email to the generated email
            updated_user = service.update_email(user_id, new_email)
            
            # Verify the email was updated
            assert updated_user.email == new_email
            
            # Verify subsequent retrieval uses the new email
            retrieved_user = service.get_user_by_email(new_email)
            assert retrieved_user is not None
            assert retrieved_user.id == user_id
            assert retrieved_user.email == new_email
            
            # Verify old email no longer retrieves the user
            old_user = service.get_user_by_email(initial_email)
            assert old_user is None
            
        finally:
            session.close()
            engine.dispose()
            try:
                os.unlink(db_path)
            except:
                pass


class TestEmailValidation:
    """Tests for email validation."""
    
    def test_validate_email_valid_formats(self):
        """Test validation of valid email formats."""
        service = UserService()
        
        valid_emails = [
            "test@example.com",
            "user.name@example.co.uk",
            "user+tag@example.com",
            "123@example.com"
        ]
        
        for email in valid_emails:
            assert service._validate_email(email) is True
    
    def test_validate_email_invalid_formats(self):
        """Test validation of invalid email formats."""
        service = UserService()
        
        invalid_emails = [
            "invalid",
            "invalid@",
            "@example.com",
            "invalid@.com",
            "",
            None
        ]
        
        for email in invalid_emails:
            assert service._validate_email(email) is False


class TestTimeValidation:
    """Tests for time format validation."""
    
    def test_validate_time_valid_formats(self):
        """Test validation of valid time formats."""
        service = UserService()
        
        valid_times = [
            "00:00",
            "06:00",
            "12:30",
            "18:45",
            "23:59"
        ]
        
        for time_str in valid_times:
            assert service._validate_time_format(time_str) is True
    
    def test_validate_time_invalid_formats(self):
        """Test validation of invalid time formats."""
        service = UserService()
        
        invalid_times = [
            "24:00",
            "12:60",
            "25:30",
            "12",
            "12:30:00",
            "invalid",
            "",
            None
        ]
        
        for time_str in invalid_times:
            assert service._validate_time_format(time_str) is False
