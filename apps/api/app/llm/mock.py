"""Mock LLM Provider for Development and Offline Testing."""

import json
from typing import Optional
from app.llm.base import BaseLLMProvider, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Simulated LLM Provider returning structured responses without API calls."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Return simulated structured response based on prompt context."""
        if "plan" in prompt.lower() or json_mode:
            content = json.dumps({
                "summary": "Implementation plan for request",
                "complexity": "medium",
                "files_to_create": ["src/modules/payment/service.py"],
                "files_to_update": ["src/main.py"],
                "testing_strategy": ["pytest unit tests"],
                "risks": []
            })
        else:
            content = "Simulated agent response for prompt"

        return LLMResponse(
            content=content,
            prompt_tokens=150,
            completion_tokens=80,
            total_tokens=230,
            cost=0.00005,
            model=model or "mock-deepseek",
        )
