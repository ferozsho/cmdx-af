"""Project-level policy enforcement for Git and Filesystem operations.

These helpers are called at the API layer (agents + endpoints) to enforce
per-project authorization policies BEFORE dispatching tool calls to the
local agent. The local agent itself remains project-unaware.
"""

import fnmatch
from typing import List

from fastapi import HTTPException


class PolicyBlockedError(HTTPException):
    """Raised when a project policy blocks an operation."""

    def __init__(self, status_code: int = 403, detail: str = "") -> None:
        super().__init__(status_code=status_code, detail=detail)


def _match_branch(branch: str, patterns: List[str]) -> bool:
    """Check whether *branch* matches any glob pattern in *patterns*.

    An empty patterns list is treated as "allow all".
    """
    if not patterns:
        return True
    return any(fnmatch.fnmatch(branch, p) for p in patterns)


def check_git_policy(
    project: object,
    operation: str,
    branch: str | None = None,
) -> None:
    """Raise HTTPException(403) if the project's Git policy blocks *operation*.

    Args:
        project: A Project ORM instance with git_* attributes.
        operation: One of 'read', 'branch_create', 'commit', 'rollback'.
        branch: The branch name (required for 'branch_create' and 'commit').

    Raises:
        PolicyBlockedError: When the operation is blocked by policy.
    """
    # Check top-level enable/disable
    if not getattr(project, "git_enabled", True):
        raise PolicyBlockedError(
            status_code=403,
            detail="Git operations are disabled for this project.",
        )

    patterns: list = getattr(project, "git_branch_patterns", ["*"]) or ["*"]

    # Read-only operations (status, log, show_file) always allowed if git_enabled
    if operation in ("read",):
        return

    # Branch creation check
    if operation == "branch_create":
        if branch and not _match_branch(branch, patterns):
            raise PolicyBlockedError(
                status_code=403,
                detail=(
                    f"Branch '{branch}' does not match allowed patterns: "
                    f"{patterns}"
                ),
            )

    # Commit check. PR-required projects may commit only to isolated agent
    # branches; merging into a protected branch remains a human/CI action.
    if operation == "commit":
        if branch and not _match_branch(branch, patterns):
            raise PolicyBlockedError(
                status_code=403,
                detail=(
                    f"Branch '{branch}' does not match allowed patterns: "
                    f"{patterns}"
                ),
            )
        if (
            getattr(project, "git_require_pr", False)
            and branch
            and not branch.startswith("agent/")
        ):
            raise PolicyBlockedError(
                status_code=403,
                detail=(
                    "PR-required projects only permit AI commits on "
                    "isolated 'agent/' branches."
                ),
            )

    # Rollback is a mutating operation
    if operation == "rollback":
        return  # Always allowed if git_enabled (no branch check needed)

    # Pull request head branches must match the allowed branch patterns.
    if operation == "pull_request":
        if branch and not _match_branch(branch, patterns):
            raise PolicyBlockedError(
                status_code=403,
                detail=(
                    f"Branch '{branch}' does not match allowed patterns: "
                    f"{patterns}"
                ),
            )


def check_fs_policy(project: object, operation: str) -> None:
    """Raise HTTPException(403) if the project's Filesystem policy blocks *operation*.

    Args:
        project: A Project ORM instance with fs_* attributes.
        operation: One of 'read', 'write', 'delete'.

    Raises:
        PolicyBlockedError: When the operation is blocked by policy.
    """
    if operation == "read" and not getattr(project, "fs_read_enabled", True):
        raise PolicyBlockedError(
            status_code=403,
            detail="Filesystem read access is disabled for this project.",
        )
    if operation == "write" and not getattr(project, "fs_write_enabled", True):
        raise PolicyBlockedError(
            status_code=403,
            detail="Filesystem write access is disabled for this project.",
        )
    if operation == "delete" and not getattr(project, "fs_delete_enabled", True):
        raise PolicyBlockedError(
            status_code=403,
            detail="Filesystem delete access is disabled for this project.",
        )
