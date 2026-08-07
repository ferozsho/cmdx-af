"""Documentation Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Technical Documentation expert. Generate documentation
that follows the project's existing documentation style and conventions.
Return JSON with:
- "docs_updated": list of documentation files updated/created
- "sections_added": list of sections added
- "summary": brief description of documentation changes"""


class DocumentationAgent(BaseAgent):
    """Documentation Agent updating project docs."""

    def __init__(self) -> None:
        super().__init__("Documentation Agent", capability="documentation")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update documentation files using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        backend_files = context.get("files_generated", [])
        frontend_files = context.get("components", [])
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    f"Backend files generated: {backend_files}\n"
                    f"Frontend files generated: {frontend_files}\n\n"
                    "Generate documentation updates (README.md, API docs, etc.) "
                    "covering the implemented changes."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "docs_updated": response.content.get("docs_updated", []),
                "sections_added": response.content.get("sections_added", []),
                "summary": response.content.get("summary", ""),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "docs_updated": [],
            }
