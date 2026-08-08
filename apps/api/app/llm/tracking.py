"""LLM usage tracking wrapper that persists usage to the database."""

import asyncio
from contextvars import ContextVar
from typing import Optional

from app.llm.base import BaseLLMProvider, LLMResponse

# Set per pipeline run so background usage writes know the instruction
current_instruction_id: ContextVar[Optional[str]] = ContextVar(
    "current_instruction_id", default=None
)


class UsageTrackingProvider(BaseLLMProvider):
    """Wraps a provider and records every call to the llm_usage table."""

    def __init__(self, inner: BaseLLMProvider) -> None:
        self.inner = inner

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Delegate to the inner provider, then persist usage in background."""
        response = await self.inner.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            json_mode=json_mode,
        )
        try:
            if response.total_tokens > 0 or response.cost > 0:
                asyncio.create_task(_persist_usage(response))
        except RuntimeError:
            pass
        return response


async def _persist_usage(response: LLMResponse) -> None:
    """Persist an LLMUsage row in a fire-and-forget background task."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.llm_usage import LLMUsage

        async with AsyncSessionLocal() as session:
            session.add(
                LLMUsage(
                    instruction_id=current_instruction_id.get(),
                    provider="deepseek",
                    model=response.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens,
                    cost=response.cost,
                )
            )
            await session.commit()
    except Exception:
        pass
