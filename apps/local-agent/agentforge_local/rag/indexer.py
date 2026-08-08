"""Local RAG Vector Indexer & Search Engine."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List

from agentforge_local.config import local_settings
from agentforge_local.rag.chunker import CodeChunker
from agentforge_local.rag.qdrant_store import QdrantStore


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
        self._store = QdrantStore(
            str(self.workspace_path),
            url=local_settings.QDRANT_URL,
            api_key=local_settings.QDRANT_API_KEY,
        )

    def index_workspace(self) -> int:
        """Scan workspace, generate chunks, and index into vector storage."""
        self.indexed_chunks.clear()
        chunks: List[Dict[str, Any]] = []
        for item in self.workspace_path.rglob("*"):
            if item.is_file() and not any(
                part in item.parts
                for part in (".git", "node_modules", "venv")
            ):
                chunked = CodeChunker.chunk_file(item)
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

        # Persistent vector store when available; in-memory chunks always kept
        # for the keyword-search fallback path.
        self._store.upsert_chunks(chunks)
        self.indexed_chunks = chunks
        return len(self.indexed_chunks)

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

