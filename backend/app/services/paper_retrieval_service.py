
import asyncio
import logging
from sqlalchemy.orm import Session
from app.models.research_paper import ResearchPaper
from app.services.paper_service import PaperService

from app.services.paper_retrieval.arxiv import (
    ArxivClient,
    ArxivAPIError,
)
from app.services.paper_retrieval.semantic_scholar import (
    SemanticScholarClient,
    SemanticScholarAPIError,
)

logger = logging.getLogger(__name__)


class PaperRetrievalService:
    def __init__(
        self,
        arxiv_client=None,
        semantic_scholar_client=None,
    ):
        self.arxiv_client = (
            arxiv_client
            if arxiv_client is not None
            else ArxivClient()
        )

        self.semantic_scholar_client = (
            semantic_scholar_client
            if semantic_scholar_client is not None
            else SemanticScholarClient()
        )

    async def search(
        self,
        topic: str,
        max_results: int = 10,
    ) -> list:
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("Research topic cannot be empty.")

        if not isinstance(max_results, int) or not 1 <= max_results <= 100:
            raise ValueError(
                "max_results must be between 1 and 100."
            )

        results = await asyncio.gather(
            self.arxiv_client.search(
                topic,
                max_results=max_results,
            ),
            self.semantic_scholar_client.search(
                topic,
                max_results=max_results,
            ),
            return_exceptions=True,
        )

        papers = []
        failures = []


        for provider, result in zip(
            ("arxiv", "semantic_scholar"),
            results,
        ):
            if isinstance(
                result,
                (ArxivAPIError, SemanticScholarAPIError),
            ):
                logger.warning(
                    "Paper retrieval failed for %s: %s",
                    provider,
                    result,
                )
                failures.append(provider)
                continue

            if isinstance(result, BaseException):
                raise result

            papers.extend(result)

        if len(failures) == 2:
            raise RuntimeError(
                "All paper retrieval providers failed."
            )
        return papers
    async def search_and_save(
        self,
        db: Session,
        topic: str,
        max_results: int = 10,
    ) -> list[ResearchPaper]:
        """Retrieve papers and save them to PostgreSQL."""

        papers = await self.search(
            topic=topic,
            max_results=max_results,
        )

        if not papers:
            return []

        saved_papers = PaperService.save_papers(
            db=db,
            papers=papers,
        )

        return saved_papers