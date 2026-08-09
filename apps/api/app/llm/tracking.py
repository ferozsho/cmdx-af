"""LLM usage tracking wrapper that persists usage to the database."""

import asyncio
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from app.llm.base import BaseLLMProvider, LLMResponse

# Set per pipeline run so background usage writes know the instruction
current_instruction_id: ContextVar[Optional[str]] = ContextVar(
    "current_instruction_id", default=None
)
# Set per pipeline run so background usage writes know the project
current_project_id: ContextVar[Optional[str]] = ContextVar(
    "current_project_id", default=None
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
        start_time = time.time()
        request_id = str(uuid.uuid4())
        try:
            response = await self.inner.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                json_mode=json_mode,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                asyncio.create_task(
                    _persist_usage(
                        response=response,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        duration_ms=duration_ms,
                        request_id=request_id,
                        temperature=temperature,
                        json_mode=json_mode,
                    )
                )
            except RuntimeError:
                pass
            return response
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                asyncio.create_task(
                    _persist_error(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=model,
                        error_message=str(exc),
                        duration_ms=duration_ms,
                        request_id=request_id,
                        temperature=temperature,
                        json_mode=json_mode,
                    )
                )
            except RuntimeError:
                pass
            raise


async def _persist_usage(
    response: LLMResponse,
    prompt: str,
    system_prompt: Optional[str] = None,
    duration_ms: int = 0,
    request_id: str = "",
    temperature: Optional[float] = None,
    json_mode: bool = False,
) -> None:
    """Persist a successful LLMUsage row in a fire-and-forget background task."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.llm_usage import LLMUsage

        async with AsyncSessionLocal() as session:
            session.add(
                LLMUsage(
                    instruction_id=current_instruction_id.get(),
                    project_id=current_project_id.get(),
                    provider=response.provider_name,
                    model=response.model,
                    prompt_text=prompt,
                    system_prompt_text=system_prompt,
                    response_text=(
                        str(response.content)
                        if response.content
                        else None
                    ),
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens,
                    cost=response.cost,
                    duration_ms=duration_ms,
                    status="success",
                    request_id=request_id,
                    temperature=temperature,
                    json_mode=json_mode,
                )
            )
            await session.commit()
    except Exception:
        pass


async def _persist_error(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    error_message: str = "",
    duration_ms: int = 0,
    request_id: str = "",
    temperature: Optional[float] = None,
    json_mode: bool = False,
) -> None:
    """Persist a failed LLM call in a fire-and-forget background task."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.llm_usage import LLMUsage

        async with AsyncSessionLocal() as session:
            session.add(
                LLMUsage(
                    instruction_id=current_instruction_id.get(),
                    project_id=current_project_id.get(),
                    provider="unknown",
                    model=model or "unknown",
                    prompt_text=prompt,
                    system_prompt_text=system_prompt,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost=0.0,
                    duration_ms=duration_ms,
                    status="error",
                    error_message=error_message,
                    request_id=request_id,
                    temperature=temperature,
                    json_mode=json_mode,
                )
            )
            await session.commit()
    except Exception:
        pass
