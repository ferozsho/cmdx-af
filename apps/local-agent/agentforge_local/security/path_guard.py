"""Path Guard Module for Strict Workspace Path Isolation."""

from pathlib import Path


class PathGuardError(Exception):
    """Exception raised when path traversal or unauthorized access occurs."""

    pass


class PathGuard:
    """Validates that requested file paths stay strictly inside workspace roots."""

    BLOCKED_PATTERNS = {
        ".env",
        ".env.example",
        ".env.local",
        ".git",
        "id_rsa",
        "id_ed25519",
        "id_dsa",
        "authorized_keys",
        ".aws",
        ".ssh",
    }

    @classmethod
    def is_blocked_part(cls, part: str) -> bool:
        """Return whether a path component is sensitive by policy."""
        return part in cls.BLOCKED_PATTERNS or part.startswith(".env.")

    @classmethod
    def validate_path(cls, workspace_root: str | Path, requested_path: str | Path) -> Path:
        """Resolve and validate that requested_path is inside workspace_root."""
        root = Path(workspace_root).resolve()
        target = (
            (root / requested_path).resolve()
            if not Path(requested_path).is_absolute()
            else Path(requested_path).resolve()
        )

        if not target.is_relative_to(root):
            raise PathGuardError(
                f"Path traversal blocked: '{requested_path}' resolves outside "
                f"workspace root '{workspace_root}'"
            )

        for part in target.parts:
            if cls.is_blocked_part(part):
                raise PathGuardError(f"Access to sensitive file or folder '{part}' is restricted")

        return target
