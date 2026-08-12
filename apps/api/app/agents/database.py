"""Database Agent Implementation."""

from typing import Any, Dict

from app.agents.base import BaseAgent

SYSTEM_PROMPT = """You are a Database Engineer agent specializing in SQLAlchemy ORM,
PostgreSQL, and Alembic migrations. Generate database code that follows existing
model patterns. Return JSON with:
- "files": list of {path, content} objects with COMPLETE file content
- "tables_created": list of table/entity names
- "relationships": list of relationship descriptions
- "summary": brief description"""


class DatabaseAgent(BaseAgent):
    """Database Agent generating SQLAlchemy models and Alembic migrations."""

    def __init__(
        self,
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        super().__init__(
            "Database Agent",
            capability="coding",
            system_prompt_override=system_prompt_override,
            tools_override=tools_override,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate database models and migrations using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Generate required SQLAlchemy ORM models and Alembic "
                    "migration. Include COMPLETE file content for each "
                    "generated file. Return each file as {path, content}."
                ),
                system_prompt=self.get_system_prompt(SYSTEM_PROMPT),
                json_mode=True,
            )
            content = response.content
            files = [
                {"path": item["path"], "content": item.get("content", "")}
                for item in (content.get("files") or [])
                if isinstance(item, dict) and item.get("path")
            ]
            write_results = (
                await self._write_files(context, files) if files else []
            )
            return {
                "status": "COMPLETED",
                "files_generated": [f["path"] for f in files],
                "files_written": write_results,
                "tables_created": content.get("tables_created", []),
                "relationships": content.get("relationships", []),
                "summary": content.get("summary", ""),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "files_generated": [],
            }
