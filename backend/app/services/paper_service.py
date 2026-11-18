from uuid import UUID

from app.models.research_job_papers import research_job_papers

from typing import Iterable

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Query, Session
from app.models.research_paper import ResearchPaper


class PaperService:
    @staticmethod
    def save_papers(
        db: Session,
        papers: Iterable,
    ) -> list[ResearchPaper]:
        """Save retrieved papers without creating duplicates."""

        saved_papers = []

        for paper in papers:
            values = {
                "external_id": paper.external_id,
                "source": paper.source,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date,
                "paper_url": paper.paper_url,
                "pdf_url": paper.pdf_url,
                "doi": paper.doi,
            }

            statement = (
                insert(ResearchPaper)
                .values(**values)
                .on_conflict_do_nothing(
                    constraint="uq_research_paper_source_external_id"
                )
            )

            db.execute(statement)

            existing_paper = (
                db.query(ResearchPaper)
                .filter(
                    ResearchPaper.source == paper.source,
                    ResearchPaper.external_id == paper.external_id,
                )
                .one()
            )

            saved_papers.append(existing_paper)

        return saved_papers
    @staticmethod
    def link_papers_to_job(
        db: Session,
        job_id: UUID,
        papers: Iterable[ResearchPaper],
    ) -> None:
        """Link retrieved papers to a research job."""
        links = [{"job_id": job_id, "paper_id": paper.id} for paper in papers]
        if not links:
            return

        statement = insert(research_job_papers).on_conflict_do_nothing(
            index_elements=["job_id", "paper_id"],
        )
        db.execute(statement, links)
    @staticmethod
    def papers_for_job(db: Session, job_id: UUID) -> Query[ResearchPaper]:
        """Return the job's linked papers in a stable order."""
        return (
            db.query(ResearchPaper)
            .join(
                research_job_papers,
                ResearchPaper.id == research_job_papers.c.paper_id,
            )
            .filter(research_job_papers.c.job_id == job_id)
            .order_by(ResearchPaper.id)
        )
