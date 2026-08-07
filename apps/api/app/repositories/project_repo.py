"""Project database repository."""

from __future__ import annotations

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import User


class ProjectRepository:
    """Database operations for Project model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_default_user_id(self) -> str:
        """Resolve the default user ID (first user in DB)."""
        result = await self.db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            return user.id
        # Create fallback user if none exists
        user = User(
            id=str(uuid.uuid4()),
            email="admin@agentforge.ai",
            hashed_password="auto-created-placeholder",
            full_name="Auto User",
        )
        self.db.add(user)
        await self.db.flush()
        return user.id

    async def list_all(self) -> List[Project]:
        """Return all projects ordered by creation date descending."""
        result = await self.db.execute(
            select(Project).order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, project_id: str) -> Optional[Project]:
        """Get a single project by its primary key."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        description: str | None = None,
        execution_target: str = "LOCAL",
        tech_stack: dict | None = None,
        user_id: str = "",
    ) -> Project:
        """Create and persist a new project."""
        if not user_id:
            user_id = await self._get_default_user_id()
        project = Project(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            execution_target=execution_target,
            tech_stack=tech_stack or {},
        )
        self.db.add(project)
        await self.db.flush()
        return project

    async def count(self) -> int:
        """Return total number of projects."""
        result = await self.db.execute(select(Project))
        return len(list(result.scalars().all()))

    async def delete(self, project_id: str) -> bool:
        """Delete a project by ID. Returns True if deleted."""
        project = await self.get_by_id(project_id)
        if project:
            await self.db.delete(project)
            await self.db.flush()
            return True
        return False
