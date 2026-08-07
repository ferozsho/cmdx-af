"""Agent Template Repository — CRUD + versioning + per-project config."""

from __future__ import annotations

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_template import AgentTemplate, AgentVersion, ProjectAgent


class AgentTemplateRepository:
    """Database operations for AgentTemplate, AgentVersion, and ProjectAgent."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Template CRUD ──────────────────────────────────────────────────

    async def list_all(self) -> List[AgentTemplate]:
        """List all agent templates ordered by name."""
        result = await self.db.execute(
            select(AgentTemplate).order_by(AgentTemplate.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, template_id: str) -> Optional[AgentTemplate]:
        """Get a single template by ID."""
        result = await self.db.execute(
            select(AgentTemplate).where(AgentTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        description: str | None = None,
        capability: str = "reasoning",
        system_prompt: str | None = None,
        tools: list | None = None,
    ) -> AgentTemplate:
        """Create a new agent template (version 1)."""
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            capability=capability,
            system_prompt=system_prompt,
            tools=tools or [],
            version=1,
        )
        self.db.add(template)
        await self.db.flush()
        await self._snapshot_version(template)
        return template

    async def update(
        self,
        template_id: str,
        name: str | None = None,
        description: str | None = None,
        capability: str | None = None,
        system_prompt: str | None = None,
        tools: list | None = None,
    ) -> AgentTemplate | None:
        """Update template and bump version."""
        template = await self.get_by_id(template_id)
        if not template:
            return None

        changed = False
        if name is not None and name != template.name:
            template.name = name
            changed = True
        if description is not None and description != template.description:
            template.description = description
            changed = True
        if capability is not None and capability != template.capability:
            template.capability = capability
            changed = True
        if system_prompt is not None and system_prompt != template.system_prompt:
            template.system_prompt = system_prompt
            changed = True
        if tools is not None and tools != template.tools:
            template.tools = tools
            changed = True

        if changed:
            template.version += 1
            await self.db.flush()
            await self._snapshot_version(template)

        return template

    async def delete(self, template_id: str) -> bool:
        """Delete a template and all its versions/project configs."""
        template = await self.get_by_id(template_id)
        if not template:
            return False
        await self.db.delete(template)
        await self.db.flush()
        return True

    # ── Versioning ─────────────────────────────────────────────────────

    async def _snapshot_version(self, template: AgentTemplate) -> None:
        """Create an immutable version snapshot."""
        snapshot_data = {
            "name": template.name,
            "description": template.description,
            "capability": template.capability,
            "system_prompt": template.system_prompt,
            "tools": template.tools,
        }
        version = AgentVersion(
            id=str(uuid.uuid4()),
            template_id=template.id,
            version=template.version,
            snapshot=snapshot_data,
        )
        self.db.add(version)
        await self.db.flush()

    async def list_versions(self, template_id: str) -> List[AgentVersion]:
        """List all versions for a template, newest first."""
        result = await self.db.execute(
            select(AgentVersion)
            .where(AgentVersion.template_id == template_id)
            .order_by(AgentVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_version(
        self, template_id: str, version: int
    ) -> Optional[AgentVersion]:
        """Get a specific version snapshot."""
        result = await self.db.execute(
            select(AgentVersion).where(
                AgentVersion.template_id == template_id,
                AgentVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    # ── Per-Project Agent Config ───────────────────────────────────────

    async def list_project_agents(self, project_id: str) -> List[ProjectAgent]:
        """List agent configs for a project, ordered by sort_order."""
        result = await self.db.execute(
            select(ProjectAgent)
            .where(ProjectAgent.project_id == project_id)
            .order_by(ProjectAgent.sort_order)
        )
        return list(result.scalars().all())

    async def get_project_agent(
        self, project_id: str, template_id: str
    ) -> Optional[ProjectAgent]:
        """Get a specific project-agent config."""
        result = await self.db.execute(
            select(ProjectAgent).where(
                ProjectAgent.project_id == project_id,
                ProjectAgent.template_id == template_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_project_agent(
        self,
        project_id: str,
        template_id: str,
        enabled: bool = True,
        sort_order: int = 0,
        custom_config: dict | None = None,
    ) -> ProjectAgent:
        """Create or update a project-agent config."""
        existing = await self.get_project_agent(project_id, template_id)
        if existing:
            existing.enabled = enabled
            existing.sort_order = sort_order
            if custom_config is not None:
                existing.custom_config = custom_config
            await self.db.flush()
            return existing

        pa = ProjectAgent(
            id=str(uuid.uuid4()),
            project_id=project_id,
            template_id=template_id,
            enabled=enabled,
            sort_order=sort_order,
            custom_config=custom_config,
        )
        self.db.add(pa)
        await self.db.flush()
        return pa

    async def remove_project_agent(
        self, project_id: str, template_id: str
    ) -> bool:
        """Remove an agent from a project."""
        existing = await self.get_project_agent(project_id, template_id)
        if not existing:
            return False
        await self.db.delete(existing)
        await self.db.flush()
        return True
