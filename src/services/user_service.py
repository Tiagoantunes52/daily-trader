"""User preference management service."""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.database.models import User


class UserService:
    """Service for managing user delivery preferences."""

    def __init__(self, db_session: Session | None = None):
        """Initialize user service with optional database session."""
        self.db_session = db_session

    def get_user_by_email(self, email: str) -> User | None:
        if not self.db_session:
            return None
        return self.db_session.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> User | None:
        if not self.db_session:
            return None
        if not isinstance(user_id, int) or user_id <= 0:
            return None
        return self.db_session.query(User).filter(User.id == user_id).first()

    def update_email(self, user_id: int, new_email: str) -> User:
        if not self.db_session:
            raise ValueError("Database session required for email update")
        if not self._validate_email(new_email):
            raise ValueError(f"Invalid email format: {new_email}")

        existing = (
            self.db_session.query(User)
            .filter(User.email == new_email, User.id != user_id)
            .first()
        )
        if existing:
            raise ValueError(f"Email already in use: {new_email}")

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        user.email = new_email
        user.updated_at = datetime.now(UTC)
        self.db_session.commit()
        return user

    def update_delivery_times(
        self, user_id: int, morning_time: str | None = None, evening_time: str | None = None
    ) -> User:
        if not self.db_session:
            raise ValueError("Database session required for delivery time update")
        if morning_time and not self._validate_time_format(morning_time):
            raise ValueError(f"Invalid morning time format: {morning_time}")
        if evening_time and not self._validate_time_format(evening_time):
            raise ValueError(f"Invalid evening time format: {evening_time}")

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        if morning_time is not None:
            user.morning_time = morning_time
        if evening_time is not None:
            user.evening_time = evening_time

        user.updated_at = datetime.now(UTC)
        self.db_session.commit()
        return user

    def update_asset_preferences(self, user_id: int, asset_preferences: list[str]) -> User:
        if not self.db_session:
            raise ValueError("Database session required for preference update")
        valid_assets = {"crypto", "stock"}
        if not all(asset in valid_assets for asset in asset_preferences):
            raise ValueError(f"Invalid asset types. Must be one of: {valid_assets}")

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        user.asset_preferences = json.dumps(asset_preferences)
        user.updated_at = datetime.now(UTC)
        self.db_session.commit()
        return user

    def get_asset_preferences(self, user_id: int) -> list[str]:
        user = self.get_user_by_id(user_id)
        if not user or not user.asset_preferences:
            return []
        try:
            return json.loads(str(user.asset_preferences))
        except (json.JSONDecodeError, TypeError):
            return []

    def delete_user(self, user_id: int) -> bool:
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
        if not email or not isinstance(email, str):
            return False
        if "@" not in email:
            return False
        parts = email.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False
        domain = parts[1]
        if "." not in domain:
            return False
        return all(part for part in domain.split("."))

    @staticmethod
    def _validate_time_format(time_str: str) -> bool:
        if not time_str or not isinstance(time_str, str):
            return False
        parts = time_str.split(":")
        if len(parts) != 2:
            return False
        try:
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, TypeError):
            return False
