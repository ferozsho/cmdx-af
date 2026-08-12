"""Persistence and sanitization for automated verification evidence."""

import hashlib
import json
import logging
import re
from typing import Any

from app.core.database import AsyncSessionLocal
from app.models.verification_run import VerificationRun

logger = logging.getLogger(__name__)

_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;]+"),
    re.compile(r'(?i)("(?:api[_-]?key|token|password|secret)"\s*:\s*")[^"]+'),
)


def sanitize_evidence(value: str, limit: int = 4000) -> str:
    """Redact common credentials and bound persisted command output."""
    redacted = value
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted[:limit]


def evaluate_gate(
    *,
    stored_status: str | None,
    stored_output_digest: str | None,
    local_output_digest: str | None = None,
) -> str:
    """Compute the external CI gate verdict from stored and local evidence.

    Returns one of:
    - ``NO_EVIDENCE`` when no stored evidence exists for the project;
    - ``FAILED`` when the stored run failed, or when the local run produced a
      different output digest than the stored one (stale / tampered
      evidence);
    - ``PASSED`` otherwise.
    """
    if not stored_status or not stored_output_digest:
        return "NO_EVIDENCE"
    if stored_status != "PASSED":
        return "FAILED"
    if (
        local_output_digest
        and local_output_digest != stored_output_digest
    ):
        return "FAILED"
    return "PASSED"


async def record_verification(
    *,
    project_id: str | None,
    instruction_id: str | None,
    category: str,
    command: list[str],
    result: dict[str, Any],
) -> None:
    """Persist content-addressed evidence without storing command arguments."""
    if not project_id or not instruction_id:
        return
    output = str(result.get("output") or result.get("error") or "")
    command_json = json.dumps(command, separators=(",", ":"), ensure_ascii=True)
    status = "PASSED" if result.get("success") else "FAILED"
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                VerificationRun(
                    project_id=project_id,
                    instruction_id=instruction_id,
                    category=category,
                    executable=command[0] if command else "",
                    command_digest=hashlib.sha256(
                        command_json.encode("utf-8")
                    ).hexdigest(),
                    status=status,
                    exit_code=result.get("exit_code"),
                    duration_seconds=float(result.get("duration_seconds") or 0),
                    output_digest=hashlib.sha256(output.encode("utf-8")).hexdigest(),
                    output_excerpt=sanitize_evidence(output),
                )
            )
            await session.commit()
    except Exception:
        logger.exception(
            "Unable to persist verification evidence: instruction=%s category=%s",
            instruction_id,
            category,
        )
