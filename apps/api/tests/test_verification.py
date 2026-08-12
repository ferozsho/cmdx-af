"""Tests for durable, secret-safe verification evidence."""

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.instruction import Instruction
from app.models.project import Project
from app.models.user import User
from app.models.verification_run import VerificationRun
from app.services.verification import record_verification, sanitize_evidence


def test_sanitize_evidence_redacts_credentials_and_bounds_output() -> None:
    raw = (
        "Authorization: Bearer signed-token\n"
        "API_KEY=top-secret token: another-secret password=hunter2\n"
        + ("x" * 5000)
    )

    safe = sanitize_evidence(raw)

    assert "signed-token" not in safe
    assert "top-secret" not in safe
    assert "another-secret" not in safe
    assert "hunter2" not in safe
    assert len(safe) == 4000


@pytest.mark.asyncio
async def test_record_verification_persists_digests_not_command_arguments() -> None:
    suffix = uuid.uuid4().hex
    user_id = f"verification-user-{suffix}"
    project_id = f"verification-project-{suffix}"
    instruction_id = f"verification-instruction-{suffix}"
    async with AsyncSessionLocal() as session:
        session.add(
            User(
                id=user_id,
                email=f"verification-{suffix}@mailinator.com",
                hashed_password="unused-test-hash",
            )
        )
        session.add(Project(id=project_id, user_id=user_id, name="Verification"))
        session.add(
            Instruction(
                id=instruction_id,
                project_id=project_id,
                user_id=user_id,
                prompt="Verify",
                status="RUNNING",
            )
        )
        await session.commit()

    try:
        await record_verification(
            project_id=project_id,
            instruction_id=instruction_id,
            category="security",
            command=["python", "-m", "bandit", "--token=do-not-store"],
            result={
                "success": False,
                "exit_code": 1,
                "duration_seconds": 1.25,
                "output": "token=do-not-store-output finding detected",
            },
        )
        async with AsyncSessionLocal() as session:
            record = await session.scalar(
                select(VerificationRun).where(
                    VerificationRun.instruction_id == instruction_id
                )
            )
        assert record is not None
        assert record.executable == "python"
        assert record.status == "FAILED"
        assert "do-not-store" not in record.output_excerpt
        assert len(record.command_digest) == 64
        assert len(record.output_digest) == 64
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(VerificationRun).where(
                    VerificationRun.instruction_id == instruction_id
                )
            )
            await session.execute(
                delete(Instruction).where(Instruction.id == instruction_id)
            )
            await session.execute(delete(Project).where(Project.id == project_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
