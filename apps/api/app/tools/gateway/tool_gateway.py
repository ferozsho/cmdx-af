"""Cloud Tool Gateway for Dispatching Agent Tool Calls."""

import uuid
from typing import Any, Dict

import httpx

from agentforge_protocol import ToolRequest, ToolResult

from app.core.config import settings
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
        """Route tool invocation to target device over WSS.

        In the API process the device socket is local, so we dispatch through
        the in-process WSS manager. In the worker process (TOOL_GATEWAY_URL
        set) the device sockets live in the API, so we relay the request over
        HTTP to the API's internal tool endpoint.
        """
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        req = ToolRequest(
            request_id=req_id,
            job_id=job_id,
            workspace_id=workspace_id,
            tool_name=tool_name,
            arguments=arguments,
            authorization_id=authorization_id,
        )

        if settings.TOOL_GATEWAY_URL:
            return await cls._relay_via_api(req, device_id)
        return await wss_manager.send_tool_request(device_id, req)

    @classmethod
    async def _relay_via_api(
        cls, req: ToolRequest, device_id: str
    ) -> ToolResult:
        """POST the tool request to the API's internal relay endpoint."""
        url = (
            f"{settings.TOOL_GATEWAY_URL.rstrip('/')}"
            "/api/v1/internal/tools/invoke"
        )
        headers = {"X-Internal-Token": settings.INTERNAL_API_TOKEN}
        try:
            async with httpx.AsyncClient(timeout=125.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "device_id": device_id,
                        "workspace_id": req.workspace_id,
                        "job_id": req.job_id,
                        "tool_name": req.tool_name,
                        "arguments": req.arguments,
                        "authorization_id": req.authorization_id,
                    },
                    headers=headers,
                )
            data = resp.json()
            if resp.status_code >= 400:
                return ToolResult(
                    request_id=req.request_id,
                    job_id=req.job_id,
                    tool_name=req.tool_name,
                    success=False,
                    error=data.get("detail") or f"HTTP {resp.status_code}",
                )
            return ToolResult(
                request_id=data.get("request_id", req.request_id),
                job_id=req.job_id,
                tool_name=data.get("tool_name", req.tool_name),
                success=bool(data.get("success")),
                result=data.get("result"),
                error=data.get("error"),
                duration_ms=data.get("duration_ms") or 0.0,
            )
        except Exception as exc:
            return ToolResult(
                request_id=req.request_id,
                job_id=req.job_id,
                tool_name=req.tool_name,
                success=False,
                error=f"Tool gateway relay failed: {exc}",
            )
