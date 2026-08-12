"""Encryption helpers for platform secrets stored at rest.

Secrets (LLM API keys) are encrypted with Fernet (AES-128-CBC + HMAC) before
being written to the ``platform_settings`` table. The Fernet key is derived
deterministically from the existing ``SECRET_KEY`` env var, so it stays stable
across restarts without requiring a new environment variable.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

# Sentinel used by the Settings API/frontend to mean "delete this key".
REMOVE_KEY_SENTINEL = "__remove__"
# Display mask never stored; used by the frontend to indicate a configured key.
MASKED_VALUE = "••••••••••••••••"


def _fernet() -> Fernet:
    """Build a Fernet cipher keyed off the app SECRET_KEY."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext secret for storage at rest."""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a stored secret; returns "" if the token is unusable."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""
