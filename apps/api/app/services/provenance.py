"""Deterministic provenance records for AI-authored source changes."""

import hashlib
import json
from typing import Any


def sha256_text(value: str) -> str:
    """Return a stable SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_commit_provenance(
    *,
    instruction_id: str,
    project_id: str,
    prompt: str,
    branch: str,
    changed_files: list[str],
    agent_name: str,
    model_name: str | None,
) -> dict[str, Any]:
    """Build a content-addressed, secret-free provenance manifest."""
    manifest: dict[str, Any] = {
        "schema": "agentforge.dev/provenance/v1",
        "generator": "AgentForge",
        "ai_generated": True,
        "instruction_id": instruction_id,
        "project_id": project_id,
        "prompt_sha256": sha256_text(prompt),
        "branch": branch,
        "changed_files": sorted(set(changed_files)),
        "agent": agent_name,
        "model": model_name,
    }
    canonical = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    manifest["digest"] = sha256_text(canonical)
    return manifest


def append_provenance_trailers(message: str, provenance: dict[str, Any]) -> str:
    """Append machine-readable Git trailers without duplicating them."""
    if "AgentForge-Provenance:" in message:
        return message
    trailers = [
        "AI-Generated: true",
        f"AgentForge-Instruction: {provenance['instruction_id']}",
        f"AgentForge-Provenance: sha256:{provenance['digest']}",
    ]
    return f"{message.rstrip()}\n\n" + "\n".join(trailers)
