"""DeepSeek API Provider Implementation."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Optional

import httpx

from app.core.config import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_CHAT_MODEL,
    get_setting,
)
from app.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMStreamChunk,
    parse_json_content,
)

_RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API Provider for Reasoning and Coding."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_base_seconds: float = 0.25,
    ) -> None:
        self.api_key = api_key or get_setting("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or get_setting(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        )
        self.transport = transport
        self.retry_base_seconds = retry_base_seconds

    def _request(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        json_mode: bool,
        *,
        stream: bool = False,
    ) -> tuple[str, dict, dict]:
        """Build a DeepSeek-compatible chat-completion request."""
        target_model = model or get_setting(
            "DEEPSEEK_CHAT_MODEL", DEFAULT_DEEPSEEK_CHAT_MODEL
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if stream:
            payload["stream_options"] = {"include_usage": True}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return target_model, headers, payload

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
            return True
        return isinstance(exc, httpx.HTTPStatusError) and (
            exc.response.status_code in _RETRYABLE_STATUS_CODES
        )

    async def _sleep_before_retry(self, attempt: int) -> None:
        await asyncio.sleep(self.retry_base_seconds * (2**attempt))

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Execute chat completion request to DeepSeek API."""
        target_model, headers, payload = self._request(
            prompt,
            system_prompt,
            model,
            temperature,
            json_mode,
        )
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    timeout=60.0, transport=self.transport
                ) as client:
                    res = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    res.raise_for_status()
                    data = res.json()
                break
            except Exception as exc:
                if attempt == 2 or not self._is_retryable(exc):
                    raise
                await self._sleep_before_retry(attempt)

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)
        tot_tokens = usage.get("total_tokens", p_tokens + c_tokens)

        # DeepSeek pricing estimation ($0.14 per 1M prompt, $0.28 per 1M completion)
        cost = (p_tokens * 0.00000014) + (c_tokens * 0.00000028)

        # Parse JSON content when json_mode is requested so agents can use
        # .get() directly on the content field without manual parsing.
        parsed_content = parse_json_content(choice) if json_mode else choice

        return LLMResponse(
            content=parsed_content,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=tot_tokens,
            cost=round(cost, 6),
            model=target_model,
            provider_name="deepseek",
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream typed chunks from DeepSeek's OpenAI-compatible SSE API."""
        target_model, headers, payload = self._request(
            prompt,
            system_prompt,
            model,
            temperature,
            json_mode,
            stream=True,
        )
        for attempt in range(3):
            emitted = False
            try:
                async with httpx.AsyncClient(
                    timeout=60.0, transport=self.transport
                ) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data:"):
                                continue
                            raw = line[5:].strip()
                            if not raw or raw == "[DONE]":
                                continue
                            event = json.loads(raw)
                            usage = event.get("usage") or {}
                            choices = event.get("choices") or []
                            content = ""
                            if choices:
                                content = choices[0].get("delta", {}).get(
                                    "content", ""
                                ) or ""
                            chunk = LLMStreamChunk(
                                content=content,
                                done=bool(usage),
                                prompt_tokens=usage.get("prompt_tokens", 0),
                                completion_tokens=usage.get(
                                    "completion_tokens", 0
                                ),
                                total_tokens=usage.get("total_tokens", 0),
                                model=event.get("model", target_model),
                                provider_name="deepseek",
                            )
                            if chunk.content or chunk.done:
                                emitted = True
                                yield chunk
                return
            except Exception as exc:
                if emitted or attempt == 2 or not self._is_retryable(exc):
                    raise
                await self._sleep_before_retry(attempt)
