
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from sqlalchemy import select, func

from app.models.research_paper import ResearchPaper
from app.services.paper_retrieval.arxiv import ArxivPaper

from app.services.paper_retrieval_service import (
    PaperRetrievalService,
)
from app.services.paper_retrieval.arxiv import ArxivAPIError
from app.services.paper_retrieval.semantic_scholar import (
    SemanticScholarAPIError,
)


@pytest.mark.parametrize(
    ("configured_key", "expected_key"),
    [(None, None), ("  ", None), (" test-api-key ", "test-api-key")],
)
def test_default_semantic_scholar_client_uses_optional_key(
    monkeypatch, configured_key, expected_key
):
    if configured_key is None:
        monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    else:
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", configured_key)

    service = PaperRetrievalService()

    assert service.semantic_scholar_client.api_key == expected_key


@pytest.fixture
def mock_clients():
    arxiv = AsyncMock()
    semantic_scholar = AsyncMock()

    return arxiv, semantic_scholar


@pytest.mark.asyncio
async def test_search_both_providers_success(mock_clients):
    arxiv, semantic_scholar = mock_clients

    arxiv.search.return_value = ["arxiv_paper"]
    semantic_scholar.search.return_value = ["semantic_paper"]

    service = PaperRetrievalService(
        arxiv_client=arxiv,
        semantic_scholar_client=semantic_scholar,
    )

    papers = await service.search("machine learning")

    assert papers == ["arxiv_paper", "semantic_paper"]

    arxiv.search.assert_awaited_once_with(
        "machine learning",
        max_results=10,
    )
    semantic_scholar.search.assert_awaited_once_with(
        "machine learning",
        max_results=10,
    )


@pytest.mark.asyncio
async def test_search_semantic_scholar_failure(mock_clients):
    arxiv, semantic_scholar = mock_clients

    arxiv.search.return_value = ["arxiv_paper"]
    semantic_scholar.search.side_effect = SemanticScholarAPIError(
        "Rate limit exceeded"
    )

    service = PaperRetrievalService(
        arxiv_client=arxiv,
        semantic_scholar_client=semantic_scholar,
    )

    papers = await service.search("machine learning")

    assert papers == ["arxiv_paper"]


@pytest.mark.asyncio
async def test_search_all_providers_fail(mock_clients):
    arxiv, semantic_scholar = mock_clients

    arxiv.search.side_effect = ArxivAPIError(
        "arXiv unavailable"
    )
    semantic_scholar.search.side_effect = SemanticScholarAPIError(
        "Semantic Scholar unavailable"
    )

    service = PaperRetrievalService(
        arxiv_client=arxiv,
        semantic_scholar_client=semantic_scholar,
    )

    with pytest.raises(
        RuntimeError,
        match="All paper retrieval providers failed",
    ):
        await service.search("machine learning")

@pytest.mark.asyncio
async def test_search_unexpected_provider_error(mock_clients):
    arxiv, semantic_scholar = mock_clients

    arxiv.search.side_effect = TypeError(
        "Unexpected programming error"
    )
    semantic_scholar.search.return_value = [
        "semantic_paper"
    ]

    service = PaperRetrievalService(
        arxiv_client=arxiv,
        semantic_scholar_client=semantic_scholar,
    )

    with pytest.raises(
        TypeError,
        match="Unexpected programming error",
    ):
        await service.search("machine learning")

@pytest.mark.asyncio
async def test_search_and_save_papers(
    mock_clients,
    db_session,
):
    arxiv, semantic_scholar = mock_clients

    paper = ArxivPaper(
        external_id="2501.00010",
        title="AI Research Automation",
        abstract="Research on automated literature discovery.",
        authors=["Alice", "Bob"],
        published_date=datetime(
            2025, 1, 1, tzinfo=timezone.utc
        ),
        paper_url="https://arxiv.org/abs/2501.00010",
        pdf_url="https://arxiv.org/pdf/2501.00010",
        doi=None,
    )

    arxiv.search.return_value = [paper]
    semantic_scholar.search.return_value = []

    service = PaperRetrievalService(
        arxiv_client=arxiv,
        semantic_scholar_client=semantic_scholar,
    )

    saved = await service.search_and_save(
        db=db_session,
        topic="AI Research Automation",
        max_results=5,
    )

    assert len(saved) == 1
    assert saved[0].external_id == "2501.00010"
    assert saved[0].source == "arxiv"
    assert saved[0].title == "AI Research Automation"

    count = db_session.scalar(
        select(func.count()).select_from(ResearchPaper)
    )

    assert count == 1

    arxiv.search.assert_awaited_once_with(
        "AI Research Automation",
        max_results=5,
    )
    semantic_scholar.search.assert_awaited_once_with(
        "AI Research Automation",
        max_results=5,
    )

@pytest.mark.asyncio
async def test_search_and_save_when_semantic_scholar_fails(
    mock_clients,
    db_session,
):
    arxiv, semantic_scholar = mock_clients

    paper = ArxivPaper(
        external_id="2501.00020",
        title="Machine Learning for Healthcare",
        abstract="Applications of ML in healthcare.",
        authors=["Alice", "Bob"],
        published_date=datetime(
            2025, 1, 1, tzinfo=timezone.utc
        ),
        paper_url="https://arxiv.org/abs/2501.00020",
        pdf_url="https://arxiv.org/pdf/2501.00020",
        doi=None,
    )

    arxiv.search.return_value = [paper]

    semantic_scholar.search.side_effect = (
        SemanticScholarAPIError(
            "Rate limit exceeded"
        )
    )

    service = PaperRetrievalService(
        arxiv_client=arxiv,
        semantic_scholar_client=semantic_scholar,
    )

    saved = await service.search_and_save(
        db=db_session,
        topic="machine learning healthcare",
        max_results=5,
    )

    assert len(saved) == 1
    assert saved[0].external_id == "2501.00020"
    assert saved[0].source == "arxiv"

    count = db_session.scalar(
        select(func.count()).select_from(ResearchPaper)
    )

    assert count == 1

@pytest.mark.asyncio
async def test_search_and_save_prevents_duplicates(
    mock_clients,
    db_session,
):
    arxiv, semantic_scholar = mock_clients

    paper = ArxivPaper(
        external_id="2501.00030",
        title="Automated Research Discovery",
        abstract="Research on automated paper retrieval.",
        authors=["Alice", "Bob"],
        published_date=datetime(
            2025, 1, 1, tzinfo=timezone.utc
        ),
        paper_url="https://arxiv.org/abs/2501.00030",
        pdf_url="https://arxiv.org/pdf/2501.00030",
        doi=None,
    )

    arxiv.search.return_value = [paper]
    semantic_scholar.search.return_value = []

    service = PaperRetrievalService(
        arxiv_client=arxiv,
        semantic_scholar_client=semantic_scholar,
    )

    first = await service.search_and_save(
        db=db_session,
        topic="automated research",
        max_results=5,
    )

    second = await service.search_and_save(
        db=db_session,
        topic="automated research",
        max_results=5,
    )

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].id == second[0].id

    count = db_session.scalar(
        select(func.count()).select_from(ResearchPaper)
    )

    assert count == 1
