"""Local Agent Subprocess Execution Tool."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List

from agentforge_local.security.path_guard import PathGuard
from agentforge_local.security.secret_redactor import SecretRedactor


class ExecutionRunner:
    """Safely executes whitelisted development commands in local workspace."""

    WHITELIST_COMMANDS = {
        "pytest",
        "npm",
        "pnpm",
        "yarn",
        "ruff",
        "mypy",
        "eslint",
        "tsc",
        "python",
        "node",
        "black",
        "prettier",
    }
    TASK_DEFAULTS = {
        "tests": ["pytest", "-q"],
        "linter": ["ruff", "check", "."],
        "formatter": ["ruff", "format", "."],
        "type_check": ["mypy", "."],
        "build": ["npm", "run", "build"],
    }
    TASK_EXECUTABLES = {
        "tests": {"pytest", "npm", "pnpm", "yarn"},
        "linter": {"ruff", "eslint", "npm", "pnpm", "yarn"},
        "formatter": {"ruff", "black", "prettier", "npm", "pnpm", "yarn"},
        "type_check": {"mypy", "tsc", "npm", "pnpm", "yarn"},
        "build": {"npm", "pnpm", "yarn", "python"},
    }
    TASK_SCRIPTS = {
        "tests": {"test", "tests"},
        "linter": {"lint", "lint:check"},
        "formatter": {"format", "format:check"},
        "type_check": {"typecheck", "type-check", "check-types"},
        "build": {"build"},
    }
    MAX_OUTPUT_CHARS = 1_000_000
    SAFE_ENV_KEYS = frozenset(
        {
            "PATH",
            "HOME",
            "TMPDIR",
            "LANG",
            "LC_ALL",
            "TERM",
            "CI",
            "NO_COLOR",
            "NODE_OPTIONS",
            "PYTHONPATH",
            "VIRTUAL_ENV",
        }
    )

    @classmethod
    def _safe_environment(cls) -> Dict[str, str]:
        """Prevent cloud/device credentials leaking into repository commands."""
        return {
            key: value
            for key, value in os.environ.items()
            if key in cls.SAFE_ENV_KEYS
        }

    @classmethod
    def run_command(
        cls,
        workspace_root: str,
        cmd_array: List[str],
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Execute command array in non-shell subprocess array inside workspace root."""
        root = PathGuard.validate_path(workspace_root, ".")

        if not cmd_array or cmd_array[0] not in cls.WHITELIST_COMMANDS:
            raise ValueError(
                f"Command '{cmd_array[0] if cmd_array else ''}' is not in "
                "the whitelisted commands list"
            )

        start_time = time.time()
        effective_command = [
            sys.executable if cmd_array[0] == "python" else cmd_array[0],
            *cmd_array[1:],
        ]
        with (
            tempfile.TemporaryFile(
                mode="w+t", encoding="utf-8"
            ) as stdout_file,
            tempfile.TemporaryFile(
                mode="w+t", encoding="utf-8"
            ) as stderr_file,
        ):
            process = subprocess.Popen(
                effective_command,
                cwd=root,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                shell=False,
                env=cls._safe_environment(),
                start_new_session=True,
            )
            try:
                exit_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds",
                    "duration_seconds": timeout,
                }
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout = stdout_file.read(cls.MAX_OUTPUT_CHARS)
            stderr = stderr_file.read(cls.MAX_OUTPUT_CHARS)
        duration = time.time() - start_time
        return {
            "exit_code": exit_code,
            "stdout": SecretRedactor.redact(stdout),
            "stderr": SecretRedactor.redact(stderr),
            "duration_seconds": round(duration, 2),
        }

    @classmethod
    def run_task(
        cls,
        workspace_root: str,
        task: str,
        cmd_array: List[str] | None = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Run a command constrained to one development-task category."""
        if task not in cls.TASK_DEFAULTS:
            raise ValueError(f"Unknown execution task '{task}'")
        command = list(cmd_array or cls.TASK_DEFAULTS[task])
        executable = command[0] if command else ""
        if executable not in cls.TASK_EXECUTABLES[task]:
            raise ValueError(
                f"Command '{executable}' is not permitted for {task}"
            )
        if executable in {"npm", "pnpm", "yarn"}:
            script_index = 2 if len(command) > 2 and command[1] == "run" else 1
            script = command[script_index] if len(command) > script_index else ""
            if script not in cls.TASK_SCRIPTS[task]:
                raise ValueError(
                    f"Package script '{script}' is not permitted for {task}"
                )
        return cls.run_command(
            workspace_root,
            command,
            timeout=timeout,
        )
