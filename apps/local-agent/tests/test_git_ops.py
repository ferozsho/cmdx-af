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


def test_create_pull_request_invokes_gh_cli(tmp_path: Path, monkeypatch) -> None:
    """PR creation shells out to the GitHub CLI with the right arguments."""
    import subprocess

    captured: dict = {}

    class _FakeProc:
        returncode = 0
        stdout = "https://github.com/acme/repo/pull/7\n"
        stderr = ""

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs.get("cwd")
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = GitTools.create_pull_request(
        str(tmp_path),
        "agent/ins_abc",
        "Fix payment module",
        body="Fixes #1",
        base="main",
    )
    assert result["pr_url"] == "https://github.com/acme/repo/pull/7"
    assert result["branch"] == "agent/ins_abc"
    assert captured["cmd"][:5] == ["gh", "pr", "create", "--base", "main"]
    assert captured["cmd"][5:9] == [
        "--head",
        "agent/ins_abc",
        "--title",
        "Fix payment module",
    ]
    assert "--body" in captured["cmd"]
    assert captured["cwd"] == tmp_path


def test_create_pull_request_fails_on_gh_error(tmp_path: Path, monkeypatch) -> None:
    """A non-zero GitHub CLI exit surfaces as a RuntimeError with detail."""
    import subprocess

    class _FakeProc:
        returncode = 1
        stdout = ""
        stderr = "gh: not authenticated\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FakeProc())
    try:
        GitTools.create_pull_request(str(tmp_path), "agent/ins_abc", "Title")
    except RuntimeError as exc:
        assert "not authenticated" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
