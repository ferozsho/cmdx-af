"""Abstract Base Class for LLM Providers."""

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel

_MAX_JSON_RECOVERY_LENGTH = 200_000


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


def _strip_code_fences(content: str) -> str:
    """Remove markdown code fences that wrap a JSON payload."""
    lines = content.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_first_json_object(content: str) -> Dict[str, Any]:
    """Extract the first balanced JSON object from a string.

    Tolerates providers that append prose after the object or get cut off
    once the object has closed. Strings and escapes are tracked so braces
    inside embedded code (e.g. Python dicts in file content) are ignored.
    """
    start = content.find("{")
    if start == -1:
        raise LLMStructuredOutputError(
            "Structured output must be a JSON object"
        )
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                parsed = json.loads(content[start : index + 1])
                if isinstance(parsed, dict):
                    return parsed
                break
    raise LLMStructuredOutputError(
        "Structured output must be a JSON object"
    )


def parse_json_content(content: Any) -> Dict[str, Any]:
    """Parse a provider response as a JSON object or fail explicitly.

    The fast path is a direct ``json.loads``. If that fails, the parser
    strips markdown code fences and finally scans for the first balanced
    JSON object, so providers that wrap output in fences or append trailing
    prose (a known DeepSeek ``json_object`` quirk) still yield a dict.
    """
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise LLMStructuredOutputError(
            "Structured output must be a JSON object"
        )
    text = content.strip().lstrip("\ufeff")
    if not text:
        raise LLMStructuredOutputError(
            "Provider returned empty content for a structured-output request"
        )
    candidates = [text]
    if text.startswith("```"):
        candidates.append(_strip_code_fences(text))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    # Fall back to scanning for the first balanced object so responses that
    # carry trailing prose still parse.
    if len(text) <= _MAX_JSON_RECOVERY_LENGTH:
        return _extract_first_json_object(text)
    raise LLMStructuredOutputError(
        "Provider returned invalid JSON for a structured-output request"
    )


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
