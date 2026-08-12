"""Unit tests for RAG indexer noise-directory ignore filter."""

from pathlib import Path

from agentforge_local.rag.indexer import _IGNORED_PARTS, LocalRAGIndexer


class OfflineStore:
    """Unit-test store that prevents writes to the live Qdrant service."""

    def upsert_chunks(self, chunks):
        return 0

    def search(self, query, top_k=5):
        return []


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
    indexer._store = OfflineStore()
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
    indexer._store = OfflineStore()
    files = list(indexer._iter_files())
    rel = {str(f.relative_to(tmp_path)) for f in files}

    assert "apps/web/page.tsx" in rel
    assert "apps/web/.next/bundle.js" not in rel


def test_index_workspace_skips_when_busy(tmp_path: Path) -> None:
    """Concurrent watcher bursts must not spawn parallel index passes.

    When an index is already running, index_workspace returns the last
    known chunk count immediately instead of starting a second pass.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n")

    indexer = LocalRAGIndexer(str(tmp_path))
    indexer._store = OfflineStore()
    # Simulate an in-flight index by holding the internal lock
    assert indexer._index_lock.acquire(blocking=False)
    try:
        result = indexer.index_workspace(chunk_size=50, chunk_overlap=10)
        assert result == 0  # skipped — last known chunks is 0
        assert indexer.index_state["state"] != "indexing"
        assert len(indexer.indexed_chunks) == 0
    finally:
        indexer._index_lock.release()

    # After release, a normal index runs to completion
    count = indexer.index_workspace(chunk_size=50, chunk_overlap=10)
    assert count >= 1
    assert indexer.index_state["state"] == "complete"


def test_keyword_retrieval_ranks_relevant_file_with_line_metadata(
    tmp_path: Path,
) -> None:
    (tmp_path / "payments.py").write_text(
        "def refund_transaction(payment_id):\n"
        "    return reverse_payment(payment_id)\n"
    )
    (tmp_path / "weather.py").write_text(
        "def current_temperature(city):\n"
        "    return weather_service(city)\n"
    )
    indexer = LocalRAGIndexer(str(tmp_path))
    indexer._store = OfflineStore()

    assert indexer.index_workspace(chunk_size=1, chunk_overlap=0) == 4
    results = indexer.search("refund transaction payment", top_k=2)

    assert results
    assert results[0]["file_path"] == "payments.py"
    assert results[0]["start_line"] == 1
    assert results[0]["end_line"] == 1
    assert results[0]["score"] == 1.0
