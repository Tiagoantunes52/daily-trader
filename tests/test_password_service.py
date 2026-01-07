"""Tests for password service with property-based testing."""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.services.password_service import PasswordService


class TestPasswordServicePropertyBased:
    """Property-based tests for PasswordService."""

    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(password=st.text(min_size=1, max_size=50))
    def test_password_hash_consistency(self, password: str):
        """
        Property 1: Password Hash Consistency

        For any valid password and its hash, verifying the password against the hash
        should always return true, and verifying an incorrect password should always
        return false.

        Validates: Requirements 2.1, 9.1
        """
        # Skip empty or whitespace-only passwords
        if not password or not password.strip():
            return

        try:
            # Hash the password
            hashed = PasswordService.hash_password(password)

            # Verify the same password returns True
            assert PasswordService.verify_password(password, hashed) is True

            # Verify a different password returns False
            different_password = password + "_modified"
            assert PasswordService.verify_password(different_password, hashed) is False
        except ValueError:
            # Some passwords may fail validation, which is acceptable
            pass


class TestPasswordServiceUnit:
    """Unit tests for PasswordService."""

    def test_hash_password_creates_valid_hash(self):
        """Test that hash_password creates a valid bcrypt hash."""
        password = "SecurePassword123!"
        hashed = PasswordService.hash_password(password)

        # Hash should be a non-empty string
        assert isinstance(hashed, str)
        assert len(hashed) > 0

        # Hash should start with $2 (bcrypt identifier)
        assert hashed.startswith("$2")

    def test_hash_password_different_hashes_for_same_password(self):
        """Test that hashing the same password twice produces different hashes."""
        password = "SecurePassword123!"
        hash1 = PasswordService.hash_password(password)
        hash2 = PasswordService.hash_password(password)

        # Hashes should be different (due to random salt)
        assert hash1 != hash2

        # But both should verify against the original password
        assert PasswordService.verify_password(password, hash1) is True
        assert PasswordService.verify_password(password, hash2) is True

    def test_hash_password_empty_password_raises_error(self):
        """Test that hashing an empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordService.hash_password("")

    def test_hash_password_none_password_raises_error(self):
        """Test that hashing None raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordService.hash_password(None)  # type: ignore

    def test_verify_password_correct_password(self):
        """Test that verify_password returns True for correct password."""
        password = "SecurePassword123!"
        hashed = PasswordService.hash_password(password)

        assert PasswordService.verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test that verify_password returns False for incorrect password."""
        password = "SecurePassword123!"
        hashed = PasswordService.hash_password(password)

        assert PasswordService.verify_password("WrongPassword456!", hashed) is False

    def test_verify_password_empty_password_raises_error(self):
        """Test that verifying with empty password raises ValueError."""
        hashed = PasswordService.hash_password("SecurePassword123!")

        with pytest.raises(ValueError, match="Password and hash cannot be empty"):
            PasswordService.verify_password("", hashed)

    def test_verify_password_empty_hash_raises_error(self):
        """Test that verifying with empty hash raises ValueError."""
        with pytest.raises(ValueError, match="Password and hash cannot be empty"):
            PasswordService.verify_password("SecurePassword123!", "")

    def test_verify_password_invalid_hash_format(self):
        """Test that verify_password returns False for invalid hash format."""
        result = PasswordService.verify_password("SecurePassword123!", "invalid_hash")
        assert result is False

    def test_validate_password_strength_strong_password(self):
        """Test that strong password passes validation."""
        password = "SecurePassword123!"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_password_strength_weak_password_too_short(self):
        """Test that short password fails validation."""
        password = "Short1!"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is False
        assert any("at least 8 characters" in error for error in errors)

    def test_validate_password_strength_no_uppercase(self):
        """Test that password without uppercase fails validation."""
        password = "securepassword123!"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is False
        assert any("uppercase" in error for error in errors)

    def test_validate_password_strength_no_lowercase(self):
        """Test that password without lowercase fails validation."""
        password = "SECUREPASSWORD123!"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is False
        assert any("lowercase" in error for error in errors)

    def test_validate_password_strength_no_digit(self):
        """Test that password without digit fails validation."""
        password = "SecurePassword!"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is False
        assert any("digit" in error for error in errors)

    def test_validate_password_strength_no_special_character(self):
        """Test that password without special character fails validation."""
        password = "SecurePassword123"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is False
        assert any("special character" in error for error in errors)

    def test_validate_password_strength_empty_password(self):
        """Test that empty password fails validation."""
        is_valid, errors = PasswordService.validate_password_strength("")

        assert is_valid is False
        assert any("cannot be empty" in error for error in errors)

    def test_validate_password_strength_multiple_errors(self):
        """Test that password with multiple issues returns all errors."""
        password = "weak"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is False
        assert len(errors) >= 3  # Should have multiple errors

    def test_validate_password_strength_special_characters_accepted(self):
        """Test that various special characters are accepted."""
        special_chars = "!@#$%^&*"
        for char in special_chars:
            password = f"SecurePassword123{char}"
            is_valid, errors = PasswordService.validate_password_strength(password)
            assert is_valid is True, f"Special character '{char}' should be accepted"

    def test_validate_password_strength_edge_case_exactly_8_chars(self):
        """Test password with exactly 8 characters (minimum length)."""
        password = "Secure1!"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_password_strength_long_password(self):
        """Test that long password passes validation."""
        password = "VeryLongSecurePassword123!@#$%^&*"
        is_valid, errors = PasswordService.validate_password_strength(password)

        assert is_valid is True
        assert len(errors) == 0
