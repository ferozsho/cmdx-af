"""User Management API Endpoints (admin-only)."""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User

router = APIRouter()

# The admin account is protected from modification/deletion.
PROTECTED_ADMIN_EMAIL = "admin@agentforge.ai"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    created_at: str | None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None


def _to_user_response(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role or "user",
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
