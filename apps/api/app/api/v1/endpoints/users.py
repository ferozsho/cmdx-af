"""User Management API Endpoints (admin-only)."""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, hash_password
from app.models.user import User

router = APIRouter()

# The admin account is protected from modification/deletion.
PROTECTED_ADMIN_EMAIL = "admin@agentforge.ai"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    org_name: str | None = None
    job_title: str | None = None
    agent_quota: int = 10
    created_at: str | None


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    role: str = "user"
    org_name: str | None = None
    job_title: str | None = None
    agent_quota: int = 10

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    org_name: str | None = None
    job_title: str | None = None
    agent_quota: int | None = None


def _to_user_response(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role or "user",
        org_name=u.org_name,
        job_title=u.job_title,
        agent_quota=u.agent_quota or 10,
        created_at=u.created_at.isoformat() if u.created_at else None,
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> Any:
    """List all users (admin only)."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [_to_user_response(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> Any:
    """Create a new user (admin only)."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        org_name=data.org_name,
        job_title=data.job_title,
        agent_quota=data.agent_quota,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _to_user_response(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> Any:
    """Get a single user by ID (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_user_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> Any:
    """Update a user's profile (admin only). The primary admin account is protected."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == PROTECTED_ADMIN_EMAIL:
        raise HTTPException(
            status_code=403,
            detail="The primary admin account cannot be modified.",
        )
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    if data.org_name is not None:
        user.org_name = data.org_name
    if data.job_title is not None:
        user.job_title = data.job_title
    if data.agent_quota is not None:
        user.agent_quota = data.agent_quota
    await db.commit()
    await db.refresh(user)
    return _to_user_response(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> Any:
    """Delete a user (admin only). The primary admin account is protected."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == PROTECTED_ADMIN_EMAIL:
        raise HTTPException(
            status_code=403,
            detail="The primary admin account cannot be deleted.",
        )
    await db.delete(user)
    await db.commit()
    return {"ok": True, "detail": f"User {user.email} deleted"}
