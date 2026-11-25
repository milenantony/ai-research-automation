from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol
from uuid import UUID

from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session

from app.models.research_job_papers import research_job_papers
from app.models.research_paper import ResearchPaper


EMBEDDING_DIMENSIONS = 768


class PassageEmbedder(Protocol):
    model: str

    def embed(self, content: str, *, is_query: bool) -> Sequence[float]: ...


@dataclass(frozen=True)
class RetrievedPassage:
    job_id: UUID
    paper_id: UUID
    passage_text: str
    title: str
    source: str
    external_id: str
    paper_url: str | None
    doi: str | None
    cosine_distance: float


class PassageRetrieval:
    """Store and search one passage per selected, nonblank abstract."""

    def __init__(self, db: Session, embedder: PassageEmbedder):
        self.db = db
        self.embedder = embedder

    def _selected_papers(self, job_id: UUID, paper_ids: Iterable[UUID]):
        selected = set(paper_ids)
        if not selected:
            return []
        papers = self.db.scalars(
            select(ResearchPaper)
            .join(research_job_papers, research_job_papers.c.paper_id == ResearchPaper.id)
            .where(
                research_job_papers.c.job_id == job_id,
                ResearchPaper.id.in_(selected),
            )
            .order_by(ResearchPaper.id)
        ).all()
        if len(papers) != len(selected):
            raise ValueError("Every selected paper must be linked to this research job")
        return papers

    def _vector(self, content: str, *, is_query: bool) -> str:
        values = [float(value) for value in self.embedder.embed(content, is_query=is_query)]
        if (
            len(values) != EMBEDDING_DIMENSIONS
            or not all(isfinite(value) for value in values)
            or not any(values)
        ):
            raise ValueError("Expected a finite, nonzero 768-dimensional embedding")
        return "[" + ",".join(map(str, values)) + "]"

    def ingest(self, job_id: UUID, paper_ids: Iterable[UUID]) -> int:
        """Return the number of changed passages. The caller owns the transaction."""
        papers = self._selected_papers(job_id, paper_ids)
        if not papers:
            return 0

        scope = {"job_id": job_id, "model": self.embedder.model}
        existing = dict(self.db.execute(
            text("""
                SELECT paper_id, passage_text
                FROM research_abstract_passages
                WHERE job_id = :job_id AND embedding_model = :model
                  AND paper_id IN :paper_ids
            """).bindparams(bindparam("paper_ids", expanding=True)),
            {**scope, "paper_ids": [paper.id for paper in papers]},
        ).all())

        changed = 0
        for paper in papers:
            abstract = (paper.abstract or "").strip()
            if abstract == existing.get(paper.id, ""):
                continue

            params = {**scope, "paper_id": paper.id}
            if not abstract:
                result = self.db.execute(text("""
                    DELETE FROM research_abstract_passages
                    WHERE job_id = :job_id AND paper_id = :paper_id
                      AND embedding_model = :model
                """), params)
            else:
                result = self.db.execute(text("""
                    INSERT INTO research_abstract_passages
                        (job_id, paper_id, embedding_model, passage_text, embedding)
                    VALUES (:job_id, :paper_id, :model, :abstract, CAST(:embedding AS vector))
                    ON CONFLICT (job_id, paper_id, embedding_model) DO UPDATE
                    SET passage_text = EXCLUDED.passage_text, embedding = EXCLUDED.embedding
                    WHERE research_abstract_passages.passage_text <> EXCLUDED.passage_text
                """), {
                    **params,
                    "abstract": abstract,
                    "embedding": self._vector(abstract, is_query=False),
                })
            changed += result.rowcount
        return changed

    def retrieve(
        self, job_id: UUID, paper_ids: Iterable[UUID], query: str, *, limit: int = 5
    ) -> list[RetrievedPassage]:
        if not query.strip():
            raise ValueError("Passage query cannot be empty")
        if limit < 1:
            raise ValueError("Passage limit must be positive")
        papers = self._selected_papers(job_id, paper_ids)
        if not papers:
            return []

        rows = self.db.execute(
            text("""
                SELECT passage.job_id, passage.paper_id, passage.passage_text,
                       paper.title, paper.source, paper.external_id, paper.paper_url, paper.doi,
                       passage.embedding <=> CAST(:embedding AS vector) AS cosine_distance
                FROM research_abstract_passages AS passage
                JOIN research_papers AS paper ON paper.id = passage.paper_id
                WHERE passage.job_id = :job_id AND passage.embedding_model = :model
                  AND passage.paper_id IN :paper_ids
                ORDER BY cosine_distance, passage.paper_id
                LIMIT :limit
            """).bindparams(bindparam("paper_ids", expanding=True)),
            {
                "job_id": job_id,
                "model": self.embedder.model,
                "paper_ids": [paper.id for paper in papers],
                "embedding": self._vector(query.strip(), is_query=True),
                "limit": limit,
            },
        ).mappings()
        return [RetrievedPassage(**row) for row in rows]
