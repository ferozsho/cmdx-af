"""Frontend Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Frontend Engineer agent specializing in React, Next.js 16,
and TypeScript. Generate frontend code that follows project design patterns.
Return JSON with:
- "files_generated": list of file paths you would create/modify
- "components": list of component names created
- "summary": brief description of what was implemented"""


class FrontendAgent(BaseAgent):
    """Frontend Agent generating React/Next.js components and pages."""

    def __init__(self) -> None:
        super().__init__("Frontend Agent", capability="coding")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate frontend code files using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Generate the required frontend code (React/Next.js components, "
                    "pages, hooks) following project conventions and design patterns."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "files_generated": response.content.get("files_generated", []),
                "components": response.content.get("components", []),
                "summary": response.content.get("summary", ""),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "files_generated": [],
            }
