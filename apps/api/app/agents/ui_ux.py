"""UI/UX Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a UI/UX Design expert. Analyze requirements and produce
detailed UI design specifications. Return JSON with:
- "page": page name
- "components": list of UI components needed
- "layout": layout description
- "responsive_rules": responsive design rules
- "accessibility_notes": accessibility considerations"""


class UIUXAgent(BaseAgent):
    """UI/UX Agent producing UI design specifications."""

    def __init__(self) -> None:
        super().__init__("UI/UX Agent", capability="reasoning")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Produce UI specification using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Produce a detailed UI/UX specification for the required feature. "
                    "Consider layout, components, responsive behavior, and accessibility."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "ui_spec": {
                    "page": response.content.get("page", "Feature Page"),
                    "components": response.content.get("components", []),
                    "layout": response.content.get("layout", ""),
                    "responsive_rules": response.content.get("responsive_rules", []),
                    "accessibility_notes": (
                        response.content.get("accessibility_notes", "")
                    ),
                },
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "ui_spec": {"page": "", "components": []},
            }
