"""Backend Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Backend Engineer agent specializing in FastAPI, Python,
and service-layer architecture. Analyze the project context and generate backend code
that follows existing patterns. Return your response as JSON with:
- "files_generated": list of file paths you would create/modify
- "summary": brief description of what was implemented
- "key_decisions": list of architectural decisions made"""


class BackendAgent(BaseAgent):
    """Backend Agent generating FastAPI routes, services, and schemas."""

    def __init__(self) -> None:
        super().__init__("Backend Agent", capability="coding")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate backend code files using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Generate the required backend Python code (FastAPI routes, "
                    "services, schemas) following project conventions."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "files_generated": response.content.get("files_generated", []),
                "summary": response.content.get("summary", ""),
                "key_decisions": response.content.get("key_decisions", []),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "files_generated": [],
            }
