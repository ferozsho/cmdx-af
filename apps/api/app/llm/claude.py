"""Anthropic Claude API Provider Implementation."""

from typing import Optional

import httpx

from app.core.config import get_setting
from app.llm.base import BaseLLMProvider, LLMResponse, parse_json_content


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API Provider (Claude 3.5 Sonnet, Opus, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or get_setting("CLAUDE_API_KEY", "")
        self.api_version = "2023-06-01"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Execute message via Anthropic Claude Messages API."""
        target_model = model or get_setting(
            "CLAUDE_CHAT_MODEL", "claude-3-5-sonnet-20241022"
        )

        # Claude doesn't have native json_mode — prepend instruction
        effective_prompt = prompt
        if json_mode:
            effective_prompt = (
                "You must respond with valid JSON only. "
                "Do not include any explanatory text outside the JSON object.\n\n"
                + prompt
            )
        messages = [{"role": "user", "content": effective_prompt}]

        payload: dict = {
            "model": target_model,
            "max_tokens": 4096,
            "messages": messages,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            res.raise_for_status()
            data = res.json()

        content_blocks = data.get("content", [])
        choice = ""
        for block in content_blocks:
            if block.get("type") == "text":
                choice += block.get("text", "")

        usage = data.get("usage", {})
        p_tokens = usage.get("input_tokens", 0)
        c_tokens = usage.get("output_tokens", 0)
        tot_tokens = p_tokens + c_tokens

        # Claude pricing ($3/1M prompt, $15/1M completion for Sonnet)
        cost = (p_tokens * 0.000003) + (c_tokens * 0.000015)

        parsed_content = parse_json_content(choice) if json_mode else choice

        return LLMResponse(
            content=parsed_content,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=tot_tokens,
            cost=round(cost, 6),
            model=target_model,
            provider_name="claude",
        )
