"""Multi-Agent Orchestration Pipeline."""

import json
import time
from typing import Any, Dict, List, Optional

from app.agents.planning import PlanningAgent
from app.agents.architecture import ArchitectureAgent
from app.agents.visual_analysis import VisualAnalysisAgent
from app.agents.ui_ux import UIUXAgent
from app.agents.frontend import FrontendAgent
from app.agents.backend import BackendAgent
from app.agents.database import DatabaseAgent
from app.agents.documentation import DocumentationAgent
from app.agents.test_agent import TestAgent
from app.agents.validation import ValidationAgent
from app.agents.git_agent import GitAgent
from app.core.database import AsyncSessionLocal
from app.models.agent_run import AgentRun
from app.models.artifact import Artifact


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
    """Sequential Multi-Agent Development Pipeline Orchestrator."""

    def __init__(self) -> None:
        self.agents = [
            PlanningAgent(),
            ArchitectureAgent(),
            VisualAnalysisAgent(),
            UIUXAgent(),
            DocumentationAgent(),
            FrontendAgent(),
            BackendAgent(),
            DatabaseAgent(),
            TestAgent(),
            ValidationAgent(),
            GitAgent(),
        ]

    async def run_pipeline(
        self,
        instruction_id: str,
        prompt: str,
        event_callback: Any = None,
        device_id: str = "dev_feroz_pc",
        workspace_id: str = "ws-test",
    ) -> Dict[str, Any]:
        """Execute all sequential agents in order, emitting live progress events."""
        context: Dict[str, Any] = {
            "instruction_id": instruction_id,
            "prompt": prompt,
            "device_id": device_id,
            "workspace_id": workspace_id,
        }
        results: List[Dict[str, Any]] = []

        for agent in self.agents:
            start_time = time.time()
            if event_callback:
                await event_callback(agent.agent_name, "STARTED", f"Running {agent.agent_name}...")

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

        return {
            "instruction_id": instruction_id,
            "status": "COMPLETED",
            "agent_runs": results,
            "final_context": context,
        }
