"""Architecture Agent Implementation."""

from typing import Any, Dict

from app.agents.base import BaseAgent

SYSTEM_PROMPT = """You are a Software Architecture expert. Analyze the project context
and verify architectural consistency. Return JSON with:
- "architectural_decisions": list of verified decisions and patterns
- "boundaries_preserved": list of service boundaries that were respected
- "concerns": list of any architectural concerns or violations
- "recommendations": list of actionable recommendations"""


class ArchitectureAgent(BaseAgent):
    """Architecture Agent enforcing design patterns and service boundaries."""

    def __init__(
        self,
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        super().__init__(
            "Architecture Agent",
            capability="reasoning",
            system_prompt_override=system_prompt_override,
            tools_override=tools_override,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Verify architectural consistency using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Analyze the architectural implications of this implementation. "
                    "Check design patterns, service boundaries, and system cohesion."
                ),
                system_prompt=self.get_system_prompt(SYSTEM_PROMPT),
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "architectural_decisions": (
                    response.content.get("architectural_decisions", [])
                ),
                "boundaries_preserved": (
                    response.content.get("boundaries_preserved", [])
                ),
                "concerns": response.content.get("concerns", []),
                "recommendations": response.content.get("recommendations", []),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "architectural_decisions": [],
            }
