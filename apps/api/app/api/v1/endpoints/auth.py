"""Authentication Endpoints — register, login, refresh, reset, me."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_current_user,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User

router = APIRouter()

# Legacy placeholder hashes (non-bcrypt) that can be upgraded to a real
# password on first register — used by the auto-created / seeded admin user.
_LEGACY_PLACEHOLDER_HASHES = {
    "auto-created-placeholder",
    "seed-placeholder-not-for-production",
}


class RegisterRequest(BaseModel):
    """User registration payload."""

    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    """User login payload."""

    email: str
    password: str


class UserResponse(BaseModel):
    """Safe user representation (never exposes hashed_password)."""

    id: str
    email: str
    full_name: str | None = None
    role: str = "user"
    created_at: str | None = None


class AuthResponse(BaseModel):
    """JWT + user payload returned on register/login/refresh."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    """Refresh token rotation payload."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Server-side logout payload (revokes the refresh token)."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Password change payload."""

    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


async def _issue_tokens(
    db: AsyncSession, user: User, rotate: RefreshToken | None = None
) -> AuthResponse:
    """Issue a fresh access + refresh token pair.

    When ``rotate`` is provided (an old refresh token being used), it is
    revoked so the old token can't be replayed.
    """
    if rotate is not None:
        rotate.revoked_at = datetime.utcnow()
    raw = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()
    return AuthResponse(
        access_token=create_access_token(
            user.id, token_version=user.token_version or 0
        ),
        refresh_token=raw,
        user=_user_response(user),
    )


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role or "user",
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(
    data: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new user account and return a JWT.

    If the email matches the legacy auto-created placeholder user (which had
    a non-bcrypt placeholder password), upgrade it with the real password so
    existing projects/devices stay attached to the same account.
    """
    email = data.email.lower().strip()
    existing = await db.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()
    if user:
        if user.hashed_password not in _LEGACY_PLACEHOLDER_HASHES:
            raise HTTPException(
                status_code=409, detail="Email already registered"
            )
        # Upgrade legacy placeholder user with a real password. The seeded
        # admin account becomes role=admin (RBAC for Settings/Observability).
        user.hashed_password = hash_password(data.password)
        if data.full_name and not user.full_name:
            user.full_name = data.full_name
        if email == "admin@agentforge.ai" and user.role != "admin":
            user.role = "admin"
        await db.commit()
        await db.refresh(user)
        return await _issue_tokens(db, user)

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _issue_tokens(db, user)


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """Authenticate a user and return a JWT."""
    email = data.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=401, detail="Invalid email or password"
        )
    return await _issue_tokens(db, user)


@router.post("/auth/refresh", response_model=AuthResponse)
async def refresh(
    data: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """Rotate a refresh token: revoke it and issue a fresh pair.

    Old tokens are single-use — after a successful refresh the previous
    refresh token is permanently revoked.
    """
    token_hash = hash_refresh_token(data.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if stored.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user_result = await db.execute(
        select(User).where(User.id == stored.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")

    return await _issue_tokens(db, user, rotate=stored)


@router.post("/auth/logout")
async def logout(
    data: LogoutRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """Revoke a refresh token server-side (real logout)."""
    token_hash = hash_refresh_token(data.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.utcnow()
        await db.commit()
    return {"ok": True, "detail": "Signed out"}


# ── Password reset (dev-mode; no SMTP — token returned in the response) ────
import secrets as _secrets
import time as _time
import uuid as _uuid

_RESET_TTL_SECONDS = 1800  # 30 minutes
_reset_tokens: dict[str, dict] = {}


class ForgotPasswordRequest(BaseModel):
    """Request a password-reset token."""

    email: str


class ResetPasswordRequest(BaseModel):
    """Reset a password with a token."""

    token: str
    new_password: str = Field(min_length=6, max_length=128)


@router.post("/auth/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """Issue a short-lived password-reset token.

    No SMTP is configured, so the token is returned directly in the response
    (dev-mode). In production this would email the user instead.
    """
    email = data.email.lower().strip()
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        # Never reveal whether an email is registered
        return {"ok": True, "detail": "If that email exists, a reset link was sent."}
    token = _secrets.token_urlsafe(32)
    _reset_tokens[token] = {
        "email": email,
        "expires_at": _time.time() + _RESET_TTL_SECONDS,
    }
    return {
        "ok": True,
        "detail": "Password reset token generated (dev-mode: returned below).",
        "reset_token": token,
        "expires_in_seconds": _RESET_TTL_SECONDS,
    }


@router.post("/auth/reset-password")
async def reset_password(
    data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """Validate a reset token and set a new password.

    Also bumps ``token_version`` (revoking all JWTs) and revokes every
    outstanding refresh token for the user.
    """
    record = _reset_tokens.pop(data.token.strip(), None)
    if not record or record["expires_at"] < _time.time():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user_result = await db.execute(
        select(User).where(User.email == record["email"])
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User no longer exists")

    user.hashed_password = hash_password(data.new_password)
    user.token_version = (user.token_version or 0) + 1
    # Revoke all outstanding refresh tokens for this user
    revoke_result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    )
    for rt in revoke_result.scalars().all():
        rt.revoked_at = datetime.utcnow()
    await db.commit()
    return {"ok": True, "detail": "Password reset. You can now sign in."}


@router.post("/auth/change-password", response_model=AuthResponse)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Change the current user's password.

    Bumps ``token_version`` so every previously issued JWT is revoked
    immediately; a fresh token is returned for the new password.
    """
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400, detail="Current password is incorrect"
        )
    current_user.hashed_password = hash_password(data.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.commit()
    await db.refresh(current_user)
    return await _issue_tokens(db, current_user)


@router.get("/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> Any:
    """Return the currently authenticated user."""
    return _user_response(current_user)
