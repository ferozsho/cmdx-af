"""Qdrant vector-store correctness tests using an in-memory engine."""

from typing import Any

from qdrant_client import QdrantClient

from agentforge_local.rag.qdrant_store import QdrantStore, _collection_name


class SemanticTestEmbedder:
    """Small deterministic embedder for predictable semantic ranking."""

    @staticmethod
    def embed_text(text: str) -> list[float]:
        normalized = text.casefold()
        if any(term in normalized for term in ("refund", "return", "money")):
            return [1.0, 0.0, 0.0]
        if any(term in normalized for term in ("weather", "temperature")):
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


def _store(workspace_path: str) -> QdrantStore:
    store = QdrantStore(
        workspace_path,
        vector_size=3,
        embedder=SemanticTestEmbedder(),
    )
    store._client = QdrantClient(location=":memory:")
    return store


def test_vector_search_returns_semantic_match_and_line_metadata() -> None:
    store = _store("/workspace/vector-search")
    chunks: list[dict[str, Any]] = [
        {
            "file_path": "payments.py",
            "start_line": 20,
            "end_line": 24,
            "content": "def refund_transaction(): return_money()",
        },
        {
            "file_path": "weather.py",
            "start_line": 3,
            "end_line": 6,
            "content": "def temperature_forecast(): weather()",
        },
    ]

    assert store.upsert_chunks(chunks) == 2
    results = store.search("return customer money", top_k=1)

    assert results[0]["file_path"] == "payments.py"
    assert results[0]["start_line"] == 20
    assert results[0]["end_line"] == 24
    assert results[0]["score"] == 1.0


def test_empty_reindex_removes_stale_collection() -> None:
    store = _store("/workspace/empty-reindex")
    chunk = {
        "file_path": "old.py",
        "start_line": 1,
        "end_line": 1,
        "content": "refund money",
    }
    assert store.upsert_chunks([chunk]) == 1
    collection_name = _collection_name(store.workspace_path)
    assert collection_name in {
        item.name for item in store._client.get_collections().collections
    }

    assert store.upsert_chunks([]) == 0
    assert collection_name not in {
        item.name for item in store._client.get_collections().collections
    }
