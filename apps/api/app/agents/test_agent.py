"""Test Agent Implementation."""

import re
from typing import Any, Dict, List

from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Test Engineer agent specializing in pytest, Jest, and
React Testing Library. Generate comprehensive test suites and report results.
Return JSON with:
- "files": list of {path, content} objects with COMPLETE test file content
- "tests_passed": number of tests that would pass
- "tests_failed": number that would fail
- "coverage_percent": estimated coverage percentage
- "test_summary": brief summary of test coverage"""


def _is_unavailable(output: str) -> bool:
    """Detect when a tool binary is missing rather than tests failing."""
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


def _parse_pytest_output(output: str) -> Dict[str, Any]:
    """Parse pytest -q output into passed/failed counts."""
    passed = 0
    failed = 0
    for line in output.splitlines():
        m = re.search(r"(\d+) (passed|failed|error)", line)
        if m:
            count = int(m.group(1))
            if m.group(2) == "passed":
                passed = count
            else:
                failed += count
    return {"passed": passed, "failed": failed}


class TestAgent(BaseAgent):
    """Test Agent generating and running backend and frontend tests."""

    def __init__(
        self,
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        super().__init__(
            "Test Agent",
            capability="coding",
            system_prompt_override=system_prompt_override,
            tools_override=tools_override,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tests via LLM, write them, then run pytest for real counts."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        files_changed: List[str] = list(
            dict.fromkeys(
                context.get("files_generated", [])
                + context.get("components", [])
            )
        )
        tests_generated: List[str] = []
        write_results: List[Dict[str, Any]] = []
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    f"Files changed: {files_changed}\n\n"
                    "Generate test cases for the implemented changes. "
                    "Include pytest tests for Python/FastAPI and Jest tests for "
                    "React/Next.js components. Return each test file as "
                    "{path, content} with COMPLETE file content."
                ),
                system_prompt=self.get_system_prompt(SYSTEM_PROMPT),
                json_mode=True,
            )

            # Write generated test files to the workspace
            files = response.content.get("files", []) or []
            if files:
                write_results = await self._write_files(context, files)
                tests_generated = [f["path"] for f in files]

            # Run pytest for real results when tests were written
            pytest_run = await self._run_command(
                context, ["pytest", "-q", "--tb=short"]
            )
            output = pytest_run.get("output") or ""
            if output and not _is_unavailable(output):
                counts = _parse_pytest_output(output)
                passed = counts["passed"]
                failed = counts["failed"]
                summary = f"pytest completed: {passed} passed, {failed} failed"
                coverage = response.content.get("coverage_percent", 0)
            else:
                passed = response.content.get("tests_passed", 0)
                failed = response.content.get("tests_failed", 0)
                coverage = response.content.get("coverage_percent", 0)
                base = response.content.get("test_summary", "")
                if output and _is_unavailable(output):
                    base += " (pytest unavailable on target; estimated counts)"
                summary = base

            return {
                "status": "COMPLETED",
                "tests_generated": tests_generated,
                "tests_written": write_results,
                "tests_passed": passed,
                "tests_failed": failed,
                "coverage_percent": coverage,
                "test_summary": summary,
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "tests_generated": tests_generated,
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage_percent": 0,
            }
