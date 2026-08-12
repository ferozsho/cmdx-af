"""LLM usage tracking wrapper that persists usage to the database."""

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextvars import ContextVar
from typing import Optional

from app.llm.base import BaseLLMProvider, LLMResponse, LLMStreamChunk
from app.services.verification import sanitize_evidence

logger = logging.getLogger(__name__)

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
        """Delegate to the provider and durably persist its usage record."""
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
            await _persist_usage(
                response=response,
                prompt=prompt,
                system_prompt=system_prompt,
                duration_ms=duration_ms,
                request_id=request_id,
                temperature=temperature,
                json_mode=json_mode,
            )
            return response
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            await _persist_error(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                error_message=str(exc),
                duration_ms=duration_ms,
                request_id=request_id,
                temperature=temperature,
                json_mode=json_mode,
            )
            raise

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Delegate streaming and persist one consolidated usage record."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        content_parts: list[str] = []
        final_chunk = LLMStreamChunk(model=model or "unknown")
        try:
            async for chunk in self.inner.stream(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                json_mode=json_mode,
            ):
                content_parts.append(chunk.content)
                final_chunk = chunk
                yield chunk
            response = LLMResponse(
                content="".join(content_parts),
                prompt_tokens=final_chunk.prompt_tokens,
                completion_tokens=final_chunk.completion_tokens,
                total_tokens=final_chunk.total_tokens,
                cost=0.0,
                model=final_chunk.model,
                provider_name=final_chunk.provider_name,
            )
            await _persist_usage(
                response=response,
                prompt=prompt,
                system_prompt=system_prompt,
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                temperature=temperature,
                json_mode=json_mode,
            )
        except Exception as exc:
            await _persist_error(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                error_message=str(exc),
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                temperature=temperature,
                json_mode=json_mode,
            )
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
    """Persist a successful LLM usage row without failing the LLM call."""
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
                    prompt_text=sanitize_evidence(prompt, limit=12000),
                    system_prompt_text=(
                        sanitize_evidence(system_prompt, limit=8000)
                        if system_prompt
                        else None
                    ),
                    response_text=(
                        sanitize_evidence(str(response.content), limit=12000)
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
        logger.exception("Unable to persist successful LLM usage record")


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
    """Persist a failed LLM call without masking the provider exception."""
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
                    prompt_text=sanitize_evidence(prompt, limit=12000),
                    system_prompt_text=(
                        sanitize_evidence(system_prompt, limit=8000)
                        if system_prompt
                        else None
                    ),
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost=0.0,
                    duration_ms=duration_ms,
                    status="error",
                    error_message=sanitize_evidence(error_message, limit=2000),
                    request_id=request_id,
                    temperature=temperature,
                    json_mode=json_mode,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Unable to persist failed LLM usage record")
