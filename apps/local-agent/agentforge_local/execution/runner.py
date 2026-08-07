"""Local Agent Subprocess Execution Tool."""

import subprocess
import time
from pathlib import Path
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
    }

    @classmethod
    def run_command(cls, workspace_root: str, cmd_array: List[str], timeout: int = 60) -> Dict[str, Any]:
        """Execute command array in non-shell subprocess array inside workspace root."""
        root = PathGuard.validate_path(workspace_root, ".")

        if not cmd_array or cmd_array[0] not in cls.WHITELIST_COMMANDS:
            raise ValueError(
                f"Command '{cmd_array[0] if cmd_array else ''}' is not in whitelisted commands list"
            )

        start_time = time.time()
        try:
            res = subprocess.run(
                cmd_array,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            duration = time.time() - start_time
            return {
                "exit_code": res.returncode,
                "stdout": SecretRedactor.redact(res.stdout),
                "stderr": SecretRedactor.redact(res.stderr),
                "duration_seconds": round(duration, 2),
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "duration_seconds": timeout,
            }
