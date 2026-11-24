"""Add saved report Markdown to research jobs."""

from alembic import op
import sqlalchemy as sa


revision = "0006_add_research_job_report"
down_revision = "099d9f76adbb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_jobs",
        sa.Column("report_markdown", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("research_jobs", "report_markdown")