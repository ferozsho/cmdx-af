"""Artifact database repository."""

from __future__ import annotations

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.instruction import Instruction


class ArtifactRepository:
    """Database operations for Artifact model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_project(self, project_id: str) -> List[Artifact]:
        """Return all artifacts belonging to a project's instructions."""
        result = await self.db.execute(
            select(Artifact)
            .join(Instruction, Instruction.id == Artifact.instruction_id)
            .where(Instruction.project_id == project_id)
            .order_by(Artifact.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        instruction_id: str,
        title: str,
        artifact_type: str,
        content: str,
    ) -> Artifact:
        """Persist a new artifact for an instruction."""
        artifact = Artifact(
            instruction_id=instruction_id,
            title=title,
            artifact_type=artifact_type,
            content=content,
        )
        self.db.add(artifact)
        await self.db.flush()
        return artifact
