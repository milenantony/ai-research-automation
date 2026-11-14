
"""baseline for existing research jobs table

Revision ID: baseline_jobs_001
Revises:
"""

from typing import Sequence, Union

from alembic import op


revision: str = "baseline_jobs_001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create research_jobs if it does not already exist."""

    op.execute("""
        CREATE TABLE IF NOT EXISTS research_jobs (
            id UUID NOT NULL,
            topic VARCHAR(500) NOT NULL,
            status VARCHAR(30) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT research_jobs_pkey PRIMARY KEY (id)
        )
    """)


def downgrade() -> None:
    """Remove research_jobs."""

    op.drop_table("research_jobs")
