"""Shared helpers for API integration tests."""

from app.core.database import AsyncSessionLocal
from app.core.time import naive_utcnow
from app.models.project import Project


async def seed_rag_indexed(project_id: str) -> None:
    """Mark a test project as RAG-indexed so the access gate is open.

    New projects start gated (``rag_indexed_at`` NULL) until their first RAG
    index completes. Tests that are not exercising the gate call this right
    after project creation to skip the indexing requirement.
    """
    async with AsyncSessionLocal() as db:
        project = await db.get(Project, project_id)
        if project and project.rag_indexed_at is None:
            project.rag_indexed_at = naive_utcnow()
            await db.commit()
