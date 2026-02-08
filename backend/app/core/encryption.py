"""Token encryption utilities using Fernet symmetric encryption."""

import logging

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Get Fernet instance from settings encryption key."""
    if not settings.TOKEN_ENCRYPTION_KEY:
        msg = "TOKEN_ENCRYPTION_KEY not configured"
        raise ValueError(msg)
    return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def encrypt_token(plaintext: str) -> str:
    """Encrypt a plaintext token using Fernet symmetric encryption.

    Args:
        plaintext: The token to encrypt.

    Returns:
        Base64-encoded encrypted string.

    Raises:
        ValueError: If TOKEN_ENCRYPTION_KEY is not configured.
    """
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted token back to plaintext.

    Args:
        ciphertext: The encrypted token (base64 string).

    Returns:
        The decrypted plaintext token.

    Raises:
        ValueError: If TOKEN_ENCRYPTION_KEY is not configured.
        InvalidToken: If decryption fails (wrong key or corrupted data).
    """
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
