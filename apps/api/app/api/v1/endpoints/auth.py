"""Authentication Endpoints — register, login, current user."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
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
    created_at: str | None = None


class AuthResponse(BaseModel):
    """JWT + user payload returned on register/login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
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
        # Upgrade legacy placeholder user with a real password
        user.hashed_password = hash_password(data.password)
        if data.full_name and not user.full_name:
            user.full_name = data.full_name
        await db.commit()
        await db.refresh(user)
        return AuthResponse(
            access_token=create_access_token(user.id),
            user=_user_response(user),
        )

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AuthResponse(
        access_token=create_access_token(user.id), user=_user_response(user)
    )


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
    return AuthResponse(
        access_token=create_access_token(user.id), user=_user_response(user)
    )


@router.get("/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> Any:
    """Return the currently authenticated user."""
    return _user_response(current_user)
