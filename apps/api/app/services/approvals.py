"""Central policy and durable approval enforcement for tool mutations."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.policies import PolicyBlockedError
from app.models.approval import ApprovalRequest
from app.services.instruction_events import append_instruction_event

RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
TOOL_RISK = {
    "write_file": "MEDIUM",
    "update_file": "MEDIUM",
    "git_checkout_branch": "MEDIUM",
    "git_branch": "MEDIUM",
    "run_tests": "MEDIUM",
    "run_linter": "MEDIUM",
    "run_type_check": "MEDIUM",
    "run_formatter": "HIGH",
    "run_build": "HIGH",
    "run_command": "HIGH",
    "delete_file": "HIGH",
    "git_commit": "HIGH",
    "git_rollback": "CRITICAL",
    "create_pull_request": "HIGH",
}
OPERATION_RISK = {
    "command.validate": "MEDIUM",
}


class ApprovalRequiredError(Exception):
    """Raised when execution must pause for a human decision."""

    def __init__(self, approval_id: str, summary: str) -> None:
        super().__init__(summary)
        self.approval_id = approval_id
        self.summary = summary


def _safe_payload(value: Any) -> Any:
    """Remove file contents and bound stored approval previews."""
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"content", "old_str", "new_str", "image_bytes"}:
                safe[key] = f"<{len(str(item))} characters>"
            else:
                safe[key] = _safe_payload(item)
        return safe
    if isinstance(value, list):
        return [_safe_payload(item) for item in value[:100]]
    if isinstance(value, str):
        return value[:2000]
    return value


def _fingerprint(tool_name: str, arguments: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"tool": tool_name, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _requires_approval(mode: str, risk_level: str) -> bool:
    normalized = mode.upper()
    if normalized == "NEVER":
        return False
    if normalized == "RISKY":
        return RISK_ORDER.get(risk_level, 3) >= RISK_ORDER["HIGH"]
    return True


def _enforce_command_policy(project: object, arguments: dict[str, Any]) -> None:
    command = arguments.get("cmd_array") or []
    executable = str(command[0]) if command else ""
    allowed = set(getattr(project, "command_allowlist", []) or [])
    if not executable or executable not in allowed:
        raise PolicyBlockedError(
            status_code=403,
            detail=f"Command '{executable}' is not allowed by project policy.",
        )
    requested_timeout = int(arguments.get("timeout") or 60)
    max_timeout = int(getattr(project, "max_command_seconds", 120) or 120)
    if requested_timeout > max_timeout:
        raise PolicyBlockedError(
            status_code=403,
            detail=(
                f"Command timeout {requested_timeout}s exceeds the project "
                f"limit of {max_timeout}s."
            ),
        )


async def authorize_tool(
    *,
    project: object | None,
    user_id: str,
    instruction_id: str | None,
    tool_name: str,
    operation: str,
    arguments: dict[str, Any],
    summary: str,
) -> str:
    """Return a local-agent authorization ID or pause for human approval."""
    if project is None:
        raise PolicyBlockedError(
            status_code=403,
            detail="Project policy is unavailable; mutating tool call denied.",
        )
    if tool_name in {
        "run_command",
        "run_tests",
        "run_linter",
        "run_formatter",
        "run_type_check",
        "run_build",
    }:
        _enforce_command_policy(project, arguments)

    project_id = str(getattr(project, "id"))
    risk_level = OPERATION_RISK.get(operation, TOOL_RISK.get(tool_name, "HIGH"))
    mode = str(getattr(project, "approval_mode", "RISKY"))
    if not _requires_approval(mode, risk_level):
        return f"policy:{project_id}:{tool_name}"

    fingerprint = _fingerprint(tool_name, arguments)
    now = datetime.now(UTC).replace(tzinfo=None)
    async with AsyncSessionLocal() as db:
        query = select(ApprovalRequest).where(
            ApprovalRequest.project_id == project_id,
            ApprovalRequest.user_id == user_id,
            ApprovalRequest.fingerprint == fingerprint,
        )
        query = (
            query.where(ApprovalRequest.instruction_id == instruction_id)
            if instruction_id is not None
            else query.where(ApprovalRequest.instruction_id.is_(None))
        )
        approval = await db.scalar(
            query.order_by(ApprovalRequest.requested_at.desc())
            .with_for_update()
            .limit(1)
        )
        if approval and approval.status == "APPROVED" and not approval.consumed_at:
            if approval.expires_at < now:
                approval.status = "EXPIRED"
            else:
                approval.consumed_at = now
                await db.commit()
                return f"approval:{approval.id}"
        if approval and approval.status == "PENDING":
            if approval.expires_at < now:
                approval.status = "EXPIRED"
            else:
                raise ApprovalRequiredError(approval.id, approval.summary)

        approval = ApprovalRequest(
            project_id=project_id,
            user_id=user_id,
            instruction_id=instruction_id,
            tool_name=tool_name,
            operation=operation,
            risk_level=risk_level,
            fingerprint=fingerprint,
            request_payload=_safe_payload(arguments),
            summary=summary,
            status="PENDING",
            expires_at=now + timedelta(hours=24),
        )
        db.add(approval)
        await db.flush()
        if instruction_id:
            await append_instruction_event(
                project_id,
                instruction_id,
                {
                    "instruction_id": instruction_id,
                    "agent_name": "System",
                    "status": "WAITING_APPROVAL",
                    "message": summary,
                    "data": {"approval_id": approval.id, "risk": risk_level},
                },
                db,
            )
        await db.commit()
        raise ApprovalRequiredError(approval.id, approval.summary)
