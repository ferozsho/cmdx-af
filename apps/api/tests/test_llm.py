"""Unit test for LLM Provider Router and Mock Provider."""

import json

import httpx
import pytest

from app.llm.base import LLMStructuredOutputError
from app.llm.deepseek import DeepSeekProvider
from app.llm.mock import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_provider() -> None:
    """Verify Mock LLM Provider returns structured completion."""
    provider = MockLLMProvider()
    response = await provider.generate(prompt="Create implementation plan", json_mode=True)
    assert response.content is not None
    assert response.total_tokens > 0


@pytest.mark.asyncio
async def test_deepseek_retries_transient_failure_and_tracks_cost() -> None:
    """Transient upstream failures retry and valid JSON is parsed strictly."""
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {
                    "prompt_tokens": 1_000_000,
                    "completion_tokens": 1_000_000,
                    "total_tokens": 2_000_000,
                },
            },
        )

    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://provider.invalid/v1",
        transport=httpx.MockTransport(handler),
        retry_base_seconds=0,
    )
    response = await provider.generate(prompt="return json", json_mode=True)

    assert requests == 2
    assert response.content == {"ok": True}
    assert response.cost == 0.42


@pytest.mark.asyncio
async def test_deepseek_rejects_invalid_structured_output() -> None:
    """JSON mode never silently returns malformed unstructured text."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "not json"}}]},
        )

    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://provider.invalid/v1",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LLMStructuredOutputError):
        await provider.generate(prompt="return json", json_mode=True)


@pytest.mark.asyncio
async def test_deepseek_streams_typed_sse_chunks() -> None:
    """DeepSeek streaming exposes text and final usage through one interface."""
    events = [
        {"model": "deepseek-chat", "choices": [{"delta": {"content": "hel"}}]},
        {"model": "deepseek-chat", "choices": [{"delta": {"content": "lo"}}]},
        {
            "model": "deepseek-chat",
            "choices": [],
            "usage": {
                "prompt_tokens": 2,
                "completion_tokens": 1,
                "total_tokens": 3,
            },
        },
    ]
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    body += "data: [DONE]\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, text=body)

    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://provider.invalid/v1",
        transport=httpx.MockTransport(handler),
    )
    chunks = [chunk async for chunk in provider.stream(prompt="say hello")]

    assert "".join(chunk.content for chunk in chunks) == "hello"
    assert chunks[-1].done is True
    assert chunks[-1].total_tokens == 3
