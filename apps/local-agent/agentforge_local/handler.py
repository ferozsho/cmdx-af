"""Tool Request Handler for Local Agent Execution Daemon."""

import time
from typing import Any, Dict
from agentforge_protocol import ToolRequest, ToolResult
from agentforge_local.filesystem.ops import FilesystemTools
from agentforge_local.git.ops import GitTools
from agentforge_local.execution.runner import ExecutionRunner


class ToolHandler:
    """Dispatches incoming ToolRequests to local tool functions."""

    def __init__(self, workspace_manager: Any) -> None:
        self.ws_mgr = workspace_manager

    async def handle_request(self, req: ToolRequest) -> ToolResult:
        """Execute tool and capture timing/errors."""
        start_time = time.time()
        ws_path = self.ws_mgr.get_workspace_path(req.workspace_id)

        if not ws_path:
            return ToolResult(
                request_id=req.request_id,
                job_id=req.job_id,
                tool_name=req.tool_name,
                success=False,
                error=f"Workspace '{req.workspace_id}' is not registered on this device",
            )

        try:
            res: Any = None
            args = req.arguments

            if req.tool_name == "read_file":
                res = FilesystemTools.read_file(ws_path, args["path"])
            elif req.tool_name == "write_file":
                res = FilesystemTools.write_file(ws_path, args["path"], args["content"])
            elif req.tool_name == "update_file":
                res = FilesystemTools.update_file(ws_path, args["path"], args["old_str"], args["new_str"])
            elif req.tool_name == "delete_file":
                res = FilesystemTools.delete_file(ws_path, args["path"])
            elif req.tool_name == "get_project_tree":
                res = FilesystemTools.get_project_tree(ws_path)
            elif req.tool_name == "git_status":
                res = GitTools.get_status(ws_path)
            elif req.tool_name == "git_checkout_branch":
                res = GitTools.create_and_checkout_branch(ws_path, args["branch_name"])
            elif req.tool_name == "git_commit":
                res = GitTools.commit_changes(ws_path, args["message"])
            elif req.tool_name == "git_diff":
                res = GitTools.get_diff(ws_path)
            elif req.tool_name == "git_rollback":
                res = GitTools.rollback(ws_path, args["commit_hash"])
            elif req.tool_name == "run_command":
                res = ExecutionRunner.run_command(ws_path, args["cmd_array"])
            else:
                raise ValueError(f"Unknown tool name '{req.tool_name}'")

            duration = (time.time() - start_time) * 1000
            return ToolResult(
                request_id=req.request_id,
                job_id=req.job_id,
                tool_name=req.tool_name,
                success=True,
                result=res,
                duration_ms=round(duration, 2),
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return ToolResult(
                request_id=req.request_id,
                job_id=req.job_id,
                tool_name=req.tool_name,
                success=False,
                error=str(e),
                duration_ms=round(duration, 2),
            )
