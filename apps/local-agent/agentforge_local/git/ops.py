"""Local Agent Git Operations Module."""

import subprocess
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
    def commit_changes(cls, workspace_root: str, message: str) -> Dict[str, str]:
        """Stage changes and return content-addressed commit metadata."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        repo.git.add("-A")
        commit = repo.index.commit(message)
        parents = commit.parents
        return {
            "commit_hash": commit.hexsha,
            "tree_hash": commit.tree.hexsha,
            "parent_hash": parents[0].hexsha if parents else "",
        }

    @classmethod
    def get_diff(cls, workspace_root: str) -> str:
        """Get git diff output."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        return repo.git.diff("HEAD~1") if len(repo.heads) > 0 else repo.git.diff()

    @classmethod
    def show_file(cls, workspace_root: str, file_path: str) -> str:
        """Get file content as it exists in HEAD (diff baseline)."""
        root = PathGuard.validate_path(workspace_root, ".")
        if ":" in file_path or ".." in file_path:
            raise ValueError("Invalid file path for git baseline lookup")
        repo = git.Repo(root)
        try:
            return repo.git.show(f"HEAD:{file_path}")
        except git.exc.GitCommandError:
            # Untracked/new file — no baseline exists
            return ""

    @classmethod
    def get_log(cls, workspace_root: str, max_count: int = 20) -> list:
        """Get recent commit log with file change summaries."""
        root = PathGuard.validate_path(workspace_root, ".")
        repo = git.Repo(root)
        commits = []
        try:
            for c in repo.iter_commits(max_count=max_count):
                entry: dict = {
                    "hash": c.hexsha,
                    "message": c.message.strip(),
                    "author": str(c.author),
                    "time": c.committed_datetime.isoformat(),
                    "files_changed": 0,
                    "insertions": 0,
                    "deletions": 0,
                    "changed_files": [],
                }
                if c.stats and c.stats.files:
                    entry["files_changed"] = len(c.stats.files)
                    entry["insertions"] = c.stats.total.get("insertions", 0)
                    entry["deletions"] = c.stats.total.get("deletions", 0)
                    entry["changed_files"] = [
                        {
                            "path": fname,
                            "insertions": s.get("insertions", 0),
                            "deletions": s.get("deletions", 0),
                        }
                        for fname, s in c.stats.files.items()
                    ]
                commits.append(entry)
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

    @classmethod
    def create_pull_request(
        cls,
        workspace_root: str,
        branch_name: str,
        title: str,
        body: str = "",
        base: str = "main",
    ) -> Dict[str, str]:
        """Create a pull request from the agent branch via the GitHub CLI.

        Requires the ``gh`` CLI to be installed and authenticated on the
        workstation. Returns the pull request URL on success.
        """
        root = PathGuard.validate_path(workspace_root, ".")
        cmd = [
            "gh",
            "pr",
            "create",
            "--base",
            base,
            "--head",
            branch_name,
            "--title",
            title,
            "--body",
            body,
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "GitHub CLI ('gh') is not installed or not on PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "GitHub CLI timed out creating the pull request."
            ) from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"GitHub CLI failed to create PR: {detail[:2000]}")
        return {
            "pr_url": (proc.stdout or "").strip(),
            "branch": branch_name,
            "base": base,
        }
