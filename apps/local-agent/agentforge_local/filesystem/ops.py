"""Local Agent Filesystem Tool Implementation."""

import os
from pathlib import Path
from typing import Any, Dict, List
from agentforge_local.security.path_guard import PathGuard
from agentforge_local.security.secret_redactor import SecretRedactor


class FilesystemTools:
    """Safe Local Workstation Filesystem Operations."""

    @classmethod
    def read_file(cls, workspace_root: str, path: str) -> str:
        """Read text content from a file inside authorized workspace root."""
        target = PathGuard.validate_path(workspace_root, path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: '{path}'")
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return SecretRedactor.redact(content)

    @classmethod
    def write_file(cls, workspace_root: str, path: str, content: str) -> str:
        """Write content to a file, creating parent directories if needed."""
        target = PathGuard.validate_path(workspace_root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{path}'"

    @classmethod
    def update_file(cls, workspace_root: str, path: str, old_str: str, new_str: str) -> str:
        """Replace old_str with new_str in specified file."""
        target = PathGuard.validate_path(workspace_root, path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: '{path}'")
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        if old_str not in content:
            raise ValueError(f"String to replace not found in '{path}'")
        updated = content.replace(old_str, new_str, 1)
        with open(target, "w", encoding="utf-8") as f:
            f.write(updated)
        return f"Successfully updated '{path}'"

    @classmethod
    def delete_file(cls, workspace_root: str, path: str) -> str:
        """Delete file inside workspace root."""
        target = PathGuard.validate_path(workspace_root, path)
        if target.is_file():
            target.unlink()
            return f"Successfully deleted '{path}'"
        raise FileNotFoundError(f"File not found: '{path}'")

    @classmethod
    def get_project_tree(cls, workspace_root: str, max_depth: int = 4) -> Dict[str, Any]:
        """Build directory tree representation of the workspace."""
        root = Path(workspace_root).resolve()

        def _build_tree(dir_path: Path, current_depth: int) -> Dict[str, Any]:
            if current_depth > max_depth:
                return {"type": "dir", "truncated": True}
            children: List[Dict[str, Any]] = []
            for item in sorted(dir_path.iterdir()):
                if item.name.startswith(".") or item.name in ("node_modules", "__pycache__", "venv"):
                    continue
                if item.is_dir():
                    children.append({
                        "name": item.name,
                        "type": "dir",
                        "children": _build_tree(item, current_depth + 1).get("children", [])
                    })
                else:
                    children.append({"name": item.name, "type": "file", "size": item.stat().st_size})
            return {"name": dir_path.name, "type": "dir", "children": children}

        return _build_tree(root, 1)
