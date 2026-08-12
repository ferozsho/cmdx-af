"""OpenAI API Provider Implementation."""

from typing import Optional

import httpx

from app.core.config import (
    DEFAULT_OPENAI_MAX_TOKENS,
    get_setting,
)
from app.llm.base import BaseLLMProvider, LLMResponse, parse_json_content

# Per-model output token ceilings enforced by the OpenAI API.
_MODEL_MAX_OUTPUT_TOKENS = {
    "gpt-3.5-turbo": 4096,
    "gpt-4-turbo": 16384,
    "gpt-4o": 16384,
}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider (GPT-4o, GPT-4 Turbo, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or get_setting("OPENAI_API_KEY", "")
        self.base_url = base_url or get_setting(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        self.transport = transport

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Execute chat completion request to OpenAI API."""
        target_model = model or get_setting("OPENAI_CHAT_MODEL", "gpt-4o")
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Cap the configured max_tokens at the selected model's ceiling so a
        # legacy model (e.g. gpt-3.5-turbo, max 4096) never gets a 400.
        model_cap = _MODEL_MAX_OUTPUT_TOKENS.get(target_model, 16384)
        max_tokens = min(
            int(get_setting("OPENAI_MAX_TOKENS", DEFAULT_OPENAI_MAX_TOKENS)),
            model_cap,
        )

        payload: dict = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(
            timeout=120.0, transport=self.transport
        ) as client:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            res.raise_for_status()
            data = res.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)
        tot_tokens = usage.get("total_tokens", p_tokens + c_tokens)

        # GPT-4o pricing ($2.50/1M prompt, $10/1M completion)
        cost = (p_tokens * 0.0000025) + (c_tokens * 0.000010)

        parsed_content = parse_json_content(choice) if json_mode else choice

        return LLMResponse(
            content=parsed_content,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=tot_tokens,
            cost=round(cost, 6),
            model=target_model,
            provider_name="openai",
        )
