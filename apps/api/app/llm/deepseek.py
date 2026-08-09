"""DeepSeek API Provider Implementation."""

import json
import httpx
from typing import Optional
from app.core.config import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_CHAT_MODEL,
    get_setting,
)
from app.llm.base import BaseLLMProvider, LLMResponse


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API Provider for Reasoning and Coding."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or get_setting("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or get_setting(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Execute chat completion request to DeepSeek API."""
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
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=60.0) as client:
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

        # DeepSeek pricing estimation ($0.14 per 1M prompt, $0.28 per 1M completion)
        cost = (p_tokens * 0.00000014) + (c_tokens * 0.00000028)

        # Parse JSON content when json_mode is requested so agents can use
        # .get() directly on the content field without manual parsing.
        parsed_content = choice
        if json_mode and isinstance(choice, str):
            try:
                parsed_content = json.loads(choice)
            except (json.JSONDecodeError, TypeError):
                pass  # Keep raw string if parsing fails

        return LLMResponse(
            content=parsed_content,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=tot_tokens,
            cost=round(cost, 6),
            model=target_model,
            provider_name="deepseek",
        )
