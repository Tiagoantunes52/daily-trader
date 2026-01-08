"""Tests for encryption service."""

import pytest

from src.services.encryption_service import EncryptionService


class TestEncryptionServiceUnitTests:
    """Unit tests for encryption service security features."""

    def test_encryption_service_encrypt_decrypt_round_trip(self):
        """Test encryption and decryption round trip."""
        encryption_service = EncryptionService()
        plaintext = "sensitive_oauth_token_12345"

        # Encrypt
        ciphertext = encryption_service.encrypt(plaintext)

        # Verify it's encrypted (not plaintext)
        assert ciphertext != plaintext
        assert len(ciphertext) > len(plaintext)  # Base64 encoding makes it longer

        # Decrypt
        decrypted = encryption_service.decrypt(ciphertext)

        # Should match original
        assert decrypted == plaintext

    def test_encryption_service_encrypt_different_outputs(self):
        """Test that encrypting the same text produces different outputs."""
        encryption_service = EncryptionService()
        plaintext = "same_text"

        # Encrypt same text multiple times
        ciphertext1 = encryption_service.encrypt(plaintext)
        ciphertext2 = encryption_service.encrypt(plaintext)

        # Should produce different ciphertexts (due to random IV)
        assert ciphertext1 != ciphertext2

        # But both should decrypt to same plaintext
        assert encryption_service.decrypt(ciphertext1) == plaintext
        assert encryption_service.decrypt(ciphertext2) == plaintext

    def test_encryption_service_encrypt_none_raises_error(self):
        """Test that encrypting None raises error."""
        encryption_service = EncryptionService()

        with pytest.raises(ValueError, match="Plaintext cannot be None"):
            encryption_service.encrypt(None)

    def test_encryption_service_decrypt_none_raises_error(self):
        """Test that decrypting None raises error."""
        encryption_service = EncryptionService()

        with pytest.raises(ValueError, match="Ciphertext cannot be None"):
            encryption_service.decrypt(None)

    def test_encryption_service_encrypt_non_string_raises_error(self):
        """Test that encrypting non-string raises error."""
        encryption_service = EncryptionService()

        with pytest.raises(ValueError, match="Plaintext must be a string"):
            encryption_service.encrypt(12345)

    def test_encryption_service_decrypt_non_string_raises_error(self):
        """Test that decrypting non-string raises error."""
        encryption_service = EncryptionService()

        with pytest.raises(ValueError, match="Ciphertext must be a string"):
            encryption_service.decrypt(12345)

    def test_encryption_service_decrypt_invalid_ciphertext(self):
        """Test that decrypting invalid ciphertext raises error."""
        encryption_service = EncryptionService()

        with pytest.raises(ValueError, match="Decryption failed"):
            encryption_service.decrypt("invalid_ciphertext")

    def test_encryption_service_decrypt_malformed_base64(self):
        """Test that decrypting malformed base64 raises error."""
        encryption_service = EncryptionService()

        with pytest.raises(ValueError, match="Decryption failed"):
            encryption_service.decrypt("not_base64!@#")

    def test_encryption_service_empty_string(self):
        """Test encryption and decryption of empty string."""
        encryption_service = EncryptionService()
        plaintext = ""

        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryption_service_unicode_text(self):
        """Test encryption and decryption of unicode text."""
        encryption_service = EncryptionService()
        plaintext = "Hello 世界 🌍 émojis"

        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryption_service_long_text(self):
        """Test encryption and decryption of long text."""
        encryption_service = EncryptionService()
        plaintext = "A" * 10000  # 10KB of text

        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryption_service_with_custom_key(self):
        """Test encryption service with custom key."""
        from cryptography.fernet import Fernet

        custom_key = Fernet.generate_key().decode()
        encryption_service = EncryptionService(custom_key)

        plaintext = "test_with_custom_key"
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryption_service_with_invalid_key(self):
        """Test encryption service with invalid key raises error."""
        with pytest.raises(ValueError, match="Invalid encryption key"):
            EncryptionService("invalid_key")

    def test_encryption_service_generate_key(self):
        """Test key generation utility method."""
        key = EncryptionService.generate_key()

        # Should be a valid base64-encoded key
        assert isinstance(key, str)
        assert len(key) > 0

        # Should be usable to create encryption service
        encryption_service = EncryptionService(key)

        # Should work for encryption/decryption
        plaintext = "test_generated_key"
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryption_service_different_keys_incompatible(self):
        """Test that different keys produce incompatible ciphertexts."""
        key1 = EncryptionService.generate_key()
        key2 = EncryptionService.generate_key()

        service1 = EncryptionService(key1)
        service2 = EncryptionService(key2)

        plaintext = "test_different_keys"
        ciphertext = service1.encrypt(plaintext)

        # Service2 should not be able to decrypt service1's ciphertext
        with pytest.raises(ValueError, match="Decryption failed"):
            service2.decrypt(ciphertext)
