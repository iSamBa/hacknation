"""Tests for token encryption utilities."""

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core.encryption import decrypt_token, encrypt_token

# Generate a test encryption key
TEST_KEY = Fernet.generate_key().decode()


class TestEncryption:
    def test_encrypt_then_decrypt_returns_original(self):
        """Encrypting then decrypting should return the original token."""
        with patch("app.core.encryption.settings.TOKEN_ENCRYPTION_KEY", TEST_KEY):
            original = "my-secret-token-12345"
            encrypted = encrypt_token(original)
            decrypted = decrypt_token(encrypted)
            assert decrypted == original

    def test_encrypted_value_is_different(self):
        """Encrypted value should be different from plaintext."""
        with patch("app.core.encryption.settings.TOKEN_ENCRYPTION_KEY", TEST_KEY):
            original = "my-secret-token"
            encrypted = encrypt_token(original)
            assert encrypted != original

    def test_decrypt_with_invalid_token_raises_error(self):
        """Decrypting invalid data should raise InvalidToken."""
        with patch("app.core.encryption.settings.TOKEN_ENCRYPTION_KEY", TEST_KEY):
            with pytest.raises(InvalidToken):
                decrypt_token("not-a-valid-encrypted-string")

    def test_encrypt_empty_string(self):
        """Encrypting an empty string should work."""
        with patch("app.core.encryption.settings.TOKEN_ENCRYPTION_KEY", TEST_KEY):
            original = ""
            encrypted = encrypt_token(original)
            decrypted = decrypt_token(encrypted)
            assert decrypted == original
