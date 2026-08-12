"""Git Agent Implementation."""

import logging
from typing import Any, Dict

from app.agents.base import BaseAgent
from app.services.approvals import ApprovalRequiredError
from app.services.provenance import (
    append_provenance_trailers,
    build_commit_provenance,
)
from app.tools.gateway.tool_gateway import ToolGateway

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Git Version Control expert. Generate a meaningful commit
message summarizing all changes. Return JSON with:
- "commit_message": well-formatted commit message with type prefix
- "branch": recommended branch name
- "tag": version tag if applicable
- "files_summary": summary of files changed"""


class GitAgent(BaseAgent):
    """Git Agent managing branches, commits, and rollbacks."""

    def __init__(
        self,
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        super().__init__(
            "Git Agent",
            capability="coding",
            system_prompt_override=system_prompt_override,
            tools_override=tools_override,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create branch, commit all changes via ToolGateway."""
        instruction_id = context.get("instruction_id", "ins_001")
        prompt = context.get("prompt", "")
        branch_name = f"agent/{instruction_id}"
        device = self._get_device_id(context)
        workspace = self._get_workspace_id(context)
        job = self._get_job_id(context)
        project_config = self._get_project_config(context)
        verification_status = str(
            context.get("verification_status", "UNVERIFIED")
        ).upper()
        if (
            getattr(project_config, "ci_gate_enabled", True)
            and verification_status != "PASSED"
        ):
            return {
                "status": "FAILED",
                "error": (
                    "CI verification gate blocked Git changes: "
                    f"status is {verification_status}."
                ),
                "branch": branch_name,
                "commit_hash": "",
                "verification_status": verification_status,
            }

        # ── Enforce git branch creation policy ──
        await self._check_git_policy(context, "branch_create", branch=branch_name)
        branch_authorization = await self._authorize_tool(
            context,
            "git_checkout_branch",
            "git.branch_create",
            {"branch_name": branch_name},
            f"Create and check out Git branch '{branch_name}'.",
        )

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
                arguments={"branch_name": branch_name},
                authorization_id=branch_authorization,
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
                system_prompt=self.get_system_prompt(SYSTEM_PROMPT),
                json_mode=True,
            )
            commit_msg = response.content.get(
                "commit_message",
                f"feat: Implementation for {instruction_id}",
            )

            # Inject commit template if configured
            template = None
            project_config = self._get_project_config(context)
            if project_config:
                template = getattr(project_config, "git_commit_template", None)
            if template:
                commit_msg = f"{commit_msg}\n\n{template}"

            provenance = build_commit_provenance(
                instruction_id=instruction_id,
                project_id=str(context.get("project_id", "")),
                prompt=prompt,
                branch=branch_name,
                changed_files=all_changes,
                agent_name=self.agent_name,
                model_name=response.model or None,
            )
            commit_msg = append_provenance_trailers(commit_msg, provenance)
            # ── Enforce git commit policy ──
            await self._check_git_policy(context, "commit", branch=branch_name)
            commit_authorization = await self._authorize_tool(
                context,
                "git_commit",
                "git.commit",
                {
                    "branch": branch_name,
                    "files": sorted(all_changes),
                    "provenance_digest": provenance["digest"],
                },
                f"Commit project changes on branch '{branch_name}'.",
            )

            # 3. Commit all changes
            commit_res = await ToolGateway.invoke_tool(
                device_id=device,
                workspace_id=workspace,
                job_id=job,
                tool_name="git_commit",
                arguments={"message": commit_msg},
                authorization_id=commit_authorization,
            )
            commit_result = (
                commit_res.result if isinstance(commit_res.result, dict) else {}
            )
            if commit_res.success:
                commit_hash = str(
                    commit_result.get("commit_hash") or commit_res.result or ""
                )

            # Persist the commit to the git_commits audit table
            if commit_res.success:
                try:
                    from app.core.database import AsyncSessionLocal
                    from app.models.git_commit import GitCommit

                    async with AsyncSessionLocal() as session:
                        session.add(
                            GitCommit(
                                instruction_id=instruction_id,
                                project_id=str(context.get("project_id", "")) or None,
                                user_id=str(context.get("user_id", "")) or None,
                                commit_hash=commit_hash,
                                branch=branch_name,
                                message=commit_msg,
                                provenance_digest=provenance["digest"],
                                prompt_digest=provenance["prompt_sha256"],
                                model_name=response.model or None,
                                changed_files=provenance["changed_files"],
                                commit_metadata={
                                    "schema": provenance["schema"],
                                    "agent": provenance["agent"],
                                    "tree_hash": commit_result.get("tree_hash"),
                                    "parent_hash": commit_result.get("parent_hash"),
                                    "tool_checks": context.get("tool_checks", []),
                                },
                                verification_status=verification_status,
                            )
                        )
                        await session.commit()
                except Exception:
                    logger.exception(
                        "Unable to persist Git provenance for instruction %s",
                        instruction_id,
                    )

            return {
                "status": "COMPLETED",
                "branch": branch_name,
                "commit_hash": commit_hash,
                "commit_message": commit_msg,
                "branch_created": (
                    branch_res.success if branch_res else False
                ),
                "pr_required": bool(
                    getattr(self._get_project_config(context), "git_require_pr", False)
                ),
                "verification_status": verification_status,
                "files_summary": response.content.get("files_summary", ""),
                "provenance": provenance,
                "tokens_used": response.total_tokens,
                "cost": response.cost,
            }
        except ApprovalRequiredError:
            raise
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "branch": branch_name,
                "commit_hash": "",
            }
