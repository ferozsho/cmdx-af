"""Local RAG Vector Indexer & Search Engine."""

import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentforge_local.config import local_settings
from agentforge_local.rag.chunker import CodeChunker
from agentforge_local.rag.qdrant_store import QdrantStore

# Path segments that are never indexed (virtualenvs, build caches, VCS)
_IGNORED_PARTS = frozenset(
    {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        ".next",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
)


class LocalRAGIndexer:
    """Local Codebase Indexer and Vector Search Engine.

    Indexes into a persistent Qdrant vector store when reachable, and
    transparently falls back to an in-memory keyword index otherwise.
    Instances are cached per workspace so the file watcher, rag_search, and
    rag_reindex share the same in-memory index state.
    """

    _instances: Dict[str, "LocalRAGIndexer"] = {}

    @classmethod
    def get(cls, workspace_path: str) -> "LocalRAGIndexer":
        """Return the shared indexer instance for a workspace."""
        path = str(Path(workspace_path).resolve())
        if path not in cls._instances:
            cls._instances[path] = cls(path)
        return cls._instances[path]

    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.indexed_chunks: List[Dict[str, Any]] = []
        # Chunking settings — set from the API Settings page via rag_reindex
        # args; cached on the instance so watcher/startup indexes use the
        # same values afterwards.
        self.chunk_size: Optional[int] = None
        self.chunk_overlap: Optional[int] = None
        # Live progress shared with rag_status / watcher / UI polling
        self.index_state: Dict[str, Any] = {
            "state": "idle",  # idle | indexing | complete | failed
            "total_files": 0,
            "scanned_files": 0,
            "chunks": 0,
            "current_file": None,
            "started_at": None,
            "finished_at": None,
        }
        self._store = QdrantStore(
            str(self.workspace_path),
            url=local_settings.QDRANT_URL,
            api_key=local_settings.QDRANT_API_KEY,
        )
        # Serializes index_workspace: the file watcher can burst many events
        # while an index is running; without this guard each event spawns a
        # parallel full index (multi-embedder CPU churn, interleaved state).
        self._index_lock = threading.Lock()

    def _iter_files(self):
        """Yield indexable files under the workspace (noise dirs skipped)."""
        for item in self.workspace_path.rglob("*"):
            if item.is_file() and not (set(item.parts) & _IGNORED_PARTS):
                yield item

    def index_workspace(
        self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None
    ) -> int:
        """Scan workspace, generate chunks, and index into vector storage.

        ``chunk_size``/``chunk_overlap`` (from the cloud Settings page) are
        cached on the instance when provided, so later watcher-triggered
        indexes reuse them. If an index is already running, the call is
        skipped (returns the last known chunk count) instead of starting a
        second concurrent pass.
        """
        if not self._index_lock.acquire(blocking=False):
            return int(self.index_state.get("chunks") or 0)
        try:
            return self._index_workspace_locked(chunk_size, chunk_overlap)
        finally:
            self._index_lock.release()

    def _index_workspace_locked(
        self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None
    ) -> int:
        if chunk_size is not None:
            self.chunk_size = chunk_size
        if chunk_overlap is not None:
            self.chunk_overlap = chunk_overlap
        cs = self.chunk_size
        ov = self.chunk_overlap
        self.indexed_chunks.clear()
        files = list(self._iter_files())
        self.index_state.update(
            {
                "state": "indexing",
                "total_files": len(files),
                "scanned_files": 0,
                "chunks": 0,
                "current_file": None,
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "finished_at": None,
            }
        )
        chunks: List[Dict[str, Any]] = []
        try:
            for idx, item in enumerate(files, start=1):
                self.index_state["scanned_files"] = idx
                try:
                    self.index_state["current_file"] = str(
                        item.relative_to(self.workspace_path)
                    )
                except ValueError:
                    self.index_state["current_file"] = str(item)
                try:
                    if cs is not None and ov is not None:
                        chunked = CodeChunker.chunk_file(
                            item, chunk_size=cs, overlap=ov
                        )
                    else:
                        chunked = CodeChunker.chunk_file(item)
                except Exception:
                    chunked = []
                rel_path = str(item.relative_to(self.workspace_path))
                for chunk in chunked:
                    chunk_id = hashlib.md5(
                        f"{rel_path}:{chunk['start_line']}".encode()
                    ).hexdigest()
                    chunks.append(
                        {
                            "id": chunk_id,
                            "file_path": rel_path,
                            "start_line": chunk["start_line"],
                            "end_line": chunk["end_line"],
                            "content": chunk["content"],
                        }
                    )
                self.index_state["chunks"] = len(chunks)

            # Persistent vector store when available; in-memory chunks always
            # kept for the keyword-search fallback path.
            self._store.upsert_chunks(chunks)
            self.indexed_chunks = chunks
            self.index_state.update(
                {
                    "state": "complete",
                    "scanned_files": len(files),
                    "chunks": len(chunks),
                    "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            return len(chunks)
        except Exception:
            self.index_state["state"] = "failed"
            self.index_state["finished_at"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            raise

    def status(self) -> Dict[str, Any]:
        """Return current index state + summary for live progress UI."""
        state = dict(self.index_state)
        total = int(state.get("total_files") or 0)
        scanned = int(state.get("scanned_files") or 0)
        state["progress"] = round((scanned / total) * 100, 1) if total else 0
        state["indexing"] = state.get("state") == "indexing"
        state["files_indexed"] = len(
            {c["file_path"] for c in self.indexed_chunks}
        )
        return state

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Semantic (vector) search with keyword fallback."""
        vector_results = self._store.search(query, top_k=top_k)
        if vector_results:
            return vector_results

        # Fallback: keyword search over in-memory chunks
        query_terms = set(query.lower().split())
        results: List[Dict[str, Any]] = []
        for chunk in self.indexed_chunks:
            content_lower = chunk["content"].lower()
            matches = sum(1 for term in query_terms if term in content_lower)
            if matches > 0:
                score = round(matches / len(query_terms), 2)
                results.append(
                    {
                        "file_path": chunk["file_path"],
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "score": score,
                        "content": chunk["content"],
                    }
                )
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

