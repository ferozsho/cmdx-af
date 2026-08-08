"""Local SentenceTransformer Vector Embedder for RAG Indexing."""

from typing import Any, List, Optional


class LocalVectorEmbedder:
    """Generates dense vector embeddings locally using SentenceTransformers or fallback."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Optional[Any] = None

    def _load_model(self) -> None:
        """Lazy load SentenceTransformer model (CPU) if available."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Force CPU — avoids CUDA kernel-mismatch errors on machines
                # with GPUs unsupported by the installed torch build.
                self._model = SentenceTransformer(self.model_name, device="cpu")
            except Exception:
                self._model = "fallback"

    @staticmethod
    def _fallback_embed(text: str) -> List[float]:
        """Lightweight deterministic pseudo-embedding vector (384 dims)."""
        seed = sum(ord(c) for c in text[:100])
        return [(float((seed * i * 31) % 1000) / 1000.0) for i in range(384)]

    def embed_text(self, text: str) -> List[float]:
        """Generate 384-dimensional float vector embedding for given text."""
        self._load_model()
        if self._model != "fallback" and hasattr(self._model, "encode"):
            try:
                vector = self._model.encode(text)
                return (
                    vector.tolist()
                    if hasattr(vector, "tolist")
                    else list(vector)
                )
            except Exception:
                return self._fallback_embed(text)
        return self._fallback_embed(text)
