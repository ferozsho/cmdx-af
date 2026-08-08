"""Authentication & authorization helpers (password hashing, JWT, deps)."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# ── Password hashing ────────────────────────────────────────────────────────
# NOTE: passlib 1.7.4 is incompatible with bcrypt>=5 (ValueError on verify),
# so we call the bcrypt library directly.


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"), hashed.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


# ── Refresh tokens ─────────────────────────────────────────────────────────


def generate_refresh_token() -> str:
    """Generate a cryptographically random refresh token (opaque)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage (SHA-256)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    """UTC expiry for a new refresh token (from settings). Naive UTC to
    match the codebase's DateTime columns."""
    return datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )


# ── JWT ─────────────────────────────────────────────────────────────────────
ALGORITHM = "HS256"

_bearer = HTTPBearer(auto_error=False)


def create_access_token(
    user_id: str,
    token_version: int = 0,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create a signed JWT access token for a user.

    ``token_version`` is embedded so a password change (which bumps
    ``users.token_version``) instantly revokes previously issued tokens.
    """
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[tuple]:
    """Decode a JWT and return ``(user_id, token_version)`` or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub"), int(payload.get("ver", 0))
    except (JWTError, TypeError, ValueError):
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency resolving the authenticated user from the Bearer token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    decoded = decode_access_token(credentials.credentials)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id, token_version = decoded
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked — please sign in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency requiring an admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
