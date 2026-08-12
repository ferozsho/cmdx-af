"""Unit test for LLM Provider Router and Mock Provider."""

import json

import httpx
import pytest

from app.llm.base import (
    LLMStructuredOutputError,
    parse_json_content,
)
from app.llm.deepseek import DeepSeekProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai import OpenAIProvider


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


def test_parse_json_content_accepts_plain_object() -> None:
    """A clean JSON object parses directly."""
    assert parse_json_content('{"ok": true}') == {"ok": True}


def test_parse_json_content_strips_markdown_fences() -> None:
    """Code-fenced JSON (```json ... ```) still parses."""
    raw = '```json\n{"files": [{"path": "a.py", "content": "x"}]}\n```'
    assert parse_json_content(raw) == {
        "files": [{"path": "a.py", "content": "x"}]
    }


def test_parse_json_content_tolerates_trailing_prose() -> None:
    """Trailing prose after the object (a DeepSeek json_object quirk) parses."""
    raw = '{"ok": true}\n\nI generated the requested files for you.'
    assert parse_json_content(raw) == {"ok": True}


def test_parse_json_content_ignores_braces_inside_strings() -> None:
    """Braces inside embedded code strings do not break object balancing."""
    content = (
        '{"files": [{"path": "models.py", "content": "class A:\\n'
        '    field = {\\"a\\": 1}"}]}'
        "\n\nDone."
    )
    assert parse_json_content(content)["files"][0]["path"] == "models.py"


def test_parse_json_content_rejects_non_object_json() -> None:
    """A bare array is not a valid structured-output object."""
    with pytest.raises(LLMStructuredOutputError):
        parse_json_content("[1, 2, 3]")


def test_parse_json_content_rejects_empty_content() -> None:
    """Empty provider content is a structured-output contract violation."""
    with pytest.raises(LLMStructuredOutputError):
        parse_json_content("   ")


@pytest.mark.asyncio
async def test_deepseek_sends_max_tokens_in_payload() -> None:
    """DeepSeek requests carry an explicit generous max_tokens cap."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    provider = DeepSeekProvider(
        api_key="test-key",
        base_url="https://provider.invalid/v1",
        transport=httpx.MockTransport(handler),
    )
    await provider.generate(prompt="return json", json_mode=True)
    assert seen["payload"]["max_tokens"] >= 8192


@pytest.mark.asyncio
async def test_openai_caps_max_tokens_at_model_ceiling() -> None:
    """OpenAI max_tokens never exceeds the selected model's output cap."""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["max_tokens"] <= 4096
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://p.invalid/v1",
        transport=httpx.MockTransport(handler),
    )
    await provider.generate(
        prompt="return json", model="gpt-3.5-turbo", json_mode=True
    )


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
