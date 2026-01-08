"""Encryption service for sensitive data like OAuth tokens."""

import base64
import os

from cryptography.fernet import Fernet


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, encryption_key: str | None = None):
        """
        Initialize encryption service with encryption key.

        Args:
            encryption_key: Base64-encoded encryption key. If not provided,
                           will try to get from environment variable ENCRYPTION_KEY.
                           If that's not set, will generate a new key.

        Raises:
            ValueError: If encryption key is invalid
        """
        if encryption_key is None:
            encryption_key = os.getenv("ENCRYPTION_KEY")

        if encryption_key is None:
            # Generate a new key for development/testing
            # In production, this should be set via environment variable
            encryption_key = Fernet.generate_key().decode()

        try:
            # Ensure key is bytes
            if isinstance(encryption_key, str):
                key_bytes = encryption_key.encode()
            else:
                key_bytes = encryption_key

            self._fernet = Fernet(key_bytes)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}") from e

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            ValueError: If plaintext is None or encryption fails
        """
        if plaintext is None:
            raise ValueError("Plaintext cannot be None")

        if not isinstance(plaintext, str):
            raise ValueError("Plaintext must be a string")

        try:
            # Convert string to bytes
            plaintext_bytes = plaintext.encode("utf-8")

            # Encrypt
            encrypted_bytes = self._fernet.encrypt(plaintext_bytes)

            # Return base64-encoded string
            return base64.b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Encryption failed: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If ciphertext is None, invalid, or decryption fails
        """
        if ciphertext is None:
            raise ValueError("Ciphertext cannot be None")

        if not isinstance(ciphertext, str):
            raise ValueError("Ciphertext must be a string")

        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(ciphertext.encode("utf-8"))

            # Decrypt
            plaintext_bytes = self._fernet.decrypt(encrypted_bytes)

            # Return decoded string
            return plaintext_bytes.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}") from e

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.

        Returns:
            Base64-encoded encryption key suitable for use in environment variables
        """
        return Fernet.generate_key().decode()
