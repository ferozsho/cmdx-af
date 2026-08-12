"""Frontend Agent Implementation."""

from typing import Any, Dict

from app.agents.base import BaseAgent

SYSTEM_PROMPT = """You are a Frontend Engineer agent specializing in React, Next.js 16,
and TypeScript. Generate production-ready frontend code that follows project patterns.
Return JSON with:
- "files": list of {path, content} objects with COMPLETE file content
- "components": list of component names created
- "summary": brief description"""


class FrontendAgent(BaseAgent):
    """Frontend Agent generating and writing React/Next.js components."""

    def __init__(
        self,
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        super().__init__(
            "Frontend Agent",
            capability="coding",
            system_prompt_override=system_prompt_override,
            tools_override=tools_override,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate frontend code via LLM and write to workspace."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Generate COMPLETE frontend code files (React/Next.js components, "
                    "pages, hooks) with full file content. Each file must include "
                    "ALL imports and complete implementation code."
                ),
                system_prompt=self.get_system_prompt(SYSTEM_PROMPT),
                json_mode=True,
            )
            files = response.content.get("files", [])
            write_results = (
                await self._write_files(context, files) if files else []
            )
            return {
                "status": "COMPLETED",
                "files_generated": [f["path"] for f in files],
                "files_written": write_results,
                "components": response.content.get("components", []),
                "summary": response.content.get("summary", ""),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {"status": "FAILED", "error": str(e), "files_generated": []}
