"""User authentication service for CRUD operations."""

from sqlalchemy.orm import Session

from src.database.models import User


class AuthUserService:
    """Service for managing user authentication and CRUD operations."""

    def __init__(self, db_session: Session):
        """Initialize auth user service with database session."""
        if not db_session:
            raise ValueError("Database session is required")
        self.db_session = db_session

    def create_user(self, email: str, password_hash: str, name: str) -> User:
        """
        Create a new user with authentication credentials.

        Args:
            email: User email address (must be unique)
            password_hash: Hashed password
            name: User's display name

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists or inputs are invalid
        """
        if not email or not isinstance(email, str):
            raise ValueError("Email must be a non-empty string")
        if not password_hash or not isinstance(password_hash, str):
            raise ValueError("Password hash must be a non-empty string")
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")

        # Check if email already exists
        existing_user = self.db_session.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError(f"Email already registered: {email}")

        user = User(email=email, password_hash=password_hash, name=name.strip())
        self.db_session.add(user)
        self.db_session.commit()
        self.db_session.refresh(user)

        return user

    def get_user_by_email(self, email: str) -> User | None:
        """
        Retrieve user by email address.

        Args:
            email: User email address

        Returns:
            User object or None if not found
        """
        if not email or not isinstance(email, str):
            return None

        return self.db_session.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> User | None:
        """
        Retrieve user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return None

        return self.db_session.query(User).filter(User.id == user_id).first()

    def update_user(self, user_id: int, **kwargs) -> User:
        """
        Update user information.

        Args:
            user_id: User ID
            **kwargs: Fields to update (email, name, password_hash, is_email_verified)

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found or email already in use
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("User ID must be a positive integer")

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Check if email is being updated and if it's already in use
        if "email" in kwargs:
            new_email = kwargs["email"]
            if not new_email or not isinstance(new_email, str):
                raise ValueError("Email must be a non-empty string")

            existing_user = (
                self.db_session.query(User)
                .filter(User.email == new_email, User.id != user_id)
                .first()
            )
            if existing_user:
                raise ValueError(f"Email already in use: {new_email}")

        # Update allowed fields
        allowed_fields = {"email", "name", "password_hash", "is_email_verified"}
        for field, value in kwargs.items():
            if field not in allowed_fields:
                raise ValueError(f"Cannot update field: {field}")

            if field == "name" and value:
                value = value.strip()
            if field == "email" and value:
                value = value.lower()

            setattr(user, field, value)

        self.db_session.commit()
        self.db_session.refresh(user)

        return user

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user and all associated data.

        Args:
            user_id: User ID

        Returns:
            True if deletion was successful, False if user not found
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("User ID must be a positive integer")

        user = self.get_user_by_id(user_id)
        if not user:
            return False

        self.db_session.delete(user)
        self.db_session.commit()

        return True

    def user_exists(self, email: str) -> bool:
        """
        Check if a user exists by email.

        Args:
            email: User email address

        Returns:
            True if user exists, False otherwise
        """
        if not email or not isinstance(email, str):
            return False

        user = self.db_session.query(User).filter(User.email == email).first()
        return user is not None
