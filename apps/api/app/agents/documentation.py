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

    def __init__(
        self,
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        super().__init__(
            "Documentation Agent",
            capability="documentation",
            system_prompt_override=system_prompt_override,
            tools_override=tools_override,
        )

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
                    "with COMPLETE file content. Return each as {path, content}."
                ),
                system_prompt=self.get_system_prompt(SYSTEM_PROMPT),
                json_mode=True,
            )
            files = response.content.get("files", [])
            write_results = await self._write_files(context, files) if files else []
            return {
                "status": "COMPLETED",
                "docs_updated": [f["path"] for f in files],
                "files_written": write_results,
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
