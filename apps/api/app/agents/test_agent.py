"""Test Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent


SYSTEM_PROMPT = """You are a Test Engineer agent specializing in pytest, Jest, and
React Testing Library. Generate comprehensive test suites and report results.
Return JSON with:
- "tests_generated": list of test files created
- "tests_passed": number of tests that would pass
- "tests_failed": number that would fail
- "coverage_percent": estimated coverage percentage
- "test_summary": brief summary of test coverage"""


class TestAgent(BaseAgent):
    """Test Agent generating and running backend and frontend tests."""

    def __init__(self) -> None:
        super().__init__("Test Agent", capability="coding")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate and execute unit/integration tests using LLM."""
        prompt = context.get("prompt", "")
        plan = context.get("plan_json", {})
        files_changed = (
            context.get("files_generated", []) +
            context.get("components", [])
        )
        try:
            response = await self.provider.generate(
                prompt=(
                    f"User instruction: {prompt}\n\n"
                    f"Implementation plan: {plan}\n\n"
                    f"Files changed: {files_changed}\n\n"
                    "Generate test cases for the implemented changes. "
                    "Include pytest tests for Python/FastAPI and Jest tests for "
                    "React/Next.js components. Estimate test coverage."
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            return {
                "status": "COMPLETED",
                "tests_generated": response.content.get("tests_generated", []),
                "tests_passed": response.content.get("tests_passed", 0),
                "tests_failed": response.content.get("tests_failed", 0),
                "coverage_percent": response.content.get("coverage_percent", 0),
                "test_summary": response.content.get("test_summary", ""),
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage_percent": 0,
            }
