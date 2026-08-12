"""Local Git tool provenance tests."""

from pathlib import Path

import git

from agentforge_local.git.ops import GitTools


def test_commit_returns_full_content_addressed_metadata(tmp_path: Path) -> None:
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "AgentForge Test").release()
    repo.config_writer().set_value(
        "user", "email", "agentforge-git@mailinator.com"
    ).release()
    (tmp_path / "app.txt").write_text("verified\n", encoding="utf-8")

    result = GitTools.commit_changes(str(tmp_path), "test: verified provenance")

    assert result["commit_hash"] == repo.head.commit.hexsha
    assert result["tree_hash"] == repo.head.commit.tree.hexsha
    assert result["parent_hash"] == ""
    assert len(result["commit_hash"]) == 40
