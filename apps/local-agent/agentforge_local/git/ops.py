"""Local Agent Git Operations Module."""

from pathlib import Path
from typing import Any, Dict, List
import git
from agentforge_local.security.path_guard import PathGuard


class GitTools:
    """Git Repository Tools Operating on Local Workspace."""

    @classmethod
    def get_status(cls, workspace_root: str) -> Dict[str, Any]:
        """Get repository status, branch info, uncommitted and unpushed files."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)

        branch_name = "HEAD"
        try:
            branch_name = repo.active_branch.name
        except Exception:
            pass

        untracked = repo.untracked_files
        modified = []
        try:
            modified = [item.a_path for item in repo.index.diff(None) if item.a_path]
        except Exception:
            pass

        staged = []
        try:
            if len(repo.heads) > 0:
                staged = [item.a_path for item in repo.index.diff("HEAD") if item.a_path]
        except Exception:
            pass

        unpushed_files: List[str] = []
        try:
            active_branch = repo.active_branch
            tracking = active_branch.tracking_branch()
            if tracking:
                diff_unpushed = active_branch.commit.diff(tracking.commit)
                for item in diff_unpushed:
                    if item.a_path:
                        unpushed_files.append(item.a_path)
                    if item.b_path:
                        unpushed_files.append(item.b_path)
                unpushed_files = sorted(list(set(unpushed_files)))
        except Exception:
            pass

        return {
            "branch": branch_name,
            "is_dirty": repo.is_dirty(),
            "untracked_files": untracked,
            "modified_files": modified,
            "staged_files": staged,
            "unpushed_files": unpushed_files,
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
    def get_log(cls, workspace_root: str, max_count: int = 20) -> list:
        """Get recent commit log."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        commits = []
        try:
            for c in repo.iter_commits(max_count=max_count):
                commits.append({
                    "hash": c.hexsha,
                    "message": c.message.strip(),
                    "author": str(c.author),
                    "time": c.committed_datetime.isoformat(),
                    "files": len(c.stats.files) if c.stats else 0,
                })
        except Exception:
            pass
        return commits

    @classmethod
    def rollback(cls, workspace_root: str, commit_hash: str) -> str:
        """Hard reset workspace to specified commit hash."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        repo.git.reset("--hard", commit_hash)
        return f"Successfully reset repository to '{commit_hash}'"
