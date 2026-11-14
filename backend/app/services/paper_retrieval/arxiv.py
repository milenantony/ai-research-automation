
from dataclasses import dataclass
from datetime import datetime
import logging
import xml.etree.ElementTree as ET

import httpx


logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"

ATOM_NAMESPACE = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivAPIError(Exception):
    """Raised when the arXiv API request or response fails."""


@dataclass
class ArxivPaper:
    """Structured metadata for a research paper retrieved from arXiv."""

    external_id: str
    title: str
    abstract: str
    authors: list[str]
    published_date: datetime
    paper_url: str
    pdf_url: str | None
    doi: str | None
    source: str = "arxiv"


class ArxivClient:
    """Client for retrieving research papers from the arXiv API."""

    def __init__(
        self,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.timeout = timeout
        self.transport = transport

    async def search(
        self,
        topic: str,
        max_results: int = 10,
        start: int = 0,
    ) -> list[ArxivPaper]:
        """
        Search arXiv for research papers matching a topic.

        Args:
            topic: Research topic to search for.
            max_results: Maximum number of papers to retrieve.
            start: Starting result index for pagination.

        Returns:
            A list of structured ArxivPaper objects.

        Raises:
            ValueError: If the search parameters are invalid.
            ArxivAPIError: If the API request or response fails.
        """

        if not topic or not topic.strip():
            raise ValueError("Research topic cannot be empty.")

        if not 1 <= max_results <= 100:
            raise ValueError("max_results must be between 1 and 100.")

        if start < 0:
            raise ValueError("start cannot be negative.")

        # Escape special characters in the quoted search phrase.
        escaped_topic = (
            topic.strip()
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )

        params = {
            "search_query": f'all:"{escaped_topic}"',
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    ARXIV_API_URL,
                    params=params,
                )

                response.raise_for_status()

        except httpx.HTTPError as exc:
            logger.exception("arXiv API request failed")

            raise ArxivAPIError(
                "Failed to retrieve papers from arXiv."
            ) from exc

        try:
            return self._parse_response(response.text)

        except (ET.ParseError, ValueError, TypeError) as exc:
            logger.exception("Failed to parse arXiv API response")

            raise ArxivAPIError(
                "Invalid response received from arXiv."
            ) from exc

    @staticmethod
    def _parse_response(xml_content: str) -> list[ArxivPaper]:
        """Parse the Atom XML response returned by arXiv."""

        root = ET.fromstring(xml_content)

        papers = []

        for entry in root.findall("atom:entry", ATOM_NAMESPACE):
            paper_id = entry.findtext(
                "atom:id",
                default="",
                namespaces=ATOM_NAMESPACE,
            ).strip()

            title = " ".join(
                entry.findtext(
                    "atom:title",
                    default="",
                    namespaces=ATOM_NAMESPACE,
                ).split()
            )

            abstract = " ".join(
                entry.findtext(
                    "atom:summary",
                    default="",
                    namespaces=ATOM_NAMESPACE,
                ).split()
            )

            published = entry.findtext(
                "atom:published",
                namespaces=ATOM_NAMESPACE,
            )

            if not paper_id or not title or not published:
                logger.warning(
                    "Skipping arXiv entry with missing required metadata"
                )
                continue

            authors = [
                author.findtext(
                    "atom:name",
                    default="",
                    namespaces=ATOM_NAMESPACE,
                ).strip()
                for author in entry.findall(
                    "atom:author",
                    ATOM_NAMESPACE,
                )
            ]

            authors = [author for author in authors if author]

            published_date = datetime.fromisoformat(
                published.strip().replace("Z", "+00:00")
            )

            pdf_url = None
            doi = None

            for link in entry.findall(
                "atom:link",
                ATOM_NAMESPACE,
            ):
                if (
                    link.get("title") == "pdf"
                    or link.get("type") == "application/pdf"
                ):
                    pdf_url = link.get("href")

            doi = entry.findtext(
                "arxiv:doi",
                namespaces=ATOM_NAMESPACE,
            )

            arxiv_id = paper_id.rstrip("/").split("/")[-1]

            papers.append(
                ArxivPaper(
                    external_id=arxiv_id,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    published_date=published_date,
                    paper_url=paper_id,
                    pdf_url=pdf_url,
                    doi=doi.strip() if doi else None,
                )
            )

        logger.info(
            "Retrieved %s papers from arXiv",
            len(papers),
        )

        return papers
