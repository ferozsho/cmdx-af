"""Google Gemini API Provider Implementation."""

import json
import httpx
from typing import Optional
from app.core.config import get_setting
from app.llm.base import BaseLLMProvider, LLMResponse


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API Provider (Gemini 2.5 Pro, Flash, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or get_setting("GEMINI_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Execute content generation via Google Gemini API."""
        target_model = model or get_setting(
            "GEMINI_CHAT_MODEL", "gemini-2.5-pro"
        )

        # Build Gemini-format contents
        contents = []
        if system_prompt:
            contents.append(
                {"role": "user", "parts": [{"text": f"System: {system_prompt}"}]}
            )
            contents.append(
                {"role": "model", "parts": [{"text": "Understood."}]}
            )
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        generation_config: dict = {"temperature": temperature}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        payload = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        headers = {"x-goog-api-key": self.api_key}

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{target_model}:generateContent"
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")

        content_obj = candidates[0].get("content", {})
        parts = content_obj.get("parts", [])
        choice = parts[0].get("text", "") if parts else ""

        usage = data.get("usageMetadata", {})
        p_tokens = usage.get("promptTokenCount", 0)
        c_tokens = usage.get("candidatesTokenCount", 0)
        tot_tokens = usage.get("totalTokenCount", p_tokens + c_tokens)

        # Gemini pricing ($1.25/1M prompt, $10/1M completion for Pro)
        cost = (p_tokens * 0.00000125) + (c_tokens * 0.000010)

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
            provider_name="gemini",
        )
