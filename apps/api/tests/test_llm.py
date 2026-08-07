"""Unit test for LLM Provider Router and Mock Provider."""

import pytest
from app.llm.router import ModelRouter
from app.llm.mock import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_provider() -> None:
    """Verify Mock LLM Provider returns structured completion."""
    provider = MockLLMProvider()
    response = await provider.generate(prompt="Create implementation plan", json_mode=True)
    assert response.content is not None
    assert response.total_tokens > 0
