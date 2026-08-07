"""Git Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Git Version Control expert. Generate a meaningful commit
message summarizing all changes. Return JSON with:
- "commit_message": well-formatted commit message with type prefix
- "branch": recommended branch name
- "tag": version tag if applicable
- "files_summary": summary of files changed"""


class GitAgent(BaseAgent):
    """Git Agent managing branches, commits, and rollbacks."""

    def __init__(self) -> None:
        super().__init__("Git Agent", capability="coding")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured git commit on agent isolation branch using LLM."""
        instruction_id = context.get("instruction_id", "ins_001")
        prompt = context.get("prompt", "")
        branch_name = f"agent/{instruction_id}"

        # Collect all agent outputs for the commit message
        plan = context.get("plan_json", {})
        backend_files = context.get("files_generated", [])
        docs = context.get("docs_updated", [])
        tests = context.get("tests_generated", [])
        all_changes = list(set(backend_files + docs + tests))

        try:
            response = await self.provider.generate(
                prompt=(
                    f"Instruction: {prompt}\n\n"
                    f"Plan: {plan}\n\n"
                    f"Files changed: {all_changes}\n\n"
                    "Write a conventional commit message summarizing these changes. "
                    "Use format: type(scope): description"
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "branch": branch_name,
                "commit_hash": "pending",  # Will be set by actual git commit
                "commit_message": response.content.get(
                    "commit_message",
                    f"feat: Implementation for instruction {instruction_id}",
                ),
                "tag": response.content.get("tag", ""),
                "files_summary": response.content.get("files_summary", ""),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "branch": branch_name,
                "commit_hash": "",
            }
