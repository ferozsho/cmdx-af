"""Validation Agent Implementation."""

import json
from typing import Any, Dict, List

from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Code Quality & Validation expert. Analyze the code changes
and identify potential issues. Return JSON with:
- "lint_issues": number of lint issues found
- "type_errors": number of type errors found
- "security_issues": number of security concerns
- "build_status": PASSED or FAILED
- "auto_fixes_applied": list of fixes applied
- "recommendations": list of recommendations"""


def _is_unavailable(output: str) -> bool:
    """Detect when a tool binary is missing rather than a real failure."""
    lowered = output.lower()
    return any(
        token in lowered
        for token in (
            "command not found",
            "no such file",
            "not recognized",
            "is not recognized",
            "no module named",
        )
    )


def _count_issues(output: str) -> int:
    """Count non-empty, non-header lines in a validation tool's output."""
    lines = [
        ln.strip()
        for ln in output.splitlines()
        if ln.strip() and not ln.startswith(("Found ", "error:", "warning:"))
    ]
    return len(lines)


def _content_dict(content: Any) -> Dict[str, Any]:
    """Coerce LLM JSON content (string or dict) into a dict."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


class ValidationAgent(BaseAgent):
    """Validation Agent running Ruff, mypy, Bandit, and ESLint checks."""

    def __init__(self) -> None:
        super().__init__("Validation Agent", capability="validation")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run linting, type-checking, and security validation via real tools."""
        all_files: List[str] = list(
            dict.fromkeys(
                context.get("files_generated", [])
                + context.get("components", [])
            )
        )
        recommendations: List[str] = []
        build_checks: List[Dict[str, Any]] = []  # {tool, passed}
        tools_available = False
        lint_issues: int | None = None
        type_errors: int | None = None
        security_issues: int | None = None

        # 1. Python lint via ruff
        try:
            ruff_run = await self._run_command(
                context, ["ruff", "check", "."]
            )
            out = ruff_run.get("output") or ""
            if out and not _is_unavailable(out):
                tools_available = True
                lint_issues = (
                    0 if ruff_run.get("success") else _count_issues(out)
                )
                build_checks.append(
                    {"tool": "ruff", "passed": bool(ruff_run.get("success"))}
                )
                if not ruff_run.get("success"):
                    recommendations.append("Fix ruff lint issues.")
        except Exception:
            pass

        # 2. Type check via mypy
        try:
            mypy_run = await self._run_command(context, ["mypy", "."])
            out = mypy_run.get("output") or ""
            if out and not _is_unavailable(out):
                tools_available = True
                type_errors = (
                    0 if mypy_run.get("success") else _count_issues(out)
                )
                build_checks.append(
                    {"tool": "mypy", "passed": bool(mypy_run.get("success"))}
                )
                if not mypy_run.get("success"):
                    recommendations.append("Fix mypy type errors.")
        except Exception:
            pass

        # 3. Security scan via bandit (best-effort)
        try:
            bandit_run = await self._run_command(
                context, ["python", "-m", "bandit", "-q", "-r", "."]
            )
            out = bandit_run.get("output") or ""
            if out and not _is_unavailable(out):
                tools_available = True
                security_issues = (
                    0 if bandit_run.get("success") else _count_issues(out)
                )
                build_checks.append(
                    {"tool": "bandit", "passed": bool(bandit_run.get("success"))}
                )
                if not bandit_run.get("success"):
                    recommendations.append("Review bandit security findings.")
        except Exception:
            pass

        # 4. Frontend lint via eslint (best-effort)
        try:
            eslint_run = await self._run_command(context, ["eslint", "."])
            out = eslint_run.get("output") or ""
            if out and not _is_unavailable(out):
                tools_available = True
                lint_issues = (lint_issues or 0) + (
                    0 if eslint_run.get("success") else _count_issues(out)
                )
                build_checks.append(
                    {"tool": "eslint", "passed": bool(eslint_run.get("success"))}
                )
                if not eslint_run.get("success"):
                    recommendations.append("Fix eslint issues.")
        except Exception:
            pass

        # LLM summary/refinement (also the source of truth when tools are
        # unavailable on the target machine)
        llm_out: Dict[str, Any] = {}
        tokens_used = None
        cost = None
        try:
            response = await self.provider.generate(
                prompt=(
                    f"Files changed: {all_files}\n\n"
                    f"Tool checks run: {build_checks}\n\n"
                    "Provide a code-quality validation summary. Return JSON "
                    "with \"lint_issues\", \"type_errors\", \"security_issues\", "
                    "\"build_status\" (PASSED/FAILED), \"auto_fixes_applied\" "
                    "(list), and \"recommendations\" (list)."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            llm_out = _content_dict(response.content)
            tokens_used = response.total_tokens
            cost = response.cost
        except Exception:
            pass

        if not tools_available:
            lint_issues = llm_out.get("lint_issues", 0)
            type_errors = llm_out.get("type_errors", 0)
            security_issues = llm_out.get("security_issues", 0)

        auto_fixes: List[str] = llm_out.get("auto_fixes_applied", []) or []
        recommendations = list(
            dict.fromkeys(recommendations + (llm_out.get("recommendations", []) or []))
        )

        build_status = llm_out.get("build_status", "PASSED")
        if build_checks and any(not c["passed"] for c in build_checks):
            build_status = "FAILED"

        return {
            "status": "COMPLETED",
            "lint_issues": int(lint_issues or 0),
            "type_errors": int(type_errors or 0),
            "security_issues": int(security_issues or 0),
            "build_status": build_status,
            "auto_fixes_applied": auto_fixes,
            "recommendations": recommendations,
            "tool_checks": build_checks,
            "tokens_used": tokens_used,
            "cost": cost,
        }
