"""Workspace Directory Registry Manager."""

import json
from pathlib import Path
from typing import Dict, Optional


class WorkspaceManager:
    """Manages authorized local workspace paths on the workstation."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.config_dir / "workspaces.json"
        self._workspaces: Dict[str, str] = self._load()

    def _load(self) -> Dict[str, str]:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(self._workspaces, f, indent=2)

    def add_workspace(self, workspace_id: str, path: str) -> str:
        """Register an authorized workspace path."""
        resolved_path = str(Path(path).resolve())
        self._workspaces[workspace_id] = resolved_path
        self._save()
        return resolved_path

    def get_workspace_path(self, workspace_id: str) -> Optional[str]:
        """Get path for workspace ID if authorized."""
        return self._workspaces.get(workspace_id)

    def remove_workspace(self, workspace_id: str) -> bool:
        """Remove workspace from registry."""
        if workspace_id in self._workspaces:
            del self._workspaces[workspace_id]
            self._save()
            return True
        return False

    def list_workspaces(self) -> Dict[str, str]:
        """List all authorized workspace paths."""
        return dict(self._workspaces)
