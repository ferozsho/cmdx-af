"""Cloud Tool Gateway for Dispatching Agent Tool Calls."""

import uuid
from typing import Any, Dict

from agentforge_protocol import ToolRequest, ToolResult

from app.wss.connection_manager import wss_manager


class ToolGateway:
    """Unified Tool Gateway Abstraction routing requests to Local Agents or Cloud Sandboxes."""

    @classmethod
    async def invoke_tool(
        cls,
        device_id: str,
        workspace_id: str,
        job_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        authorization_id: str | None = None,
    ) -> ToolResult:
        """Route tool invocation to target device over WSS."""
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        req = ToolRequest(
            request_id=req_id,
            job_id=job_id,
            workspace_id=workspace_id,
            tool_name=tool_name,
            arguments=arguments,
            authorization_id=authorization_id,
        )

        return await wss_manager.send_tool_request(device_id, req)
