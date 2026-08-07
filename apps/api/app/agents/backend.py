"""Backend Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Backend Engineer agent specializing in FastAPI, Python,
and service-layer architecture. Generate complete backend code files.
Return JSON with:
- "files": list of {path, content} objects with COMPLETE file content
- "summary": brief description
- "key_decisions": list of architectural decisions"""


class BackendAgent(BaseAgent):
    """Backend Agent generating and writing FastAPI routes, services, schemas."""

    def __init__(self) -> None:
        super().__init__("Backend Agent", capability="coding")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate backend code via LLM and write to workspace."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Generate COMPLETE backend Python code (FastAPI routes, "
                    "services, schemas) with full file content including all imports."
                ),
                system_prompt=SYSTEM_PROMPT,
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
                "summary": response.content.get("summary", ""),
                "key_decisions": response.content.get("key_decisions", []),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {"status": "FAILED", "error": str(e), "files_generated": []}
