"""Tests for deterministic AI change provenance."""

from types import SimpleNamespace

import pytest

from app.agents.git_agent import GitAgent
from app.core.policies import PolicyBlockedError, check_git_policy
from app.services.provenance import (
    append_provenance_trailers,
    build_commit_provenance,
)


def test_commit_provenance_is_deterministic_and_does_not_store_prompt() -> None:
    """Equivalent change inputs produce the same content-addressed manifest."""
    inputs = {
        "instruction_id": "instruction-1",
        "project_id": "project-1",
        "prompt": "Implement the requested feature with token secret-value",
        "branch": "agent/instruction-1",
        "changed_files": ["b.py", "a.py", "a.py"],
        "agent_name": "Git Agent",
        "model_name": "test-model",
    }
    first = build_commit_provenance(**inputs)
    second = build_commit_provenance(**inputs)

    assert first == second
    assert first["changed_files"] == ["a.py", "b.py"]
    assert "secret-value" not in str(first)
    assert len(first["prompt_sha256"]) == 64
    assert len(first["digest"]) == 64


def test_commit_trailers_are_machine_readable_and_idempotent() -> None:
    provenance = build_commit_provenance(
        instruction_id="instruction-1",
        project_id="project-1",
        prompt="Change it",
        branch="agent/instruction-1",
        changed_files=["app.py"],
        agent_name="Git Agent",
        model_name="test-model",
    )

    message = append_provenance_trailers("feat: change it", provenance)

    assert "AI-Generated: true" in message
    assert "AgentForge-Instruction: instruction-1" in message
    assert f"AgentForge-Provenance: sha256:{provenance['digest']}" in message
    assert append_provenance_trailers(message, provenance) == message


@pytest.mark.asyncio
async def test_git_agent_blocks_unverified_change_before_using_tools() -> None:
    """The CI gate fails closed before branch creation or LLM usage."""
    agent = GitAgent.__new__(GitAgent)
    result = await agent.execute(
        {
            "instruction_id": "instruction-1",
            "project_config": SimpleNamespace(ci_gate_enabled=True),
            "verification_status": "UNVERIFIED",
        }
    )

    assert result["status"] == "FAILED"
    assert result["commit_hash"] == ""
    assert "UNVERIFIED" in result["error"]


def test_pr_policy_allows_agent_branch_but_blocks_direct_branch() -> None:
    project = SimpleNamespace(
        git_enabled=True,
        git_branch_patterns=["*"],
        git_require_pr=True,
    )

    check_git_policy(project, "commit", branch="agent/instruction-1")
    with pytest.raises(PolicyBlockedError):
        check_git_policy(project, "commit", branch="main")
