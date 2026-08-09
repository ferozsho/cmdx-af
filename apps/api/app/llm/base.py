"""Abstract Base Class for LLM Providers."""

from abc import ABC, abstractmethod
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
