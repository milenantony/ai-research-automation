from unittest.mock import AsyncMock

from app.services.paper_retrieval.arxiv import ArxivClient, ArxivPaper
from app.services.paper_retrieval.semantic_scholar import SemanticScholarClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.research_paper import ResearchPaper
from app.services.paper_service import PaperService


def test_repeated_search_lists_one_paper_only_for_its_job(client, monkeypatch):
    topic = "Machine learning in healthcare"
    paper = ArxivPaper(
        external_id="2501.00001",
        title="Machine Learning in Healthcare",
        abstract="A study of clinical applications.",
        authors=["Alice"],
        published_date=None,
        paper_url="https://arxiv.org/abs/2501.00001",
        pdf_url=None,
        doi=None,
    )
    arxiv_search = AsyncMock(return_value=[paper])
    scholar_search = AsyncMock(return_value=[])
    monkeypatch.setattr(ArxivClient, "search", arxiv_search)
    monkeypatch.setattr(SemanticScholarClient, "search", scholar_search)

    first_job = client.post("/research-jobs", json={"topic": topic})
    second_job = client.post("/research-jobs", json={"topic": "Solar forecasting"})
    assert first_job.status_code == 201, first_job.text
    assert second_job.status_code == 201, second_job.text

    first_path = f"/research-jobs/{first_job.json()['id']}/papers"
    second_path = f"/research-jobs/{second_job.json()['id']}/papers"

    first_search = client.post(f"{first_path}:search", json={"max_results": 3})
    assert first_search.status_code == 200, first_search.text
    papers = first_search.json()
    assert len(papers) == 1
    assert papers[0]["external_id"] == paper.external_id
    assert papers[0]["source"] == "arxiv"
    arxiv_search.assert_awaited_once_with(topic, max_results=3)
    scholar_search.assert_awaited_once_with(topic, max_results=3)

    repeat_search = client.post(f"{first_path}:search", json={"max_results": 3})
    assert repeat_search.status_code == 200, repeat_search.text
    assert repeat_search.json() == papers

    first_listing = client.get(first_path)
    assert first_listing.status_code == 200, first_listing.text
    assert first_listing.json() == papers

    second_listing = client.get(second_path)
    assert second_listing.status_code == 200, second_listing.text
    assert second_listing.json() == []
def test_search_rolls_back_new_paper_when_linking_fails(
    client, db_session, monkeypatch
):
    paper = ArxivPaper(
        external_id="rollback-test-001",
        title="Paper for rollback test",
        abstract=None,
        authors=[],
        published_date=None,
        paper_url=None,
        pdf_url=None,
        doi=None,
    )
    monkeypatch.setattr(ArxivClient, "search", AsyncMock(return_value=[paper]))
    monkeypatch.setattr(SemanticScholarClient, "search", AsyncMock(return_value=[]))

    def fail_link(db, job_id, papers):
        assert len(list(papers)) == 1
        raise SQLAlchemyError("Simulated link failure")

    monkeypatch.setattr(PaperService, "link_papers_to_job", staticmethod(fail_link))

    job = client.post("/research-jobs", json={"topic": "Research on rollback"})
    assert job.status_code == 201, job.text

    path = f"/research-jobs/{job.json()['id']}/papers"
    response = client.post(f"{path}:search", json={"max_results": 1})
    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Failed to save research job papers"

    stored_id = db_session.scalar(
        select(ResearchPaper.id).where(
            ResearchPaper.source == "arxiv",
            ResearchPaper.external_id == paper.external_id,
        )
    )
    assert stored_id is None

    listing = client.get(path)
    assert listing.status_code == 200, listing.text
    assert listing.json() == []