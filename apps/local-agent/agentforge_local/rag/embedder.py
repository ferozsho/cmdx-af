"""Local SentenceTransformer Vector Embedder for RAG Indexing."""

from typing import Any, List, Optional


class LocalVectorEmbedder:
    """Generates dense vector embeddings locally using SentenceTransformers or fallback."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Optional[Any] = None

    def _load_model(self) -> None:
        """Lazy load SentenceTransformer model if available."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                self._model = "fallback"

    def embed_text(self, text: str) -> List[float]:
        """Generate 384-dimensional float vector embedding for given text."""
        self._load_model()
        if self._model != "fallback" and hasattr(self._model, "encode"):
            vector = self._model.encode(text)
            return vector.tolist() if hasattr(vector, "tolist") else list(vector)

        # Lightweight fallback deterministic pseudo-embedding vector (384 dimensions)
        seed = sum(ord(c) for c in text[:100])
        return [(float((seed * i * 31) % 1000) / 1000.0) for i in range(384)]
