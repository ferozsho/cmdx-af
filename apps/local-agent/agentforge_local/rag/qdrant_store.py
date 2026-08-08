"""Qdrant-backed vector store for local RAG indexing."""

import hashlib
from typing import Any, Dict, List, Optional

from agentforge_local.rag.embedder import LocalVectorEmbedder


def _collection_name(workspace_path: str) -> str:
    """Stable collection name derived from the workspace path."""
    digest = hashlib.md5(workspace_path.encode()).hexdigest()[:16]
    return f"ws_{digest}"


class QdrantStore:
    """Persistent vector store on top of Qdrant with graceful fallback.

    All methods degrade to no-ops/empty results when Qdrant is unreachable,
    so the caller can fall back to the in-memory keyword indexer.
    """

    def __init__(
        self,
        workspace_path: str,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: int = 384,
        embedder: Optional[LocalVectorEmbedder] = None,
    ) -> None:
        self.workspace_path = workspace_path
        self.url = url or "http://localhost:6333"
        self.api_key = api_key
        self.vector_size = vector_size
        self.embedder = embedder or LocalVectorEmbedder()
        self._client: Optional[Any] = None

    @property
    def available(self) -> bool:
        """Whether the Qdrant client is currently usable."""
        return self._get_client() is not None

    def _get_client(self) -> Optional[Any]:
        """Lazy-create the Qdrant client; returns None when unreachable."""
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=5,
            )
            client.get_collections()  # connectivity probe
            self._client = client
            return client
        except Exception:
            return None

    def _collection(self) -> Optional[str]:
        """Return the collection name if the store is usable, else None."""
        client = self._get_client()
        if client is None:
            return None
        name = _collection_name(self.workspace_path)
        try:
            existing = [c.name for c in client.get_collections().collections]
            if name not in existing:
                from qdrant_client.models import Distance, VectorParams

                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=self.vector_size, distance=Distance.COSINE
                    ),
                )
            return name
        except Exception:
            return None

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Embed and upsert chunks; returns number stored (0 when offline)."""
        if not chunks:
            return 0
        name = self._collection()
        if name is None:
            return 0
        try:
            from qdrant_client.models import PointStruct

            client = self._get_client()
            # Batch-embed all chunks in one pass (per-chunk calls made full
            # workspace indexing take many minutes on large repos).
            vectors = self.embedder.embed_batch(
                [chunk["content"] for chunk in chunks]
            )
            points = []
            for chunk, vector in zip(chunks, vectors):
                point_id = hashlib.md5(
                    f"{chunk['file_path']}:{chunk['start_line']}".encode()
                ).hexdigest()
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "file_path": chunk["file_path"],
                            "start_line": chunk["start_line"],
                            "end_line": chunk["end_line"],
                            "content": chunk["content"],
                        },
                    )
                )
            client.upsert(collection_name=name, points=points)
            # Drop stale points (files no longer part of the index) so a
            # re-index reflects the current workspace, not old content.
            try:
                from qdrant_client.models import (
                    FieldCondition,
                    Filter,
                    FilterSelector,
                    MatchAny,
                )

                new_paths = list({c["file_path"] for c in chunks})
                client.delete(
                    collection_name=name,
                    points_selector=FilterSelector(
                        filter=Filter(
                            must_not=[
                                FieldCondition(
                                    key="file_path",
                                    match=MatchAny(any=new_paths),
                                )
                            ]
                        )
                    ),
                )
            except Exception:
                pass
            return len(points)
        except Exception:
            return 0

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Semantic vector search; returns [] when offline or no collection."""
        client = self._get_client()
        if client is None:
            return []
        name = _collection_name(self.workspace_path)
        try:
            existing = [c.name for c in client.get_collections().collections]
            if name not in existing:
                return []
            vector = self.embedder.embed_text(query)
            hits = client.search(
                collection_name=name,
                query_vector=vector,
                limit=top_k,
                with_payload=True,
            )
            results = []
            for hit in hits:
                payload = hit.payload or {}
                results.append(
                    {
                        "file_path": payload.get("file_path", ""),
                        "start_line": payload.get("start_line", 0),
                        "end_line": payload.get("end_line", 0),
                        "score": round(float(hit.score), 4),
                        "content": payload.get("content", ""),
                    }
                )
            return results
        except Exception:
            return []
