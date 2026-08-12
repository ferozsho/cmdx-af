"""Base Agent Class."""

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.llm.router import ModelRouter
from app.tools.gateway.tool_gateway import ToolGateway


class BaseAgent(ABC):
    """Abstract base class for specialized software development agents."""

    def __init__(
        self,
        agent_name: str,
        capability: str = "reasoning",
        system_prompt_override: str | None = None,
        tools_override: list[str] | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.provider = ModelRouter.get_provider(capability)
        self._system_prompt_override = system_prompt_override
        self._tools_override = tools_override

    def get_system_prompt(self, default: str) -> str:
        """Return the override system prompt if set, otherwise the default."""
        return self._system_prompt_override or default

    def get_tools(self, default: list[str] | None = None) -> list[str]:
        """Return override tools list if set, otherwise the default (or empty)."""
        if self._tools_override is not None:
            return self._tools_override
        return default or []

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task and return result dictionary."""
        pass

    def _get_device_id(self, context: Dict[str, Any]) -> str:
        return context.get("device_id", "dev_feroz_pc")

    def _get_workspace_id(self, context: Dict[str, Any]) -> str:
        return context.get("workspace_id", "ws-test")

    def _get_job_id(self, context: Dict[str, Any]) -> str:
        return context.get("instruction_id", "unknown")

    def _get_project_config(self, context: Dict[str, Any]) -> Optional[object]:
        """Return the project config object injected by the pipeline, if any."""
        return context.get("project_config")

    async def _check_fs_policy(
        self, context: Dict[str, Any], operation: str
    ) -> None:
        """Enforce filesystem policy before dispatching a tool call."""
        project = self._get_project_config(context)
        if project is None:
            return
        from app.core.policies import check_fs_policy

        check_fs_policy(project, operation)

    async def _check_git_policy(
        self,
        context: Dict[str, Any],
        operation: str,
        branch: str | None = None,
    ) -> None:
        """Enforce git policy before dispatching a git tool call."""
        project = self._get_project_config(context)
        if project is None:
            return
        from app.core.policies import check_git_policy

        check_git_policy(project, operation, branch=branch)

    async def _authorize_tool(
        self,
        context: Dict[str, Any],
        tool_name: str,
        operation: str,
        arguments: dict[str, Any],
        summary: str,
    ) -> str:
        """Apply project policy and obtain a one-time mutation grant."""
        from app.services.approvals import authorize_tool

        project = self._get_project_config(context)
        user_id = str(
            context.get("user_id")
            or getattr(project, "user_id", "")
        )
        if not user_id:
            raise PermissionError("Instruction owner is unavailable.")
        return await authorize_tool(
            project=project,
            user_id=user_id,
            instruction_id=context.get("instruction_id"),
            tool_name=tool_name,
            operation=operation,
            arguments=arguments,
            summary=summary,
        )

    async def _write_files(
        self,
        context: Dict[str, Any],
        files: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """Write files to workspace via ToolGateway. Each file: {path, content}."""
        # Enforce filesystem write policy
        await self._check_fs_policy(context, "write")
        approval_arguments = {
            "files": [
                {
                    "path": item["path"],
                    "characters": len(item["content"]),
                    "sha256": hashlib.sha256(
                        item["content"].encode("utf-8")
                    ).hexdigest(),
                }
                for item in files
            ]
        }
        authorization_id = await self._authorize_tool(
            context,
            "write_file",
            "filesystem.write",
            approval_arguments,
            f"Write {len(files)} file(s) to the project workspace.",
        )

        results = []
        device = self._get_device_id(context)
        workspace = self._get_workspace_id(context)
        job = self._get_job_id(context)
        for f in files:
            try:
                res = await ToolGateway.invoke_tool(
                    device_id=device,
                    workspace_id=workspace,
                    job_id=job,
                    tool_name="write_file",
                    arguments={"path": f["path"], "content": f["content"]},
                    authorization_id=authorization_id,
                )
                results.append({
                    "path": f["path"],
                    "success": res.success,
                    "error": res.error if not res.success else None,
                })
            except Exception as e:
                results.append({"path": f["path"], "success": False, "error": str(e)})
            # Audit log each write to the file_operations table
            try:
                from app.core.database import AsyncSessionLocal
                from app.models.file_operation import FileOperation

                async with AsyncSessionLocal() as session:
                    session.add(
                        FileOperation(
                            instruction_id=job,
                            operation_type="write",
                            file_path=f["path"],
                        )
                    )
                    await session.commit()
            except Exception:
                pass
        return results

    async def _read_file(
        self,
        context: Dict[str, Any],
        path: str,
    ) -> Dict[str, Any]:
        """Read a single file from workspace via ToolGateway."""
        await self._check_fs_policy(context, "read")
        device = self._get_device_id(context)
        workspace = self._get_workspace_id(context)
        job = self._get_job_id(context)
        try:
            res = await ToolGateway.invoke_tool(
                device_id=device,
                workspace_id=workspace,
                job_id=job,
                tool_name="read_file",
                arguments={"path": path},
            )
            if not res.success:
                return {"path": path, "success": False, "error": res.error}
            return {"path": path, "success": True, "content": res.result}
        except Exception as e:
            return {"path": path, "success": False, "error": str(e)}

    async def _delete_file(
        self,
        context: Dict[str, Any],
        path: str,
    ) -> Dict[str, Any]:
        """Delete a file from workspace via ToolGateway."""
        await self._check_fs_policy(context, "delete")
        authorization_id = await self._authorize_tool(
            context,
            "delete_file",
            "filesystem.delete",
            {"path": path},
            f"Delete '{path}' from the project workspace.",
        )
        device = self._get_device_id(context)
        workspace = self._get_workspace_id(context)
        job = self._get_job_id(context)
        try:
            res = await ToolGateway.invoke_tool(
                device_id=device,
                workspace_id=workspace,
                job_id=job,
                tool_name="delete_file",
                arguments={"path": path},
                authorization_id=authorization_id,
            )
            if not res.success:
                return {"path": path, "success": False, "error": res.error}
            return {"path": path, "success": True}
        except Exception as e:
            return {"path": path, "success": False, "error": str(e)}

    async def _run_command(
        self,
        context: Dict[str, Any],
        cmd_array: List[str],
        *,
        operation: str = "command.execute",
        category: str = "command",
    ) -> Dict[str, Any]:
        """Run a shell command array via ToolGateway."""
        device = self._get_device_id(context)
        workspace = self._get_workspace_id(context)
        job = self._get_job_id(context)
        project = self._get_project_config(context)
        timeout = int(getattr(project, "max_command_seconds", 120) or 120)
        authorization_id = await self._authorize_tool(
            context,
            "run_command",
            operation,
            {"cmd_array": cmd_array, "timeout": timeout},
            f"Run command: {' '.join(cmd_array)}",
        )
        try:
            res = await ToolGateway.invoke_tool(
                device_id=device,
                workspace_id=workspace,
                job_id=job,
                tool_name="run_command",
                arguments={"cmd_array": cmd_array, "timeout": timeout},
                authorization_id=authorization_id,
            )
            if not res.success:
                result = {"success": False, "output": "", "error": res.error}
                await self._record_verification(
                    context, cmd_array, category, result
                )
                return result
            result = res.result
            if isinstance(result, dict):
                parsed_result = {
                    "success": result.get("exit_code", 0) == 0,
                    "exit_code": result.get("exit_code", 0),
                    "output": (
                        str(result.get("stdout", ""))
                        + "\n"
                        + str(result.get("stderr", ""))
                    ).strip(),
                    "duration_seconds": result.get("duration_seconds", 0),
                    "error": None,
                }
                await self._record_verification(
                    context, cmd_array, category, parsed_result
                )
                return parsed_result
            parsed_result = {
                "success": True,
                "output": str(result),
                "exit_code": 0,
                "error": None,
            }
            await self._record_verification(
                context, cmd_array, category, parsed_result
            )
            return parsed_result
        except Exception as e:
            result = {"success": False, "output": "", "error": str(e)}
            await self._record_verification(context, cmd_array, category, result)
            return result

    async def _record_verification(
        self,
        context: Dict[str, Any],
        command: list[str],
        category: str,
        result: dict[str, Any],
    ) -> None:
        """Persist bounded, redacted evidence for a completed command."""
        from app.services.verification import record_verification

        await record_verification(
            project_id=context.get("project_id"),
            instruction_id=context.get("instruction_id"),
            category=category,
            command=command,
            result=result,
        )
