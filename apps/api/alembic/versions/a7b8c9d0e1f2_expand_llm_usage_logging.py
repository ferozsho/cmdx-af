"""expand llm_usage with full prompt/response/error logging and project_id

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-09
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns — all nullable so existing rows survive
    op.add_column(
        "llm_usage",
        sa.Column("project_id", sa.String(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("prompt_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("system_prompt_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("response_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "llm_usage",
        sa.Column("status", sa.String(), nullable=False, server_default="success"),
    )
    op.add_column(
        "llm_usage",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("request_id", sa.String(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("temperature", sa.Float(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("json_mode", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Indexes for query performance
    op.create_index(
        "ix_llm_usage_instruction_id", "llm_usage", ["instruction_id"]
    )
    op.create_index(
        "ix_llm_usage_project_id", "llm_usage", ["project_id"]
    )
    op.create_index(
        "ix_llm_usage_provider", "llm_usage", ["provider"]
    )
    op.create_index(
        "ix_llm_usage_model", "llm_usage", ["model"]
    )
    op.create_index(
        "ix_llm_usage_status", "llm_usage", ["status"]
    )
    op.create_index(
        "ix_llm_usage_request_id", "llm_usage", ["request_id"]
    )
    op.create_index(
        "ix_llm_usage_created_at", "llm_usage", ["created_at"]
    )

    # Foreign key for project_id
    op.create_foreign_key(
        "fk_llm_usage_project_id",
        "llm_usage",
        "projects",
        ["project_id"],
        ["id"],
    )

    # Backfill project_id from instructions for existing rows
    op.execute(
        sa.text(
            """
            UPDATE llm_usage
            SET project_id = instructions.project_id
            FROM instructions
            WHERE llm_usage.instruction_id = instructions.id
              AND llm_usage.project_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_llm_usage_project_id", "llm_usage", type_="foreignkey")
    op.drop_index("ix_llm_usage_created_at", table_name="llm_usage")
    op.drop_index("ix_llm_usage_request_id", table_name="llm_usage")
    op.drop_index("ix_llm_usage_status", table_name="llm_usage")
    op.drop_index("ix_llm_usage_model", table_name="llm_usage")
    op.drop_index("ix_llm_usage_provider", table_name="llm_usage")
    op.drop_index("ix_llm_usage_project_id", table_name="llm_usage")
    op.drop_index("ix_llm_usage_instruction_id", table_name="llm_usage")
    op.drop_column("llm_usage", "json_mode")
    op.drop_column("llm_usage", "temperature")
    op.drop_column("llm_usage", "request_id")
    op.drop_column("llm_usage", "error_message")
    op.drop_column("llm_usage", "status")
    op.drop_column("llm_usage", "duration_ms")
    op.drop_column("llm_usage", "response_text")
    op.drop_column("llm_usage", "system_prompt_text")
    op.drop_column("llm_usage", "prompt_text")
    op.drop_column("llm_usage", "project_id")
