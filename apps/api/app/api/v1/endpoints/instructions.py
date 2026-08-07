"""Instruction Submission and Agent Execution Endpoints."""

import asyncio
import uuid
from typing import Any, List
from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.pipeline import PipelineOrchestrator
from app.services.sse_broadcaster import broadcaster

router = APIRouter()


class InstructionSubmit(BaseModel):
    """Instruction submission request payload."""

    prompt: str


class InstructionResponse(BaseModel):
    """Instruction response schema."""

    id: str
    project_id: str
    prompt: str
    status: str


@router.post(
    "/projects/{project_id}/instructions",
    response_model=InstructionResponse,
)
async def submit_instruction(project_id: str, data: InstructionSubmit) -> Any:
    """Submit natural language development instruction and trigger Agent Pipeline."""
    ins_id = f"ins_{uuid.uuid4().hex[:8]}"

    async def _run_async_pipeline() -> None:
        orchestrator = PipelineOrchestrator()

        async def _event_cb(agent_name: str, status: str, msg: str) -> None:
            await broadcaster.broadcast(
                project_id,
                {
                    "instruction_id": ins_id,
                    "agent_name": agent_name,
                    "status": status,
                    "message": msg,
                },
            )

        await orchestrator.run_pipeline(ins_id, data.prompt, event_callback=_event_cb)

    asyncio.create_task(_run_async_pipeline())

    return InstructionResponse(
        id=ins_id,
        project_id=project_id,
        prompt=data.prompt,
        status="RUNNING",
    )
