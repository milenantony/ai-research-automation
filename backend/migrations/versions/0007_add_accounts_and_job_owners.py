"""Add PaperX accounts, sessions, and research job ownership."""

from alembic import op
import sqlalchemy as sa


revision = "0007_add_accounts_and_job_owners"
down_revision = "0006_add_research_job_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
    )
    op.create_table(
        "account_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "account_id", sa.Uuid(), sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_account_sessions_account_id", "account_sessions", ["account_id"])
    op.add_column("research_jobs", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_research_jobs_owner_id", "research_jobs", "accounts", ["owner_id"], ["id"]
    )
    op.create_index("ix_research_jobs_owner_id", "research_jobs", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_research_jobs_owner_id", table_name="research_jobs")
    op.drop_constraint("fk_research_jobs_owner_id", "research_jobs", type_="foreignkey")
    op.drop_column("research_jobs", "owner_id")
    op.drop_table("account_sessions")
    op.drop_table("accounts")
