"""Add RAG readiness gate marker to projects.

Revision ID: o5a6b7c8d9e0
Revises: n0a1b2c3d4e5
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o5a6b7c8d9e0"
down_revision: Union[str, None] = "n0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add projects.rag_indexed_at (NULL = index required, access gated)."""
    op.add_column(
        "projects",
        sa.Column("rag_indexed_at", sa.DateTime(), nullable=True),
    )
    # Projects that already ran a re-index job before this migration are
    # considered indexed so existing workspaces are not locked out.
    op.execute(
        """
        UPDATE projects
        SET rag_indexed_at = bg.finished_at
        FROM (
            SELECT DISTINCT ON (project_id) project_id, finished_at
            FROM background_jobs
            WHERE job_type = 'RAG_REINDEX'
              AND status = 'COMPLETED'
            ORDER BY project_id, created_at DESC
        ) AS bg
        WHERE projects.id = bg.project_id
        """
    )


def downgrade() -> None:
    """Drop the RAG readiness marker."""
    op.drop_column("projects", "rag_indexed_at")
