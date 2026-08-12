"""JSON-response Streamable HTTP MCP endpoint for IDE integrations."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM, get_current_user
from app.models.instruction import Instruction
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.services.instruction_events import append_instruction_event
from app.services.project_context import build_project_context

router = APIRouter()

LATEST_PROTOCOL = "2025-11-25"
SUPPORTED_PROTOCOLS = {LATEST_PROTOCOL, "2025-06-18"}
SESSION_AUDIENCE = "agentforge-mcp-session"


def _result(request_id: Any, value: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _create_session(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "aud": SESSION_AUDIENCE,
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": str(uuid.uuid4()),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _require_session(request: Request, user_id: str) -> None:
    token = request.headers.get("Mcp-Session-Id", "")
    if not token:
        raise HTTPException(status_code=400, detail="Mcp-Session-Id is required")
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=SESSION_AUDIENCE,
        )
    except JWTError as exc:
        raise HTTPException(status_code=404, detail="MCP session expired") from exc
    if payload.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="MCP session owner mismatch")


def _validate_transport_headers(request: Request, *, initialized: bool) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise HTTPException(status_code=403, detail="Origin is not allowed")
    if initialized:
        version = request.headers.get("MCP-Protocol-Version", "2025-03-26")
        if version not in SUPPORTED_PROTOCOLS:
            raise HTTPException(status_code=400, detail="Unsupported MCP protocol")


async def _owned_context(
    db: AsyncSession,
    user: User,
    project_id: str,
) -> dict[str, Any]:
    project = await ProjectRepository(db).get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return await build_project_context(db, project)


def _tools() -> list[dict[str, Any]]:
    project_schema = {
        "type": "object",
        "properties": {"project_id": {"type": "string"}},
        "required": ["project_id"],
        "additionalProperties": False,
    }
    return [
        {
            "name": "agentforge_project_context",
            "description": "Read bounded project history, evidence, and provenance.",
            "inputSchema": project_schema,
            "annotations": {"readOnlyHint": True, "idempotentHint": True},
        },
        {
            "name": "agentforge_list_tasks",
            "description": "List project tasks, agent progress, and pending questions.",
            "inputSchema": project_schema,
            "annotations": {"readOnlyHint": True, "idempotentHint": True},
        },
        {
            "name": "agentforge_submit_instruction",
            "description": "Queue a new instruction for the durable agent worker.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "prompt": {"type": "string", "minLength": 2, "maxLength": 10000},
                },
                "required": ["project_id", "prompt"],
                "additionalProperties": False,
            },
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
            },
        },
    ]


@router.post("/mcp")
async def mcp_post(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Handle authenticated MCP lifecycle, resource, and tool requests."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(_error(None, -32700, "Parse error"), status_code=400)
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return JSONResponse(
            _error(body.get("id") if isinstance(body, dict) else None, -32600, "Invalid Request"),
            status_code=400,
        )
    method = body.get("method")
    request_id = body.get("id")
    is_initialize = method == "initialize"
    _validate_transport_headers(request, initialized=not is_initialize)

    if is_initialize:
        params = body.get("params") or {}
        requested = str(params.get("protocolVersion", ""))
        protocol = requested if requested in SUPPORTED_PROTOCOLS else LATEST_PROTOCOL
        session_id = _create_session(current_user.id)
        return JSONResponse(
            _result(
                request_id,
                {
                    "protocolVersion": protocol,
                    "capabilities": {
                        "resources": {"listChanged": False},
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {"name": "AgentForge", "version": "1.0.0"},
                    "instructions": (
                        "Use project resources for verified context. Mutating tools "
                        "queue work through the durable approval-aware pipeline."
                    ),
                },
            ),
            headers={
                "Mcp-Session-Id": session_id,
                "MCP-Protocol-Version": protocol,
            },
        )

    _require_session(request, current_user.id)
    if method == "notifications/initialized":
        return Response(status_code=202)
    if method == "ping":
        return JSONResponse(_result(request_id, {}))
    if method == "tools/list":
        return JSONResponse(_result(request_id, {"tools": _tools()}))
    if method == "resources/list":
        projects = await ProjectRepository(db).list_for_user(current_user.id)
        resources = [
            {
                "uri": f"agentforge://projects/{project.id}/context",
                "name": f"{project.name} project context",
                "mimeType": "application/json",
            }
            for project in projects
        ]
        return JSONResponse(_result(request_id, {"resources": resources}))
    if method == "resources/read":
        uri = str((body.get("params") or {}).get("uri", ""))
        prefix = "agentforge://projects/"
        if not uri.startswith(prefix) or not uri.endswith("/context"):
            return JSONResponse(_error(request_id, -32602, "Unknown resource"))
        project_id = uri[len(prefix) : -len("/context")]
        context = await _owned_context(db, current_user, project_id)
        return JSONResponse(
            _result(
                request_id,
                {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(context, default=str),
                        }
                    ]
                },
            )
        )
    if method == "tools/call":
        params = body.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        project_id = str(arguments.get("project_id", ""))
        context = await _owned_context(db, current_user, project_id)
        if name == "agentforge_project_context":
            payload = context
        elif name == "agentforge_list_tasks":
            payload = {
                "tasks": context["instructions"],
                "agent_runs": context["agent_runs"],
                "questions": context["questions"],
            }
        elif name == "agentforge_submit_instruction":
            prompt = str(arguments.get("prompt", "")).strip()
            if len(prompt) < 2 or len(prompt) > 10000:
                return JSONResponse(_error(request_id, -32602, "Invalid prompt"))
            instruction = Instruction(
                id=f"ins_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                user_id=current_user.id,
                prompt=prompt,
                status="PENDING",
            )
            db.add(instruction)
            await append_instruction_event(
                project_id,
                instruction.id,
                {
                    "instruction_id": instruction.id,
                    "agent_name": "System",
                    "status": "PENDING",
                    "message": "Instruction queued from MCP client.",
                },
                db,
            )
            await db.commit()
            payload = {"instruction_id": instruction.id, "status": "PENDING"}
        else:
            return JSONResponse(_error(request_id, -32601, "Unknown tool"))
        return JSONResponse(
            _result(
                request_id,
                {
                    "content": [
                        {"type": "text", "text": json.dumps(payload, default=str)}
                    ],
                    "structuredContent": payload,
                },
            )
        )
    return JSONResponse(_error(request_id, -32601, "Method not found"))


@router.get("/mcp")
async def mcp_get(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Response:
    """Decline server-initiated SSE while retaining Streamable HTTP semantics."""
    _validate_transport_headers(request, initialized=True)
    _require_session(request, current_user.id)
    return Response(status_code=405, headers={"Allow": "POST"})
