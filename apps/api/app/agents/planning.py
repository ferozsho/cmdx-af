"""Planning Agent Implementation."""

import json
from typing import Any, Dict
from app.agents.base import BaseAgent


class PlanningAgent(BaseAgent):
    """Planning Agent responsible for analyzing instructions and proposing steps."""

    def __init__(self) -> None:
        super().__init__("Planning Agent", capability="reasoning")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze prompt and produce structured JSON plan."""
        prompt = context.get("prompt", "")
        system_prompt = (
            "You are a Senior Software Architect. Analyze the natural language instruction "
            "and output a structured JSON plan with complexity, modules_to_create, "
            "files_to_create, files_to_update, testing_strategy, and risks."
        )

        response = await self.provider.generate(
            prompt=f"Create implementation plan for instruction: {prompt}",
            system_prompt=system_prompt,
            json_mode=True,
        )

        try:
            plan = json.loads(response.content)
        except Exception:
            plan = {
                "summary": response.content,
                "complexity": "medium",
                "files_to_create": [],
                "files_to_update": [],
                "testing_strategy": ["pytest"],
                "risks": [],
            }

        return {"status": "COMPLETED", "plan": plan, "llm_usage": response.model_dump()}
