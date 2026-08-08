"""Planning Agent Implementation."""

import json
from typing import Any, Dict
from app.agents.base import BaseAgent

DEFAULT_SYSTEM_PROMPT = (
    "You are a Senior Software Architect. Analyze the natural language instruction "
    "and output a structured JSON plan with complexity, modules_to_create, "
    "files_to_create, files_to_update, testing_strategy, and risks."
)


class PlanningAgent(BaseAgent):
    """Planning Agent responsible for analyzing instructions and proposing steps."""

    def __init__(
        self,
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        super().__init__(
            "Planning Agent",
            capability="reasoning",
            system_prompt_override=system_prompt_override,
            tools_override=tools_override,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze prompt and produce structured JSON plan."""
        prompt = context.get("prompt", "")

        response = await self.provider.generate(
            prompt=f"Create implementation plan for instruction: {prompt}",
            system_prompt=self.get_system_prompt(DEFAULT_SYSTEM_PROMPT),
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
