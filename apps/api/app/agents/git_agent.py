"""Git Agent Implementation."""

from typing import Any, Dict
from app.agents.base import BaseAgent
from app.tools.gateway.tool_gateway import ToolGateway


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
        """Create branch, commit all changes via ToolGateway."""
        instruction_id = context.get("instruction_id", "ins_001")
        prompt = context.get("prompt", "")
        branch_name = f"agent/{instruction_id}"
        device = self._get_device_id(context)
        workspace = self._get_workspace_id(context)
        job = self._get_job_id(context)

        # Collect all agent outputs for the commit message
        plan = context.get("plan_json", {})
        backend_files = context.get("files_generated", [])
        docs = context.get("docs_updated", [])
        tests = context.get("tests_generated", [])
        all_changes = list(set(backend_files + docs + tests))

        commit_hash = ""
        try:
            # 1. Create and checkout agent branch
            branch_res = await ToolGateway.invoke_tool(
                device_id=device,
                workspace_id=workspace,
                job_id=job,
                tool_name="git_checkout_branch",
                arguments={"branch": branch_name},
            )
        except Exception:
            branch_res = None

        try:
            # 2. Generate commit message via LLM
            response = await self.provider.generate(
                prompt=(
                    f"Instruction: {prompt}\n\n"
                    f"Plan: {plan}\n\n"
                    f"Files changed: {all_changes}\n\n"
                    "Write a conventional commit message. "
                    "Format: type(scope): description"
                ),
                system_prompt=SYSTEM_PROMPT,
                json_mode=True,
            )
            commit_msg = response.content.get(
                "commit_message",
                f"feat: Implementation for {instruction_id}",
            )

            # 3. Commit all changes
            commit_res = await ToolGateway.invoke_tool(
                device_id=device,
                workspace_id=workspace,
                job_id=job,
                tool_name="git_commit",
                arguments={"message": commit_msg},
            )
            if commit_res.success:
                commit_hash = str(commit_res.result or "")[:8]

            return {
                "status": "COMPLETED",
                "branch": branch_name,
                "commit_hash": commit_hash or "committed",
                "commit_message": commit_msg,
                "branch_created": (
                    branch_res.success if branch_res else False
                ),
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
