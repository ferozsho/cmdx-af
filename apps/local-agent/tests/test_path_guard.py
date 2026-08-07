"""Unit tests for Local Agent PathGuard Security."""

import pytest
from pathlib import Path
from agentforge_local.security.path_guard import PathGuard, PathGuardError


def test_path_guard_valid_path(tmp_path: Path) -> None:
    """Verify valid path inside workspace root passes validation."""
    valid = PathGuard.validate_path(tmp_path, "src/main.py")
    assert str(valid).startswith(str(tmp_path))


def test_path_guard_traversal_blocked(tmp_path: Path) -> None:
    """Verify directory traversal attempt raises PathGuardError."""
    with pytest.raises(PathGuardError):
        PathGuard.validate_path(tmp_path, "../../etc/passwd")


def test_path_guard_restricted_folder(tmp_path: Path) -> None:
    """Verify access to restricted folder raises PathGuardError."""
    with pytest.raises(PathGuardError):
        PathGuard.validate_path(tmp_path, ".env")
