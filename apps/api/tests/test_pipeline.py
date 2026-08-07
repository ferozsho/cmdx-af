"""Unit test for Multi-Agent Orchestration Pipeline."""

import pytest
from app.agents.pipeline import PipelineOrchestrator


@pytest.mark.asyncio
async def test_pipeline_execution() -> None:
    """Verify Pipeline Orchestrator executes all sequential agents successfully."""
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.run_pipeline("ins_test_001", "Create payment feature")
    assert result["status"] == "COMPLETED"
    assert len(result["agent_runs"]) == 11
