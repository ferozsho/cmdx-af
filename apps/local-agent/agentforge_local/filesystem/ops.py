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
    def get_project_tree(cls, workspace_root: str, max_depth: int = 10) -> Dict[str, Any]:
        """Build directory tree representation of the workspace."""
        root = Path(workspace_root).resolve()

        IGNORED_DIRS = {
            "node_modules",
            "__pycache__",
            "venv",
            ".venv",
            ".git",
            ".next",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }

        def _build_tree(dir_path: Path, current_depth: int) -> Dict[str, Any]:
            if current_depth > max_depth:
                return {"type": "dir", "truncated": True}
            children: List[Dict[str, Any]] = []
            try:
                items = sorted(dir_path.iterdir())
            except Exception:
                return {"name": dir_path.name, "type": "dir", "children": []}

            for item in items:
                if item.name.startswith(".") and item.name not in (".env.example",):
                    continue
                if item.name in IGNORED_DIRS:
                    continue
                if item.is_dir():
                    children.append({
                        "name": item.name,
                        "type": "dir",
                        "children": _build_tree(item, current_depth + 1).get("children", [])
                    })
                else:
                    try:
                        size = item.stat().st_size
                    except Exception:
                        size = 0
                    children.append({"name": item.name, "type": "file", "size": size})
            return {"name": dir_path.name, "type": "dir", "children": children}

        return _build_tree(root, 1)

    @classmethod
    def validate_path(cls, path: str) -> Dict[str, Any]:
        """Validate a directory path on this host machine.

        Returns the same structured shape as the cloud API's
        ValidatePathResponse so the frontend can render it directly.
        """
        raw = (path or "").strip()
        if not raw:
            return {
                "valid": False,
                "exists": False,
                "warnings": ["Path is empty."],
            }
        try:
            target = Path(raw).expanduser().resolve()
        except (OSError, RuntimeError) as e:
            return {
                "valid": False,
                "exists": False,
                "warnings": [f"Cannot resolve path: {e}"],
            }

        exists = target.exists()
        is_dir = target.is_dir()
        readable = os.access(target, os.R_OK) if exists else False
        writable = os.access(target, os.W_OK) if exists else False
        git = bool(is_dir and (target / ".git").is_dir())

        warnings: List[str] = []
        if not exists:
            warnings.append(f"Directory does not exist: {target}")
        elif not is_dir:
            warnings.append(f"Path is not a directory: {target}")
        if exists and not readable:
            warnings.append("Directory is not readable")
        if exists and not writable:
            warnings.append("Directory is not writable")
        if is_dir and not git:
            warnings.append(
                "No Git repository detected. "
                "Git versioning will be unavailable."
            )

        detected: List[str] = []
        files_count = 0
        dirs_count = 0
        project_name = None
        if is_dir:
            detected = _detect_stack(target)
            files_count, dirs_count = _count_entries(target)
            project_name = target.name

        valid = bool(exists and is_dir and readable and writable)
        return {
            "valid": valid,
            "exists": exists,
            "is_directory": is_dir,
            "readable": readable,
            "writable": writable,
            "git_repository": git,
            "detected_stack": detected,
            "project_name": project_name,
            "files_count": files_count,
            "directories_count": dirs_count,
            "warnings": warnings,
        }


# Lightweight tech-stack detection (mirrors the cloud API markers)
STACK_MARKERS: Dict[str, List[str]] = {
    "Python": ["requirements.txt", "pyproject.toml", "setup.py"],
    "FastAPI": ["fastapi"],
    "Django": ["manage.py"],
    "Flask": ["flask"],
    "Next.js": ["next.config.js", "next.config.mjs", "next.config.ts"],
    "React": ["react"],
    "Node.js": ["package.json"],
    "TypeScript": ["tsconfig.json"],
    "PHP": ["composer.json", "index.php", "version.php"],
    "Moodle": ["version.php", "config.php", "lib/moodlelib.php"],
    "PostgreSQL": ["psycopg2", "asyncpg"],
    "MySQL": ["mysqlclient", "pymysql", "mysql2"],
    "Redis": ["redis"],
    "Docker": ["Dockerfile", "docker-compose.yml"],
    "MongoDB": ["mongoengine", "pymongo", "motor"],
}


def _detect_stack(project_path: Path) -> List[str]:
    """Scan project directory and detect technologies."""
    detected: List[str] = []
    try:
        root_files = {f.name for f in project_path.iterdir() if f.is_file()}
        all_files_lower = {
            f.name.lower() for f in project_path.rglob("*") if f.is_file()
        }
        for tech, markers in STACK_MARKERS.items():
            if any(
                m in root_files or m in all_files_lower for m in markers
            ):
                detected.append(tech)
    except Exception:
        pass
    return detected


def _count_entries(project_path: Path) -> tuple:
    """Count files and directories (capped for performance)."""
    files_count = 0
    dirs_count = 0
    try:
        for item in project_path.rglob("*"):
            if ".git" in item.parts:
                continue
            if item.is_dir():
                dirs_count += 1
            elif item.is_file():
                files_count += 1
            if files_count + dirs_count > 5000:
                break
    except Exception:
        pass
    return files_count, dirs_count
