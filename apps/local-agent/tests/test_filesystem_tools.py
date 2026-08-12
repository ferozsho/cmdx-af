"""Independent filesystem tool coverage."""

import json
from pathlib import Path

from agentforge_local.filesystem.ops import FilesystemTools


def test_filesystem_crud_list_and_search(tmp_path: Path) -> None:
    FilesystemTools.write_file(
        str(tmp_path),
        "src/example.py",
        "first line\nneedle = 'visible'\n",
    )
    assert "needle" in FilesystemTools.read_file(
        str(tmp_path),
        "src/example.py",
    )

    FilesystemTools.update_file(
        str(tmp_path),
        "src/example.py",
        "visible",
        "updated",
    )
    entries = FilesystemTools.list_files(
        str(tmp_path),
        recursive=True,
    )
    matches = FilesystemTools.search_in_files(
        str(tmp_path),
        "UPDATED",
    )

    assert {entry["path"] for entry in entries} >= {
        "src",
        "src/example.py",
    }
    assert matches == [
        {
            "path": "src/example.py",
            "line": 2,
            "column": 11,
            "preview": "needle = 'updated'",
        }
    ]
    assert "Successfully deleted" in FilesystemTools.delete_file(
        str(tmp_path),
        "src/example.py",
    )


def test_list_and_search_exclude_hidden_and_environment_files(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env.example").write_text("SECRET=not-for-agent\n")
    (tmp_path / ".hidden.txt").write_text("needle\n")
    (tmp_path / "visible.json").write_text(json.dumps({"key": "needle"}))

    entries = FilesystemTools.list_files(str(tmp_path), recursive=True)
    matches = FilesystemTools.search_in_files(str(tmp_path), "needle")

    assert [entry["path"] for entry in entries] == ["visible.json"]
    assert [match["path"] for match in matches] == ["visible.json"]
