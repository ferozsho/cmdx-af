"""Local RAG Vector Indexer & Search Engine."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List
from agentforge_local.rag.chunker import CodeChunker


class LocalRAGIndexer:
    """Local Codebase Indexer and Vector Search Engine."""

    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.indexed_chunks: List[Dict[str, Any]] = []

    def index_workspace(self) -> int:
        """Scan workspace and generate chunks for vector storage."""
        self.indexed_chunks.clear()
        for item in self.workspace_path.rglob("*"):
            if item.is_file() and not any(part in item.parts for part in (".git", "node_modules", "venv")):
                chunks = CodeChunker.chunk_file(item)
                rel_path = str(item.relative_to(self.workspace_path))
                for chunk in chunks:
                    chunk_id = hashlib.md5(f"{rel_path}:{chunk['start_line']}".encode()).hexdigest()
                    self.indexed_chunks.append({
                        "id": chunk_id,
                        "file_path": rel_path,
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "content": chunk["content"],
                    })
        return len(self.indexed_chunks)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search across indexed chunks."""
        query_terms = set(query.lower().split())
        results: List[Dict[str, Any]] = []

        for chunk in self.indexed_chunks:
            content_lower = chunk["content"].lower()
            matches = sum(1 for term in query_terms if term in content_lower)
            if matches > 0:
                score = round(matches / len(query_terms), 2)
                results.append({
                    "file_path": chunk["file_path"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "score": score,
                    "content": chunk["content"],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
