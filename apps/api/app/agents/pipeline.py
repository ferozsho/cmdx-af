"""Multi-Agent Orchestration Pipeline."""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.agents.registry import AGENT_REGISTRY, DEFAULT_AGENT_ORDER
from app.core.database import AsyncSessionLocal
from app.llm.router import LLMConfigurationError
from app.llm.tracking import current_instruction_id, current_project_id
from app.models.agent_run import AgentRun
from app.models.artifact import Artifact
from app.models.instruction import Instruction
from app.repositories.agent_template_repo import AgentTemplateRepository
from app.repositories.project_repo import ProjectRepository
from app.services.approvals import ApprovalRequiredError

logger = logging.getLogger(__name__)


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
            "verification_status": res.get("verification_status", "UNVERIFIED"),
            "tool_checks": res.get("tool_checks", []),
            "diagnostics": res.get("diagnostics", []),
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


async def _emit_event(
    event_callback: Any,
    agent_name: str,
    status: str,
    message: str,
    data: dict | None = None,
) -> None:
    """Emit progress without allowing a disconnected client to stop a job."""
    if not event_callback:
        return
    try:
        await event_callback(agent_name, status, message, data=data)
    except Exception:
        logger.exception(
            "Unable to emit pipeline event: agent=%s status=%s",
            agent_name,
            status,
        )


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
                indexed_templates = list(enumerate(templates))
                indexed_templates.sort(
                    key=lambda item: (
                        pa_map[item[1].id].sort_order
                        if item[1].id in pa_map
                        else len(templates) + item[0]
                    )
                )
                agents: list = []
                for _, t in indexed_templates:
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
        except LLMConfigurationError:
            logger.exception(
                "LLM configuration prevents execution for project=%s",
                self.project_id,
            )
            raise
        except Exception:
            logger.exception(
                "_load_agents failed for project=%s; execution is disabled",
                self.project_id,
            )
            return []

    def _default_agents(self) -> list:
        """Return the hardcoded default agent list (backward compat)."""
        return [AGENT_REGISTRY[name]() for name in DEFAULT_AGENT_ORDER]

    async def run_pipeline(
        self,
        instruction_id: str,
        prompt: str,
        event_callback: Any = None,
        device_id: str = "",
        workspace_id: str = "ws-test",
        image_bytes: str | None = None,
        image_mime_type: str | None = None,
        previous_context: list[dict] | None = None,
        session_model_name: str | None = None,
        session_context_limit: int | None = None,
        cancel_check: Any = None,
        user_id: str | None = None,
    ) -> Dict[str, Any]:
        """Execute all sequential agents in order, emitting live progress events."""
        # Bind instruction_id and project_id so LLM usage tracking persists
        # the right FKs in the background task.
        current_instruction_id.set(instruction_id)
        current_project_id.set(self.project_id)

        # Load per-project agent config (or defaults)
        agents = await self._load_agents()

        # Load project config for policy enforcement
        project_config = None
        project_policy_error: str | None = None
        if self.project_id:
            try:
                async with AsyncSessionLocal() as session:
                    project_repo = ProjectRepository(session)
                    project_config = await project_repo.get_by_id(self.project_id)
                    if project_config is None:
                        project_policy_error = "Project policy could not be loaded."
            except Exception:
                logger.exception(
                    "Unable to load project policy for project=%s",
                    self.project_id,
                )
                project_policy_error = "Project policy could not be loaded."

        context: Dict[str, Any] = {
            "instruction_id": instruction_id,
            "project_id": self.project_id,
            "prompt": prompt,
            "device_id": device_id,
            "workspace_id": workspace_id,
            "project_config": project_config,
            "user_id": user_id or getattr(project_config, "user_id", None),
        }
        # Inject image attachment for Visual Analysis Agent
        if image_bytes:
            context["image_bytes"] = image_bytes
            context["image_mime_type"] = image_mime_type or "image/png"
        # Inject session context (previous instructions in this session)
        if previous_context:
            context["session_context"] = previous_context
            context["session_model_name"] = session_model_name
            context["session_context_limit"] = session_context_limit
        results: List[Dict[str, Any]] = []
        persistence_failed = False
        cancelled = False
        waiting_approval = False
        completed_runs: dict[str, dict[str, Any]] = {}
        try:
            async with AsyncSessionLocal() as session:
                prior_runs = await session.scalars(
                    select(AgentRun)
                    .where(
                        AgentRun.instruction_id == instruction_id,
                        AgentRun.status == "COMPLETED",
                    )
                    .order_by(AgentRun.created_at.asc())
                )
                for prior in prior_runs.all():
                    if isinstance(prior.metadata_json, dict):
                        completed_runs[prior.agent_name] = prior.metadata_json
        except Exception:
            logger.exception(
                "Unable to load completed pipeline checkpoints: %s",
                instruction_id,
            )

        if project_policy_error:
            context["pipeline_error"] = project_policy_error
            agents = []
            await _emit_event(
                event_callback,
                "System",
                "FAILED",
                project_policy_error,
            )

        for agent in agents:
            if agent.agent_name in completed_runs:
                checkpoint = dict(completed_runs[agent.agent_name])
                context.update(checkpoint)
                results.append(checkpoint)
                await _emit_event(
                    event_callback,
                    agent.agent_name,
                    "COMPLETED",
                    f"Resumed from completed {agent.agent_name} checkpoint.",
                    data=checkpoint,
                )
                continue
            if cancel_check and await cancel_check():
                cancelled = True
                context["pipeline_error"] = "Instruction cancelled."
                await _emit_event(
                    event_callback,
                    "System",
                    "CANCELLED",
                    "Instruction cancelled before the next agent step.",
                )
                break
            start_time = time.time()
            await _emit_event(
                event_callback,
                agent.agent_name,
                "STARTED",
                f"Running {agent.agent_name}...",
            )

            try:
                res = await agent.execute(context)
            except ApprovalRequiredError as exc:
                waiting_approval = True
                context["pipeline_error"] = exc.summary
                res = {
                    "status": "WAITING_APPROVAL",
                    "approval_id": exc.approval_id,
                    "error": exc.summary,
                }
            except Exception as exc:
                logger.exception(
                    "Agent execution failed: instruction=%s agent=%s",
                    instruction_id,
                    agent.agent_name,
                )
                res = {"status": "FAILED", "error": str(exc)}
            duration = round(time.time() - start_time, 2)
            step_status = str(res.get("status", "COMPLETED")).upper()
            res["status"] = step_status
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
                            output=json.dumps(res, default=str)[:100000],
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
                persistence_failed = True
                logger.exception(
                    "Unable to persist agent result: instruction=%s agent=%s",
                    instruction_id,
                    agent.agent_name,
                )

            await _emit_event(
                event_callback,
                agent.agent_name,
                step_status,
                (
                    f"{agent.agent_name} failed after {duration}s."
                    if step_status == "FAILED"
                    else f"{agent.agent_name} finished in {duration}s."
                ),
                data=res,
            )

            if step_status in {"FAILED", "WAITING_APPROVAL"}:
                break

        # Mark the instruction as COMPLETED/FAILED based on agent results
        any_failed = any(r.get("status") == "FAILED" for r in results)
        final_status = (
            "CANCELLED"
            if cancelled
            else (
                "WAITING_APPROVAL"
                if waiting_approval
                else (
                    "FAILED"
                    if any_failed or not results or persistence_failed
                    else "COMPLETED"
                )
            )
        )
        try:
            async with AsyncSessionLocal() as session:
                instruction = await session.get(Instruction, instruction_id)
                if instruction:
                    instruction.status = final_status
                    await session.commit()
        except Exception:
            final_status = "FAILED"
            logger.exception(
                "Unable to persist final pipeline state: instruction=%s status=%s",
                instruction_id,
                final_status,
            )

        return {
            "instruction_id": instruction_id,
            "status": final_status,
            "agent_runs": results,
            "final_context": context,
        }
