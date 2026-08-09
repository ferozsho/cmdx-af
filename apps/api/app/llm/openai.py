"""OpenAI API Provider Implementation."""

import json
import httpx
from typing import Optional
from app.core.config import get_setting
from app.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider (GPT-4o, GPT-4 Turbo, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or get_setting("OPENAI_API_KEY", "")
        self.base_url = base_url or get_setting(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )

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

        payload: dict = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=120.0) as client:
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

        parsed_content = choice
        if json_mode and isinstance(choice, str):
            try:
                parsed_content = json.loads(choice)
            except (json.JSONDecodeError, TypeError):
                pass

        return LLMResponse(
            content=parsed_content,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=tot_tokens,
            cost=round(cost, 6),
            model=target_model,
            provider_name="openai",
        )
