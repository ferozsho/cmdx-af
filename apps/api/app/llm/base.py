"""Abstract Base Class for LLM Providers."""

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Structured LLM Response Schema.

    When json_mode is requested, content is auto-parsed from JSON string
    to dict by the provider, so agents can use .get() directly.
    """

    content: Union[str, Dict[str, Any]]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    provider_name: str = ""


class LLMStreamChunk(BaseModel):
    """One provider-independent streaming completion event."""

    content: str = ""
    done: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider_name: str = ""


class LLMStructuredOutputError(ValueError):
    """Raised when a provider violates a requested structured-output contract."""


def parse_json_content(content: Any) -> Dict[str, Any]:
    """Parse a provider response as a JSON object or fail explicitly."""
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise LLMStructuredOutputError("Structured output must be a JSON object")
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise LLMStructuredOutputError(
            "Provider returned invalid JSON for a structured-output request"
        ) from exc
    if not isinstance(parsed, dict):
        raise LLMStructuredOutputError("Structured output must be a JSON object")
    return parsed


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers (DeepSeek, OpenAI, Mock, etc.)."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate text or JSON completion from prompt."""
        pass

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a completion, with a safe one-chunk fallback for providers."""
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            json_mode=json_mode,
        )
        content = (
            json.dumps(response.content)
            if isinstance(response.content, dict)
            else response.content
        )
        yield LLMStreamChunk(
            content=content,
            done=True,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            model=response.model,
            provider_name=response.provider_name,
        )
