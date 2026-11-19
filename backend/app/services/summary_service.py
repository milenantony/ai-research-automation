from uuid import UUID

from sqlalchemy.orm import Session

from app.models.research_summary import ResearchSummary
from app.models.research_summary_papers import research_summary_papers


def save_linked_paper_summary(
    db: Session,
    job_id: UUID,
    summary: str,
    paper_ids: list[UUID],
) -> None:
    """Save a summary and its sources in prompt order."""
    if not paper_ids:
        raise ValueError("A linked-paper summary requires at least one source")

    record = ResearchSummary(job_id=job_id, summary=summary)
    db.add(record)
    db.flush()

    links = [
        {
            "summary_id": record.id,
            "paper_id": paper_id,
            "position": position,
        }
        for position, paper_id in enumerate(paper_ids, start=1)
    ]
    db.execute(research_summary_papers.insert(), links)