"""Unit tests for Local Agent PathGuard Security."""

from pathlib import Path

import pytest

from agentforge_local.security.path_guard import PathGuard, PathGuardError


def test_path_guard_valid_path(tmp_path: Path) -> None:
    """Verify valid path inside workspace root passes validation."""
    valid = PathGuard.validate_path(tmp_path, "src/main.py")
    assert str(valid).startswith(str(tmp_path))


def test_path_guard_traversal_blocked(tmp_path: Path) -> None:
    """Verify directory traversal attempt raises PathGuardError."""
    with pytest.raises(PathGuardError):
        PathGuard.validate_path(tmp_path, "../../etc/passwd")


def test_path_guard_blocks_sibling_with_shared_prefix(tmp_path: Path) -> None:
    """A sibling such as workspace-copy is not inside workspace."""
    workspace = tmp_path / "workspace"
    sibling = tmp_path / "workspace-copy" / "secret.txt"
    with pytest.raises(PathGuardError):
        PathGuard.validate_path(workspace, sibling)


def test_path_guard_restricted_folder(tmp_path: Path) -> None:
    """Verify access to restricted folder raises PathGuardError."""
    with pytest.raises(PathGuardError):
        PathGuard.validate_path(tmp_path, ".env")


@pytest.mark.parametrize(
    "name",
    [".env.example", ".env.production", ".env.local"],
)
def test_path_guard_blocks_all_environment_file_variants(
    tmp_path: Path,
    name: str,
) -> None:
    with pytest.raises(PathGuardError):
        PathGuard.validate_path(tmp_path, name)
