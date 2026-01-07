"""Password hashing and validation service."""

import re

import bcrypt


class PasswordService:
    """Service for password hashing, verification, and validation."""

    # Password strength requirements
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    BCRYPT_ROUNDS = 12

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with 12+ rounds.

        Args:
            password: The plaintext password to hash

        Returns:
            The hashed password as a string

        Raises:
            ValueError: If password is empty or None
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Generate salt and hash password with bcrypt
        salt = bcrypt.gensalt(rounds=PasswordService.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a plaintext password against a bcrypt hash.

        Args:
            password: The plaintext password to verify
            password_hash: The bcrypt hash to verify against

        Returns:
            True if password matches hash, False otherwise

        Raises:
            ValueError: If password or hash is empty
        """
        if not password or not password_hash:
            raise ValueError("Password and hash cannot be empty")

        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except (ValueError, TypeError):
            # Invalid hash format
            return False

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, list[str]]:
        """
        Validate password strength against security requirements.

        Args:
            password: The password to validate

        Returns:
            A tuple of (is_valid, error_messages) where is_valid is True if password
            meets all requirements, and error_messages is a list of validation errors

        Requirements:
            - Minimum 8 characters
            - At least one uppercase letter
            - At least one lowercase letter
            - At least one digit
            - At least one special character (!@#$%^&*)
        """
        errors = []

        if not password:
            errors.append("Password cannot be empty")
            return False, errors

        if len(password) < PasswordService.MIN_LENGTH:
            errors.append(f"Password must be at least {PasswordService.MIN_LENGTH} characters long")

        if PasswordService.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if PasswordService.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if PasswordService.REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if PasswordService.REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*]", password):
            errors.append("Password must contain at least one special character (!@#$%^&*)")

        is_valid = len(errors) == 0
        return is_valid, errors
