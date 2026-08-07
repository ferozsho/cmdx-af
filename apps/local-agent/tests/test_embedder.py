"""Unit test for LocalVectorEmbedder."""

from agentforge_local.rag.embedder import LocalVectorEmbedder


def test_embed_text_returns_vector() -> None:
    """Verify vector embedder returns 384 dimensional list of floats."""
    embedder = LocalVectorEmbedder()
    vector = embedder.embed_text("def process_payment(amount): pass")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert isinstance(vector[0], float)
