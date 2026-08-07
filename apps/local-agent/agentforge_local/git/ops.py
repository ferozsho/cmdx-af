"""Local Agent Git Operations Module."""

from pathlib import Path
from typing import Any, Dict, List
import git
from agentforge_local.security.path_guard import PathGuard


class GitTools:
    """Git Repository Tools Operating on Local Workspace."""

    @classmethod
    def get_status(cls, workspace_root: str) -> Dict[str, Any]:
        """Get repository status and branch info."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        return {
            "branch": repo.active_branch.name,
            "is_dirty": repo.is_dirty(),
            "untracked_files": repo.untracked_files,
            "modified_files": [item.a_path for item in repo.index.diff(None)],
        }

    @classmethod
    def create_and_checkout_branch(cls, workspace_root: str, branch_name: str) -> str:
        """Create and checkout new agent isolation branch."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        if branch_name in repo.branches:
            repo.git.checkout(branch_name)
        else:
            repo.git.checkout("-b", branch_name)
        return f"Checked out branch '{branch_name}'"

    @classmethod
    def commit_changes(cls, workspace_root: str, message: str) -> str:
        """Stage all changes and commit with structured message."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        repo.git.add("-A")
        commit = repo.index.commit(message)
        return commit.hexsha

    @classmethod
    def get_diff(cls, workspace_root: str) -> str:
        """Get git diff output."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        return repo.git.diff("HEAD~1") if len(repo.heads) > 0 else repo.git.diff()

    @classmethod
    def rollback(cls, workspace_root: str, commit_hash: str) -> str:
        """Hard reset workspace to specified commit hash."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        repo.git.reset("--hard", commit_hash)
        return f"Successfully reset repository to '{commit_hash}'"
