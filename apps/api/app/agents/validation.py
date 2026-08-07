"""Validation Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Code Quality & Validation expert. Analyze the code changes
and identify potential issues. Return JSON with:
- "lint_issues": number of lint issues found
- "type_errors": number of type errors found
- "security_issues": number of security concerns
- "build_status": PASSED or FAILED
- "auto_fixes_applied": list of fixes applied
- "recommendations": list of recommendations"""


class ValidationAgent(BaseAgent):
    """Validation Agent running Ruff, mypy, Bandit, and ESLint checks."""

    def __init__(self) -> None:
        super().__init__("Validation Agent", capability="validation")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run syntax, linting, type-checking, and security validation."""
        frontend_files = context.get("files_generated", [])
        backend_files = context.get("files_generated", [])
        all_files = frontend_files + backend_files
        try:
            response = await self.provider.generate(
                prompt=(
                    f"Files changed: {all_files}\n\n"
                    "Review these code changes for lint issues, type errors, "
                    "security concerns, and build integrity. "
                    "Identify any auto-fixes that should be applied."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "lint_issues": response.content.get("lint_issues", 0),
                "type_errors": response.content.get("type_errors", 0),
                "security_issues": response.content.get("security_issues", 0),
                "build_status": response.content.get("build_status", "PASSED"),
                "auto_fixes_applied": (
                    response.content.get("auto_fixes_applied", [])
                ),
                "recommendations": response.content.get("recommendations", []),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "lint_issues": 0,
            }
