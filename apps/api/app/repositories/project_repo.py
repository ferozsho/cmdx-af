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

    async def list_for_user(self, user_id: str) -> List[Project]:
        """Return projects belonging to a user, newest first."""
        result = await self.db.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def belongs_to(self, project_id: str, user_id: str) -> bool:
        """True when a project exists and belongs to the given user."""
        result = await self.db.execute(
            select(Project.id).where(
                Project.id == project_id, Project.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None

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
        local_path: str | None = None,
        tech_stack: dict | None = None,
        user_id: str = "",
        git_enabled: bool = True,
        git_branch_patterns: list | None = None,
        git_require_pr: bool = False,
        git_commit_template: str | None = None,
        fs_read_enabled: bool = True,
        fs_write_enabled: bool = True,
        fs_delete_enabled: bool = True,
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
            local_path=local_path,
            tech_stack=tech_stack or {},
            git_enabled=git_enabled,
            git_branch_patterns=git_branch_patterns or ["*"],
            git_require_pr=git_require_pr,
            git_commit_template=git_commit_template,
            fs_read_enabled=fs_read_enabled,
            fs_write_enabled=fs_write_enabled,
            fs_delete_enabled=fs_delete_enabled,
        )
        self.db.add(project)
        await self.db.flush()
        return project

    async def count(self) -> int:
        """Return total number of projects."""
        result = await self.db.execute(select(Project))
        return len(list(result.scalars().all()))

    async def count_for_user(self, user_id: str) -> int:
        """Return total number of projects for a user."""
        result = await self.db.execute(
            select(Project).where(Project.user_id == user_id)
        )
        return len(list(result.scalars().all()))

    async def delete(self, project_id: str) -> bool:
        """Delete a project by ID. Returns True if deleted."""
        project = await self.get_by_id(project_id)
        if project:
            await self.db.delete(project)
            await self.db.flush()
            return True
        return False

    async def update(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        execution_target: str | None = None,
        local_path: str | None = None,
        tech_stack: dict | None = None,
        git_enabled: bool | None = None,
        git_branch_patterns: list | None = None,
        git_require_pr: bool | None = None,
        git_commit_template: str | None = None,
        fs_read_enabled: bool | None = None,
        fs_write_enabled: bool | None = None,
        fs_delete_enabled: bool | None = None,
    ) -> Project | None:
        """Update an existing project. Returns updated project or None if not found."""
        project = await self.get_by_id(project_id)
        if not project:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if execution_target is not None:
            project.execution_target = execution_target
        if local_path is not None:
            project.local_path = local_path
        if tech_stack is not None:
            project.tech_stack = tech_stack
        if git_enabled is not None:
            project.git_enabled = git_enabled
        if git_branch_patterns is not None:
            project.git_branch_patterns = git_branch_patterns
        if git_require_pr is not None:
            project.git_require_pr = git_require_pr
        if git_commit_template is not None:
            project.git_commit_template = git_commit_template
        if fs_read_enabled is not None:
            project.fs_read_enabled = fs_read_enabled
        if fs_write_enabled is not None:
            project.fs_write_enabled = fs_write_enabled
        if fs_delete_enabled is not None:
            project.fs_delete_enabled = fs_delete_enabled
        await self.db.flush()
        return project
