from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


research_summary_papers = Table(
    "research_summary_papers",
    Base.metadata,
    Column(
        "summary_id",
        UUID(as_uuid=True),
        ForeignKey("research_summaries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "paper_id",
        UUID(as_uuid=True),
        ForeignKey("research_papers.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    ),
    Column("position", Integer, nullable=False),
    UniqueConstraint(
        "summary_id",
        "position",
        name="uq_research_summary_papers_summary_position",
    ),
    CheckConstraint(
        "position >= 1",
        name="ck_research_summary_papers_positive_position",
    ),
)