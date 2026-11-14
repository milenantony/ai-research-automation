
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

import httpx


logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API_URL = (
    "https://api.semanticscholar.org/graph/v1/paper/search"
)

PAPER_FIELDS = (
    "paperId,title,abstract,authors,publicationDate,"
    "year,externalIds,url,openAccessPdf"
)


class SemanticScholarAPIError(Exception):
    """Raised when the Semantic Scholar API request or response fails."""


@dataclass
class SemanticScholarPaper:
    """Structured metadata for a paper retrieved from Semantic Scholar."""

    external_id: str
    title: str
    abstract: str
    authors: list[str]
    published_date: datetime | None
    paper_url: str | None
    pdf_url: str | None
    doi: str | None
    source: str = "semantic_scholar"


class SemanticScholarClient:
    """Client for retrieving research papers from Semantic Scholar."""

    def __init__(
        self,
        timeout: float = 20.0,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.timeout = timeout
        self.api_key = api_key
        self.transport = transport

    async def search(
        self,
        topic: str,
        max_results: int = 10,
        offset: int = 0,
    ) -> list[SemanticScholarPaper]:
        """
        Search Semantic Scholar for research papers.

        Args:
            topic: Research topic to search for.
            max_results: Maximum number of papers to retrieve.
            offset: Starting result index for pagination.

        Returns:
            A list of structured SemanticScholarPaper objects.

        Raises:
            ValueError: If search parameters are invalid.
            SemanticScholarAPIError: If the API request or response fails.
        """

        if not topic or not topic.strip():
            raise ValueError("Research topic cannot be empty.")

        if not 1 <= max_results <= 100:
            raise ValueError("max_results must be between 1 and 100.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        params = {
            "query": topic.strip(),
            "limit": max_results,
            "offset": offset,
            "fields": PAPER_FIELDS,
        }

        headers = {}

        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    SEMANTIC_SCHOLAR_API_URL,
                    params=params,
                    headers=headers,
                )

                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            if status_code == 429:
                message = (
                    "Semantic Scholar API rate limit exceeded."
                )
            else:
                message = (
                    "Failed to retrieve papers from Semantic Scholar."
                )

            logger.error(
                "Semantic Scholar API returned HTTP %s",
                status_code,
            )

            raise SemanticScholarAPIError(message) from exc

        except httpx.HTTPError as exc:
            logger.exception("Semantic Scholar API request failed")

            raise SemanticScholarAPIError(
                "Failed to connect to Semantic Scholar."
            ) from exc

        try:
            data = response.json()
            return self._parse_response(data)

        except (ValueError, TypeError, KeyError) as exc:
            logger.exception(
                "Failed to parse Semantic Scholar API response"
            )

            raise SemanticScholarAPIError(
                "Invalid response received from Semantic Scholar."
            ) from exc

    @staticmethod
    def _parse_response(
        data: dict,
    ) -> list[SemanticScholarPaper]:
        """Parse the JSON response returned by Semantic Scholar."""

        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")

        paper_data = data.get("data", [])

        if not isinstance(paper_data, list):
            raise ValueError("Expected data to be a list.")

        papers = []

        for item in paper_data:
            if not isinstance(item, dict):
                logger.warning(
                    "Skipping invalid Semantic Scholar paper entry"
                )
                continue

            paper_id = item.get("paperId")
            title = item.get("title")

            if not paper_id or not title:
                logger.warning(
                    "Skipping paper with missing required metadata"
                )
                continue

            abstract = item.get("abstract") or ""

            authors_data = item.get("authors") or []

            if not isinstance(authors_data, list):
                authors_data = []

            authors = [
                author["name"].strip()
                for author in authors_data
                if (
                    isinstance(author, dict)
                    and isinstance(author.get("name"), str)
                    and author["name"].strip()
                )
            ]

            publication_date = item.get("publicationDate")

            published_date = None

            if publication_date:
                published_date = datetime.fromisoformat(
                    publication_date.replace("Z", "+00:00")
                )

                if published_date.tzinfo is None:
                    published_date = published_date.replace(
                        tzinfo=timezone.utc
                    )

            elif item.get("year"):
                published_date = datetime(
                    year=int(item["year"]),
                    month=1,
                    day=1,
                    tzinfo=timezone.utc,
                )

            external_ids = item.get("externalIds") or {}

            if not isinstance(external_ids, dict):
                external_ids = {}

            doi = external_ids.get("DOI")

            open_access_pdf = item.get("openAccessPdf") or {}

            if not isinstance(open_access_pdf, dict):
                open_access_pdf = {}

            papers.append(
                SemanticScholarPaper(
                    external_id=str(paper_id),
                    title=" ".join(title.split()),
                    abstract=" ".join(abstract.split()),
                    authors=authors,
                    published_date=published_date,
                    paper_url=item.get("url"),
                    pdf_url=open_access_pdf.get("url"),
                    doi=doi.strip() if isinstance(doi, str) else None,
                )
            )

        logger.info(
            "Retrieved %s papers from Semantic Scholar",
            len(papers),
        )

        return papers
