"""Database Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Database Engineer agent specializing in SQLAlchemy ORM,
PostgreSQL, and Alembic migrations. Generate database code that follows existing
model patterns. Return JSON with:
- "files_generated": list of file paths created (models, migrations)
- "tables_created": list of table/entity names
- "relationships": list of relationship descriptions
- "summary": brief description"""


class DatabaseAgent(BaseAgent):
    """Database Agent generating SQLAlchemy models and Alembic migrations."""

    def __init__(self) -> None:
        super().__init__("Database Agent", capability="coding")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate database models and migrations using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    "Generate required SQLAlchemy ORM models and Alembic migration. "
                    "Follow existing model conventions in the project."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "files_generated": response.content.get("files_generated", []),
                "tables_created": response.content.get("tables_created", []),
                "relationships": response.content.get("relationships", []),
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
