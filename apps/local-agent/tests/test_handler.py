"""Security tests for local tool request dispatch."""

from pathlib import Path

import pytest
from agentforge_protocol import ToolRequest

from agentforge_local.execution.runner import ExecutionRunner
from agentforge_local.handler import ToolHandler


class EmptyWorkspaceManager:
    """Workspace registry with no authorized roots."""

    def get_workspace_path(self, workspace_id: str) -> None:
        return None


class FixtureWorkspaceManager:
    """Workspace registry that resolves one test root."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def get_workspace_path(self, workspace_id: str) -> str | None:
        return str(self.root) if workspace_id == "workspace-test" else None


@pytest.mark.asyncio
async def test_existing_raw_path_is_not_an_authorized_workspace(
    tmp_path: Path,
) -> None:
    """A cloud request cannot promote an arbitrary host path to a workspace."""
    request = ToolRequest(
        request_id="request-1",
        job_id="job-1",
        workspace_id=str(tmp_path),
        tool_name="get_project_tree",
        arguments={},
    )

    result = await ToolHandler(EmptyWorkspaceManager()).handle_request(request)

    assert result.success is False
    assert "not authorized" in (result.error or "")


@pytest.mark.asyncio
async def test_mutating_tool_requires_authorization() -> None:
    """A compromised caller cannot send an unattested mutation."""
    request = ToolRequest(
        request_id="request-2",
        job_id="job-2",
        workspace_id="workspace-2",
        tool_name="run_command",
        arguments={"cmd_array": ["pytest", "-q"]},
    )

    result = await ToolHandler(EmptyWorkspaceManager()).handle_request(request)

    assert result.success is False
    assert "no policy or approval authorization" in (result.error or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "expected_task"),
    [
        ("run_tests", "tests"),
        ("run_linter", "linter"),
        ("run_formatter", "formatter"),
        ("run_type_check", "type_check"),
        ("run_build", "build"),
    ],
)
async def test_named_execution_tools_dispatch_to_restricted_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    expected_task: str,
) -> None:
    """Each protocol tool maps to its matching restricted task category."""
    calls: list[tuple[str, str, list[str] | None, int]] = []

    def fake_run_task(
        workspace_root: str,
        task: str,
        cmd_array: list[str] | None = None,
        timeout: int = 60,
    ) -> dict:
        calls.append((workspace_root, task, cmd_array, timeout))
        return {"exit_code": 0}

    monkeypatch.setattr(ExecutionRunner, "run_task", fake_run_task)
    request = ToolRequest(
        request_id=f"request-{tool_name}",
        job_id="job-test",
        workspace_id="workspace-test",
        tool_name=tool_name,
        arguments={"timeout": 30},
        authorization_id="policy:test",
    )

    result = await ToolHandler(FixtureWorkspaceManager(tmp_path)).handle_request(
        request
    )

    assert result.success is True
    assert calls == [(str(tmp_path), expected_task, None, 30)]
