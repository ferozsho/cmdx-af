"""Multi-Agent Orchestration Pipeline."""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.agents.registry import AGENT_REGISTRY, DEFAULT_AGENT_ORDER
from app.core.database import AsyncSessionLocal
from app.llm.tracking import current_instruction_id
from app.models.agent_run import AgentRun

logger = logging.getLogger(__name__)
from app.models.artifact import Artifact
from app.models.instruction import Instruction
from app.repositories.agent_template_repo import AgentTemplateRepository
from app.repositories.project_repo import ProjectRepository


# Maps each artifact-producing agent to its Artifact.artifact_type
_ARTIFACT_TYPES = {
    "Planning Agent": "plan",
    "Architecture Agent": "architecture",
    "Visual Analysis Agent": "visual_spec",
    "UI/UX Agent": "ui_spec",
    "Documentation Agent": "documentation",
    "Test Agent": "test_report",
    "Validation Agent": "validation_report",
}


def _build_artifact(
    agent_name: str, res: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    """Build a persisted artifact payload from an agent result."""
    artifact_type = _ARTIFACT_TYPES.get(agent_name)
    if not artifact_type:
        return None

    if agent_name == "Planning Agent":
        content = res.get("plan")
    elif agent_name == "Architecture Agent":
        content = {
            k: res.get(k)
            for k in (
                "architectural_decisions",
                "concerns",
                "recommendations",
            )
        }
    elif agent_name == "Visual Analysis Agent":
        content = res.get("visual_analysis")
    elif agent_name == "UI/UX Agent":
        content = res.get("ui_spec")
    elif agent_name == "Documentation Agent":
        content = {
            "docs_updated": res.get("docs_updated", []),
            "sections_added": res.get("sections_added", []),
            "summary": res.get("summary", ""),
        }
    elif agent_name == "Test Agent":
        content = {
            "tests_generated": res.get("tests_generated", []),
            "tests_passed": res.get("tests_passed", 0),
            "tests_failed": res.get("tests_failed", 0),
            "coverage_percent": res.get("coverage_percent", 0),
            "test_summary": res.get("test_summary", ""),
        }
    elif agent_name == "Validation Agent":
        content = {
            "lint_issues": res.get("lint_issues", 0),
            "type_errors": res.get("type_errors", 0),
            "security_issues": res.get("security_issues", 0),
            "build_status": res.get("build_status", "PASSED"),
            "recommendations": res.get("recommendations", []),
        }
    else:
        content = None

    if not content:
        return None
    return {
        "title": agent_name,
        "type": artifact_type,
        "content": json.dumps(content, default=str, indent=2),
    }


class PipelineOrchestrator:
    """Sequential Multi-Agent Development Pipeline Orchestrator.

    Loads per-project agent configuration from the project_agents table so
    users can enable/disable agents, reorder them, and override prompts/tools
    per project. Falls back to all 11 default agents when no configuration
    exists (backward compatible).
    """

    def __init__(self, project_id: str | None = None) -> None:
        self.project_id = project_id
        self.agents: list = []  # Populated lazily in _load_agents()

    async def _load_agents(self) -> list:
        """Build the agent instance list from per-project config or defaults.

        Merges project_agent overrides with the full template list so that
        unconfigured agents default to enabled (matching the frontend's
        behavior). When ALL configured agents are disabled, no agents run
        — we never fall back to defaults once a project has any config.
        """
        if not self.project_id:
            return self._default_agents()

        try:
            async with AsyncSessionLocal() as session:
                template_repo = AgentTemplateRepository(session)
                templates = await template_repo.list_all()
                templates = [t for t in templates if t.is_active]

                if not templates:
                    return []

                project_agents = await template_repo.list_project_agents(
                    self.project_id
                )

                # No per-project config at all → use all defaults
                if not project_agents:
                    return self._default_agents()

                # Merge: project_agent overrides win; unconfigured agents
                # default to enabled (consistent with the frontend).
                pa_map = {pa.template_id: pa for pa in project_agents}
                agents: list = []
                for t in templates:
                    pa = pa_map.get(t.id)
                    enabled = pa.enabled if pa else True
                    if not enabled:
                        continue
                    agent_cls = AGENT_REGISTRY.get(t.name)
                    if not agent_cls:
                        continue
                    overrides = (pa.custom_config or {}) if pa else {}
                    agents.append(
                        agent_cls(
                            system_prompt_override=overrides.get("system_prompt"),
                            tools_override=overrides.get("tools"),
                        )
                    )

                # If the project has any config at all, respect it — never
                # fall back to defaults. An empty list means the user disabled
                # every single agent.
                logger.info(
                    "_load_agents: project=%s configured=%d enabled=%d",
                    self.project_id, len(project_agents), len(agents),
                )
                return agents
        except Exception as exc:
            logger.exception(
                "_load_agents failed for project=%s, falling back to defaults",
                self.project_id,
            )

    def _default_agents(self) -> list:
        """Return the hardcoded default agent list (backward compat)."""
        return [AGENT_REGISTRY[name]() for name in DEFAULT_AGENT_ORDER]

    async def run_pipeline(
        self,
        instruction_id: str,
        prompt: str,
        event_callback: Any = None,
        device_id: str = "dev_feroz_pc",
        workspace_id: str = "ws-test",
        image_bytes: str | None = None,
        image_mime_type: str | None = None,
    ) -> Dict[str, Any]:
        """Execute all sequential agents in order, emitting live progress events."""
        # Bind instruction_id so LLM usage tracking persists the right FK
        current_instruction_id.set(instruction_id)

        # Load per-project agent config (or defaults)
        agents = await self._load_agents()

        # Load project config for policy enforcement
        project_config = None
        if self.project_id:
            try:
                async with AsyncSessionLocal() as session:
                    project_repo = ProjectRepository(session)
                    project_config = await project_repo.get_by_id(self.project_id)
            except Exception:
                pass

        context: Dict[str, Any] = {
            "instruction_id": instruction_id,
            "prompt": prompt,
            "device_id": device_id,
            "workspace_id": workspace_id,
            "project_config": project_config,
        }
        # Inject image attachment for Visual Analysis Agent
        if image_bytes:
            context["image_bytes"] = image_bytes
            context["image_mime_type"] = image_mime_type or "image/png"
        results: List[Dict[str, Any]] = []

        for agent in agents:
            start_time = time.time()
            if event_callback:
                await event_callback(
                    agent.agent_name, "STARTED", f"Running {agent.agent_name}..."
                )

            res = await agent.execute(context)
            duration = round(time.time() - start_time, 2)
            res["duration_seconds"] = duration
            res["agent_name"] = agent.agent_name

            context.update(res)
            # Normalize plan key so all downstream agents can find it
            if "plan" in res and "plan_json" not in res:
                context["plan_json"] = res["plan"]
            results.append(res)

            # Persist run + artifact to the database
            try:
                async with AsyncSessionLocal() as session:
                    session.add(
                        AgentRun(
                            instruction_id=instruction_id,
                            agent_name=agent.agent_name,
                            status=str(res.get("status", "COMPLETED")),
                            output=json.dumps(res, default=str)[:10000],
                            metadata_json=res,
                            duration_seconds=duration,
                        )
                    )
                    artifact = _build_artifact(agent.agent_name, res)
                    if artifact:
                        session.add(
                            Artifact(
                                instruction_id=instruction_id,
                                title=artifact["title"],
                                artifact_type=artifact["type"],
                                content=artifact["content"],
                            )
                        )
                    await session.commit()
            except Exception:
                pass

            if event_callback:
                await event_callback(
                    agent.agent_name,
                    "COMPLETED",
                    f"{agent.agent_name} finished in {duration}s.",
                    data=res,
                )

        # Mark the instruction as COMPLETED/FAILED based on agent results
        try:
            any_failed = any(r.get("status") == "FAILED" for r in results)
            async with AsyncSessionLocal() as session:
                instruction = await session.get(Instruction, instruction_id)
                if instruction:
                    instruction.status = "FAILED" if any_failed else "COMPLETED"
                    await session.commit()
        except Exception:
            pass

        return {
            "instruction_id": instruction_id,
            "status": "COMPLETED",
            "agent_runs": results,
            "final_context": context,
        }