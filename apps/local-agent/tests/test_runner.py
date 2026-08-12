"""Security and resource-boundary tests for command execution."""

from pathlib import Path

import pytest

from agentforge_local.execution.runner import ExecutionRunner


def test_runner_does_not_inherit_device_credentials(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("DEVICE_TOKEN", "must-not-reach-child")

    result = ExecutionRunner.run_command(
        str(tmp_path),
        [
            "python",
            "-c",
            "import os; print(os.getenv('DEVICE_TOKEN', 'absent'))",
        ],
    )

    assert result["exit_code"] == 0
    assert result["stdout"].strip() == "absent"


def test_runner_bounds_captured_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ExecutionRunner, "MAX_OUTPUT_CHARS", 100)

    result = ExecutionRunner.run_command(
        str(tmp_path),
        ["python", "-c", "print('x' * 1000)"],
    )

    assert result["exit_code"] == 0
    assert len(result["stdout"]) == 100


def test_task_runner_accepts_only_matching_task_commands(tmp_path: Path) -> None:
    accepted = ExecutionRunner.run_task(
        str(tmp_path),
        "tests",
        ["pytest", "--version"],
    )

    assert accepted["exit_code"] == 0
    with pytest.raises(ValueError, match="not permitted for tests"):
        ExecutionRunner.run_task(
            str(tmp_path),
            "tests",
            ["python", "-c", "print('not a test')"],
        )
    with pytest.raises(ValueError, match="not permitted for tests"):
        ExecutionRunner.run_task(
            str(tmp_path),
            "tests",
            ["npm", "run", "build"],
        )
