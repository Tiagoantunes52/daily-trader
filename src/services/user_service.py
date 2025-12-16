"""User profile and configuration management service."""

import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import UserProfile


class UserService:
    """Service for managing user profiles and preferences."""
    
    def __init__(self, db_session: Session = None):
        """Initialize user service with optional database session."""
        self.db_session = db_session
    
    def create_user(
        self,
        email: str,
        morning_time: str = None,
        evening_time: str = None,
        asset_preferences: list[str] = None
    ) -> UserProfile:
        """
        Create a new user profile.
        
        Args:
            email: User email address
            morning_time: Morning delivery time in HH:MM format
            evening_time: Evening delivery time in HH:MM format
            asset_preferences: List of asset types to receive tips for (e.g., ["crypto", "stock"])
            
        Returns:
            Created UserProfile object
        """
        if not self.db_session:
            raise ValueError("Database session required for user creation")
        
        # Validate email format
        if not self._validate_email(email):
            raise ValueError(f"Invalid email format: {email}")
        
        # Validate time format if provided
        if morning_time and not self._validate_time_format(morning_time):
            raise ValueError(f"Invalid morning time format: {morning_time}")
        if evening_time and not self._validate_time_format(evening_time):
            raise ValueError(f"Invalid evening time format: {evening_time}")
        
        user = UserProfile(
            id=str(uuid.uuid4()),
            email=email,
            morning_time=morning_time,
            evening_time=evening_time,
            asset_preferences=json.dumps(asset_preferences) if asset_preferences else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db_session.add(user)
        self.db_session.commit()
        
        return user
    
    def get_user_by_email(self, email: str) -> UserProfile:
        """
        Retrieve user profile by email address.
        
        Args:
            email: User email address
            
        Returns:
            UserProfile object or None if not found
        """
        if not self.db_session:
            return None
        
        return self.db_session.query(UserProfile).filter(
            UserProfile.email == email
        ).first()
    
    def get_user_by_id(self, user_id: str) -> UserProfile:
        """
        Retrieve user profile by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            UserProfile object or None if not found
        """
        if not self.db_session:
            return None
        
        return self.db_session.query(UserProfile).filter(
            UserProfile.id == user_id
        ).first()
    
    def update_email(self, user_id: str, new_email: str) -> UserProfile:
        """
        Update user email address.
        
        Args:
            user_id: User ID
            new_email: New email address
            
        Returns:
            Updated UserProfile object
            
        Raises:
            ValueError: If email is invalid or already in use
        """
        if not self.db_session:
            raise ValueError("Database session required for email update")
        
        # Validate email format
        if not self._validate_email(new_email):
            raise ValueError(f"Invalid email format: {new_email}")
        
        # Check if email is already in use
        existing_user = self.db_session.query(UserProfile).filter(
            UserProfile.email == new_email,
            UserProfile.id != user_id
        ).first()
        
        if existing_user:
            raise ValueError(f"Email already in use: {new_email}")
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        user.email = new_email
        user.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        
        return user
    
    def update_delivery_times(
        self,
        user_id: str,
        morning_time: str = None,
        evening_time: str = None
    ) -> UserProfile:
        """
        Update user delivery times.
        
        Args:
            user_id: User ID
            morning_time: Morning delivery time in HH:MM format
            evening_time: Evening delivery time in HH:MM format
            
        Returns:
            Updated UserProfile object
        """
        if not self.db_session:
            raise ValueError("Database session required for delivery time update")
        
        # Validate time formats
        if morning_time and not self._validate_time_format(morning_time):
            raise ValueError(f"Invalid morning time format: {morning_time}")
        if evening_time and not self._validate_time_format(evening_time):
            raise ValueError(f"Invalid evening time format: {evening_time}")
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        if morning_time:
            user.morning_time = morning_time
        if evening_time:
            user.evening_time = evening_time
        
        user.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        
        return user
    
    def update_asset_preferences(
        self,
        user_id: str,
        asset_preferences: list[str]
    ) -> UserProfile:
        """
        Update user asset preferences.
        
        Args:
            user_id: User ID
            asset_preferences: List of asset types (e.g., ["crypto", "stock"])
            
        Returns:
            Updated UserProfile object
        """
        if not self.db_session:
            raise ValueError("Database session required for preference update")
        
        # Validate asset preferences
        valid_assets = {"crypto", "stock"}
        if not all(asset in valid_assets for asset in asset_preferences):
            raise ValueError(f"Invalid asset types. Must be one of: {valid_assets}")
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        user.asset_preferences = json.dumps(asset_preferences)
        user.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        
        return user
    
    def get_asset_preferences(self, user_id: str) -> list[str]:
        """
        Get user asset preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            List of asset types
        """
        user = self.get_user_by_id(user_id)
        if not user or not user.asset_preferences:
            return []
        
        try:
            return json.loads(user.asset_preferences)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deletion was successful
        """
        if not self.db_session:
            raise ValueError("Database session required for user deletion")
        
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        self.db_session.delete(user)
        self.db_session.commit()
        
        return True
    
    @staticmethod
    def _validate_email(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid
        """
        if not email or not isinstance(email, str):
            return False
        
        # Basic email validation
        if "@" not in email:
            return False
        
        parts = email.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False
        
        # Validate domain part has at least one dot and valid structure
        domain = parts[1]
        if "." not in domain:
            return False
        
        domain_parts = domain.split(".")
        # Check that domain has at least 2 parts (e.g., example.com)
        if len(domain_parts) < 2:
            return False
        
        # Check that each part is non-empty
        if not all(part for part in domain_parts):
            return False
        
        return True
    
    @staticmethod
    def _validate_time_format(time_str: str) -> bool:
        """
        Validate time format (HH:MM).
        
        Args:
            time_str: Time string to validate
            
        Returns:
            True if time format is valid
        """
        if not time_str or not isinstance(time_str, str):
            return False
        
        parts = time_str.split(":")
        if len(parts) != 2:
            return False
        
        try:
            hour = int(parts[0])
            minute = int(parts[1])
            
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                return False
            
            return True
        except (ValueError, TypeError):
            return False
