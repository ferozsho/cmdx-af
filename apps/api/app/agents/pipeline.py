"""Multi-Agent Orchestration Pipeline."""

import time
from typing import Any, Dict, List
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
