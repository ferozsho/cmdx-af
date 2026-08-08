"""Unit tests for RAG indexer noise-directory ignore filter."""

from pathlib import Path

from agentforge_local.rag.indexer import _IGNORED_PARTS, LocalRAGIndexer


def test_ignored_parts_cover_noise_dirs() -> None:
    """The ignore set includes VCS, venvs, and build caches."""
    for part in (
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".next",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    ):
        assert part in _IGNORED_PARTS, f"{part} should be ignored"


def test_iter_files_skips_ignored_dirs(tmp_path: Path) -> None:
    """_iter_files yields real source files but skips venv/cache noise."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("y = 2\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("z = 3\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"\x00")

    indexer = LocalRAGIndexer(str(tmp_path))
    files = list(indexer._iter_files())
    rel = {str(f.relative_to(tmp_path)) for f in files}

    assert "src/main.py" in rel
    assert ".venv/lib.py" not in rel
    assert "node_modules/pkg.js" not in rel
    assert "__pycache__/mod.cpython-311.pyc" not in rel


def test_iter_files_includes_nested_ignored(tmp_path: Path) -> None:
    """Nested ignored dirs (e.g. apps/web/.next) are also skipped."""
    (tmp_path / "apps" / "web").mkdir(parents=True)
    (tmp_path / "apps" / "web" / ".next").mkdir()
    (tmp_path / "apps" / "web" / ".next" / "bundle.js").write_text("x\n")
    (tmp_path / "apps" / "web" / "page.tsx").write_text("export default\n")

    indexer = LocalRAGIndexer(str(tmp_path))
    files = list(indexer._iter_files())
    rel = {str(f.relative_to(tmp_path)) for f in files}

    assert "apps/web/page.tsx" in rel
    assert "apps/web/.next/bundle.js" not in rel
