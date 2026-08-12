"""Tool Request Handler for Local Agent Execution Daemon."""

import time
from typing import Any

from agentforge_protocol import ToolRequest, ToolResult

from agentforge_local.execution.runner import ExecutionRunner
from agentforge_local.filesystem.ops import FilesystemTools
from agentforge_local.git.ops import GitTools
from agentforge_local.rag.indexer import LocalRAGIndexer


class ToolHandler:
    """Dispatches incoming ToolRequests to local tool functions."""

    def __init__(self, workspace_manager: Any) -> None:
        self.ws_mgr = workspace_manager

    MUTATING_TOOLS = frozenset(
        {
            "write_file",
            "update_file",
            "delete_file",
            "run_command",
            "run_tests",
            "run_linter",
            "run_formatter",
            "run_type_check",
            "run_build",
            "git_branch",
            "git_checkout_branch",
            "git_commit",
            "git_rollback",
            "create_pull_request",
        }
    )

    async def handle_request(self, req: ToolRequest) -> ToolResult:
        """Execute tool and capture timing/errors."""
        start_time = time.time()
        args = req.arguments
        if req.tool_name in self.MUTATING_TOOLS and not req.authorization_id:
            return ToolResult(
                request_id=req.request_id,
                job_id=req.job_id,
                tool_name=req.tool_name,
                success=False,
                error="Mutating tool call has no policy or approval authorization.",
            )
        if req.tool_name == "validate_path":
            ws_path = ""
        else:
            ws_path = self.ws_mgr.get_workspace_path(req.workspace_id)
            if not ws_path:
                return ToolResult(
                    request_id=req.request_id,
                    job_id=req.job_id,
                    tool_name=req.tool_name,
                    success=False,
                    error=f"Workspace '{req.workspace_id}' is not authorized.",
                )

        try:
            res: Any = None

            if req.tool_name == "read_file":
                res = FilesystemTools.read_file(ws_path, args["path"])
            elif req.tool_name == "write_file":
                res = FilesystemTools.write_file(ws_path, args["path"], args["content"])
            elif req.tool_name == "update_file":
                res = FilesystemTools.update_file(
                    ws_path,
                    args["path"],
                    args["old_str"],
                    args["new_str"],
                )
            elif req.tool_name == "delete_file":
                res = FilesystemTools.delete_file(ws_path, args["path"])
            elif req.tool_name == "get_project_tree":
                res = FilesystemTools.get_project_tree(ws_path)
            elif req.tool_name == "list_files":
                res = FilesystemTools.list_files(
                    ws_path,
                    path=args.get("path", "."),
                    recursive=bool(args.get("recursive", False)),
                    limit=int(args.get("limit", 1000)),
                )
            elif req.tool_name == "search_in_files":
                res = FilesystemTools.search_in_files(
                    ws_path,
                    query=args.get("query", ""),
                    path=args.get("path", "."),
                    case_sensitive=bool(args.get("case_sensitive", False)),
                    limit=int(args.get("limit", 100)),
                )
            elif req.tool_name == "git_status":
                res = GitTools.get_status(ws_path)
            elif req.tool_name == "git_checkout_branch":
                res = GitTools.create_and_checkout_branch(ws_path, args["branch_name"])
            elif req.tool_name == "git_branch":
                res = GitTools.create_and_checkout_branch(
                    ws_path,
                    args["branch_name"],
                )
            elif req.tool_name == "git_commit":
                res = GitTools.commit_changes(ws_path, args["message"])
            elif req.tool_name == "git_diff":
                res = GitTools.get_diff(ws_path)
            elif req.tool_name == "git_log":
                res = GitTools.get_log(ws_path, max_count=args.get("max_count", 20))
            elif req.tool_name == "git_rollback":
                res = GitTools.rollback(ws_path, args["commit_hash"])
            elif req.tool_name == "create_pull_request":
                res = GitTools.create_pull_request(
                    ws_path,
                    args["branch_name"],
                    args["title"],
                    body=args.get("body", ""),
                    base=args.get("base", "main"),
                )
            elif req.tool_name == "git_show_file":
                res = GitTools.show_file(ws_path, args["path"])
            elif req.tool_name == "run_command":
                res = ExecutionRunner.run_command(
                    ws_path,
                    args["cmd_array"],
                    timeout=min(int(args.get("timeout", 60)), 300),
                )
            elif req.tool_name in {
                "run_tests",
                "run_linter",
                "run_formatter",
                "run_type_check",
                "run_build",
            }:
                task = {
                    "run_tests": "tests",
                    "run_linter": "linter",
                    "run_formatter": "formatter",
                    "run_type_check": "type_check",
                    "run_build": "build",
                }[req.tool_name]
                res = ExecutionRunner.run_task(
                    ws_path,
                    task,
                    cmd_array=args.get("cmd_array"),
                    timeout=min(int(args.get("timeout", 60)), 300),
                )
            elif req.tool_name == "validate_path":
                res = FilesystemTools.validate_path(args.get("path", ""))
            elif req.tool_name == "rag_search":
                # Search only — indexing is done by the file watcher or an
                # explicit rag_reindex, so searches stay fast on large repos.
                indexer = LocalRAGIndexer.get(ws_path)
                res = indexer.search(
                    args.get("query", ""), top_k=args.get("top_k", 5)
                )
            elif req.tool_name == "rag_reindex":
                indexer = LocalRAGIndexer.get(ws_path)
                indexer.index_workspace(
                    chunk_size=args.get("chunk_size"),
                    chunk_overlap=args.get("chunk_overlap"),
                )
                files_indexed = len(
                    {c["file_path"] for c in indexer.indexed_chunks}
                )
                res = {
                    "files_indexed": files_indexed,
                    "chunks": len(indexer.indexed_chunks),
                    "last_index": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            elif req.tool_name == "rag_status":
                indexer = LocalRAGIndexer.get(ws_path)
                res = indexer.status()
            elif req.tool_name == "rag_chunks":
                # Browse the full index: paginated chunk list (with optional
                # file-path/content substring filter) for the UI's default
                # "All Chunks" view.
                indexer = LocalRAGIndexer.get(ws_path)
                res = indexer.list_chunks(
                    offset=args.get("offset", 0),
                    limit=args.get("limit", 10),
                    query=args.get("query", ""),
                )
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
