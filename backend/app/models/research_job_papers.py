from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


research_job_papers = Table(
    "research_job_papers",
    Base.metadata,
    Column(
        "job_id",
        UUID(as_uuid=True),
        ForeignKey("research_jobs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "paper_id",
        UUID(as_uuid=True),
        ForeignKey("research_papers.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)