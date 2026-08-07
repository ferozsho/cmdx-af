"""Base Agent Class."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from app.llm.router import ModelRouter
from app.tools.gateway.tool_gateway import ToolGateway


class BaseAgent(ABC):
    """Abstract base class for specialized software development agents."""

    def __init__(self, agent_name: str, capability: str = "reasoning") -> None:
        self.agent_name = agent_name
        self.provider = ModelRouter.get_provider(capability)

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

    async def _write_files(
        self,
        context: Dict[str, Any],
        files: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """Write files to workspace via ToolGateway. Each file: {path, content}."""
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
                )
                results.append({
                    "path": f["path"],
                    "success": res.success,
                    "error": res.error if not res.success else None,
                })
            except Exception as e:
                results.append({"path": f["path"], "success": False, "error": str(e)})
        return results

    async def _run_command(
        self,
        context: Dict[str, Any],
        command: str,
    ) -> Dict[str, Any]:
        """Run a shell command via ToolGateway."""
        device = self._get_device_id(context)
        workspace = self._get_workspace_id(context)
        job = self._get_job_id(context)
        try:
            res = await ToolGateway.invoke_tool(
                device_id=device,
                workspace_id=workspace,
                job_id=job,
                tool_name="run_command",
                arguments={"command": command},
            )
            return {"success": res.success, "output": res.result, "error": res.error}
        except Exception as e:
            return {"success": False, "error": str(e)}
