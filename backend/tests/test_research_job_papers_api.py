from unittest.mock import AsyncMock
import pytest
from uuid import uuid4

from app.services.paper_retrieval.arxiv import ArxivClient, ArxivPaper
from app.services.paper_retrieval.semantic_scholar import SemanticScholarClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.research_paper import ResearchPaper
from app.services.paper_service import PaperService
from app.services.paper_retrieval.arxiv import ArxivAPIError, ArxivClient, ArxivPaper
from app.services.paper_retrieval.semantic_scholar import (
    SemanticScholarAPIError,
    SemanticScholarClient,
)


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
@pytest.mark.parametrize("max_results", [0, 101])
def test_search_rejects_invalid_limits(client, monkeypatch, max_results):
    arxiv_search = AsyncMock(return_value=[])
    scholar_search = AsyncMock(return_value=[])
    monkeypatch.setattr(ArxivClient, "search", arxiv_search)
    monkeypatch.setattr(SemanticScholarClient, "search", scholar_search)

    job = client.post("/research-jobs", json={"topic": "Solar forecasting"})
    assert job.status_code == 201, job.text

    response = client.post(
        f"/research-jobs/{job.json()['id']}/papers:search",
        json={"max_results": max_results},
    )

    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["body", "max_results"]
        for error in response.json()["detail"]
    )
    arxiv_search.assert_not_awaited()
    scholar_search.assert_not_awaited()
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_paper_endpoints_return_404_for_missing_job(client, monkeypatch, method):
    arxiv_search = AsyncMock(return_value=[])
    scholar_search = AsyncMock(return_value=[])
    monkeypatch.setattr(ArxivClient, "search", arxiv_search)
    monkeypatch.setattr(SemanticScholarClient, "search", scholar_search)

    path = f"/research-jobs/{uuid4()}/papers"
    if method == "GET":
        response = client.get(path)
    else:
        response = client.post(f"{path}:search", json={"max_results": 1})

    assert response.status_code == 404, response.text
    arxiv_search.assert_not_awaited()
    scholar_search.assert_not_awaited()
def test_list_job_papers_paginates_in_id_order(client, monkeypatch):
    papers = [
        ArxivPaper(
            external_id=f"pagination-{number}",
            title=f"Solar forecasting study {number}",
            abstract=None,
            authors=[],
            published_date=None,
            paper_url=None,
            pdf_url=None,
            doi=None,
        )
        for number in range(3)
    ]
    monkeypatch.setattr(ArxivClient, "search", AsyncMock(return_value=papers))
    monkeypatch.setattr(SemanticScholarClient, "search", AsyncMock(return_value=[]))

    job = client.post("/research-jobs", json={"topic": "Solar forecasting"})
    assert job.status_code == 201, job.text
    path = f"/research-jobs/{job.json()['id']}/papers"

    search = client.post(f"{path}:search", json={"max_results": 3})
    assert search.status_code == 200, search.text
    expected_ids = sorted(paper["id"] for paper in search.json())
    assert len(set(expected_ids)) == 3

    for skip in (0, 2, 3):
        page = client.get(path, params={"skip": skip, "limit": 2})
        assert page.status_code == 200, page.text
        assert [paper["id"] for paper in page.json()] == expected_ids[skip : skip + 2]
def test_search_returns_502_when_both_providers_fail(client, monkeypatch):
    arxiv_search = AsyncMock(side_effect=ArxivAPIError("arXiv unavailable"))
    scholar_search = AsyncMock(
        side_effect=SemanticScholarAPIError("Semantic Scholar unavailable")
    )
    monkeypatch.setattr(ArxivClient, "search", arxiv_search)
    monkeypatch.setattr(SemanticScholarClient, "search", scholar_search)

    topic = "Solar forecasting"
    job = client.post("/research-jobs", json={"topic": topic})
    assert job.status_code == 201, job.text
    path = f"/research-jobs/{job.json()['id']}/papers"

    response = client.post(f"{path}:search", json={"max_results": 2})

    assert response.status_code == 502, response.text
    assert response.json()["detail"] == "All paper retrieval providers failed"
    arxiv_search.assert_awaited_once_with(topic, max_results=2)
    scholar_search.assert_awaited_once_with(topic, max_results=2)

    listing = client.get(path)
    assert listing.status_code == 200, listing.text
    assert listing.json() == []
def test_summary_uses_only_papers_linked_to_requested_job(client, monkeypatch,db_session):
    from app.services.llm_service import LLMService
    from uuid import UUID
    from app.models import ResearchSummary, research_summary_papers

    def make_paper(external_id, title, abstract):
        return ArxivPaper(
            external_id=external_id,
            title=title,
            abstract=abstract,
            authors=[],
            published_date=None,
            paper_url=None,
            pdf_url=None,
            doi=None,
        )

    solar = make_paper("summary-solar", "Solar study", "Cloud cover affects irradiance.")
    wind = make_paper("summary-wind", "Wind study", "Turbine height affects output.")
    solar_two = make_paper("summary-solar-2", "Satellite forecasting", None)

    monkeypatch.setattr(
        ArxivClient, "search", AsyncMock(side_effect=[[solar, solar_two], [wind]])
    )

   
    monkeypatch.setattr(SemanticScholarClient, "search", AsyncMock(return_value=[]))

    prompts = []

    def capture_prompt(self, prompt):
        prompts.append(prompt)
        return "Summary of the solar study."

    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    monkeypatch.setattr(LLMService, "generate", capture_prompt)
    solar_ids_by_title = {}

    job_ids = []
    for topic in ("Solar forecasting", "Wind forecasting"):
        job = client.post("/research-jobs", json={"topic": topic})
        assert job.status_code == 201, job.text
        job_id = job.json()["id"]
        search = client.post(
            f"/research-jobs/{job_id}/papers:search", json={"max_results": 2}
        )
        assert search.status_code == 200, search.text
        if topic == "Solar forecasting":
            solar_ids_by_title = {
                paper["title"]: UUID(paper["id"]) for paper in search.json()
            }
        job_ids.append(job_id)

    response = client.post(f"/research-jobs/{job_ids[0]}/papers:generate-summary")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "job_id": job_ids[0],
        "topic": "Solar forecasting",
        "summary": "Summary of the solar study.",
    }
    assert len(prompts) == 1
    assert solar.title in prompts[0]
    assert solar.abstract in prompts[0]
    assert wind.title not in prompts[0]
    assert wind.abstract not in prompts[0]
    assert set(solar_ids_by_title) == {solar.title, solar_two.title}
    prompt_titles = [
        line.split(": ", 1)[1]
        for line in prompts[0].splitlines()
        if line.startswith(("Paper 1: ", "Paper 2: "))
    ]
    assert sorted(prompt_titles) == sorted(solar_ids_by_title)

    saved = db_session.scalars(
        select(ResearchSummary).where(ResearchSummary.job_id == UUID(job_ids[0]))
    ).one()
    assert saved.summary == response.json()["summary"]

    links = research_summary_papers.c
    stored_sources = db_session.execute(
        select(links.position, links.paper_id)
        .where(links.summary_id == saved.id)
        .order_by(links.position)
    ).all()
    assert stored_sources == [
        (position, solar_ids_by_title[title])
        for position, title in enumerate(prompt_titles, start=1)
    ]

@pytest.mark.parametrize(
    ("job_exists", "expected_status", "expected_detail"),
    [
        (True, 400, "No papers are linked to this research job"),
        (False, 404, "Research job not found"),
    ],
    ids=["empty-job", "missing-job"],
)
def test_linked_summary_requires_job_and_papers(
    client, monkeypatch, job_exists, expected_status, expected_detail
):
    from app.services.llm_service import LLMService

    def fail_if_initialized(self):
        pytest.fail("LLMService was initialized before linked papers were available")

    monkeypatch.setattr(LLMService, "__init__", fail_if_initialized)

    if job_exists:
        job = client.post("/research-jobs", json={"topic": "Solar forecasting"})
        assert job.status_code == 201, job.text
        job_id = job.json()["id"]
    else:
        job_id = uuid4()

    response = client.post(f"/research-jobs/{job_id}/papers:generate-summary")

    assert response.status_code == expected_status, response.text
def test_linked_summary_rolls_back_when_source_insert_fails(
    client, db_session, monkeypatch
):
    from uuid import UUID

    from app.api.routes import research
    from app.models import ResearchSummary
    from app.services.llm_service import LLMService
    from app.services.summary_service import save_linked_paper_summary

    job = client.post("/research-jobs", json={"topic": "Solar forecasting"})
    assert job.status_code == 201, job.text
    job_id = UUID(job.json()["id"])

    paper = ResearchPaper(
        source="arxiv",
        external_id="summary-rollback-001",
        title="Solar forecasting study",
        authors=[],
    )
    db_session.add(paper)
    db_session.flush()
    paper_id = paper.id
    PaperService.link_papers_to_job(db_session, job_id, [paper])
    db_session.commit()

    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    monkeypatch.setattr(LLMService, "generate", lambda self, prompt: "Solar summary.")

    def save_with_duplicate_source(db, job_id, summary, paper_ids):
        assert paper_ids == [paper_id]
        save_linked_paper_summary(db, job_id, summary, [paper_id, paper_id])

    monkeypatch.setattr(
        research, "save_linked_paper_summary", save_with_duplicate_source
    )

    response = client.post(f"/research-jobs/{job_id}/papers:generate-summary")

    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Failed to save linked-paper summary"

    saved_ids = db_session.scalars(
        select(ResearchSummary.id).where(ResearchSummary.job_id == job_id)
    ).all()
    assert saved_ids == []

    linked_papers = PaperService.papers_for_job(db_session, job_id).all()
    assert [item.id for item in linked_papers] == [paper_id]
def test_refined_search_uses_agent_query_and_preserves_job_topic(client, monkeypatch):
    from unittest.mock import Mock

    from app.api.routes import research

    topic = "How can we forecast solar irradiance?"
    refined_query = "solar irradiance forecasting"
    build_query = AsyncMock(return_value=refined_query)
    agent = Mock(build_search_query=build_query)
    monkeypatch.setattr(research, "PaperDiscoveryAgent", Mock(return_value=agent))

    arxiv_search = AsyncMock(return_value=[])
    scholar_search = AsyncMock(return_value=[])
    monkeypatch.setattr(ArxivClient, "search", arxiv_search)
    monkeypatch.setattr(SemanticScholarClient, "search", scholar_search)

    job = client.post("/research-jobs", json={"topic": topic})
    assert job.status_code == 201, job.text
    job_path = f"/research-jobs/{job.json()['id']}"

    response = client.post(
        f"{job_path}/papers:search",
        json={"refine_query": True, "max_results": 3},
    )

    assert response.status_code == 200, response.text
    assert response.json() == []
    build_query.assert_awaited_once_with(topic)
    arxiv_search.assert_awaited_once_with(refined_query, max_results=3)
    scholar_search.assert_awaited_once_with(refined_query, max_results=3)

    stored_job = client.get(job_path)
    assert stored_job.status_code == 200, stored_job.text
    assert stored_job.json()["topic"] == topic
def test_refined_search_configuration_failure_stops_retrieval(client, monkeypatch):
    from unittest.mock import Mock

    from app.api.routes import research
    from app.services.llm_exceptions import LLMConfigurationError

    agent = Mock(side_effect=LLMConfigurationError("GEMINI_API_KEY is missing"))
    monkeypatch.setattr(research, "PaperDiscoveryAgent", agent)

    arxiv_search = AsyncMock()
    scholar_search = AsyncMock()
    monkeypatch.setattr(ArxivClient, "search", arxiv_search)
    monkeypatch.setattr(SemanticScholarClient, "search", scholar_search)

    job = client.post("/research-jobs", json={"topic": "solar forecasting"})
    assert job.status_code == 201, job.text

    response = client.post(
        f"/research-jobs/{job.json()['id']}/papers:search",
        json={"refine_query": True},
    )

    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Paper discovery agent configuration failed"
    arxiv_search.assert_not_awaited()
    scholar_search.assert_not_awaited()
def test_refined_search_provider_failure_stops_retrieval(client, monkeypatch):
    from unittest.mock import Mock

    from app.api.routes import research
    from app.services.llm_exceptions import LLMProviderError

    build_query = AsyncMock(side_effect=LLMProviderError("Gemini request failed"))
    agent = Mock(build_search_query=build_query)
    monkeypatch.setattr(research, "PaperDiscoveryAgent", Mock(return_value=agent))

    arxiv_search = AsyncMock()
    scholar_search = AsyncMock()
    monkeypatch.setattr(ArxivClient, "search", arxiv_search)
    monkeypatch.setattr(SemanticScholarClient, "search", scholar_search)

    job = client.post("/research-jobs", json={"topic": "solar forecasting"})
    assert job.status_code == 201, job.text

    response = client.post(
        f"/research-jobs/{job.json()['id']}/papers:search",
        json={"refine_query": True},
    )

    assert response.status_code == 502, response.text
    assert response.json()["detail"] == "Failed to generate a paper search query"
    build_query.assert_awaited_once_with("solar forecasting")
    arxiv_search.assert_not_awaited()
    scholar_search.assert_not_awaited()
def test_reviewed_summary_uses_selected_papers_in_order(client, db_session, monkeypatch):
    from uuid import UUID

    from app.models import ResearchSummary, research_summary_papers
    from app.services.llm_service import LLMService

    job = client.post("/research-jobs", json={"topic": "Solar forecasting"})
    other_job = client.post("/research-jobs", json={"topic": "Wind forecasting"})
    assert job.status_code == other_job.status_code == 201
    job_id = UUID(job.json()["id"])
    other_job_id = UUID(other_job.json()["id"])

    papers = [
        ResearchPaper(source="arxiv", external_id=f"review-{i}",
                      title=title, abstract=f"Abstract {i}", authors=[])
        for i, title in enumerate(("First", "Second", "Excluded", "Other job"))
    ]
    db_session.add_all(papers)
    db_session.flush()
    PaperService.link_papers_to_job(db_session, job_id, papers[:3])
    PaperService.link_papers_to_job(db_session, other_job_id, papers[3:])
    db_session.commit()

    prompts = []
    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    monkeypatch.setattr(
        LLMService, "generate",
        lambda self, prompt: prompts.append(prompt) or "Reviewed summary",
    )

    selected = [str(papers[1].id), str(papers[0].id)]
    response = client.post(
        f"/research-jobs/{job_id}/papers:generate-summary",
        json={"paper_ids": selected},
    )
    assert response.status_code == 200, response.text
    assert "Paper 1: Second" in prompts[0]
    assert "Paper 2: First" in prompts[0]
    assert "Excluded" not in prompts[0]
    assert "Other job" not in prompts[0]

    summary_id = db_session.scalars(
        select(ResearchSummary.id).where(ResearchSummary.job_id == job_id)
    ).one()
    saved_ids = db_session.execute(
        select(research_summary_papers.c.paper_id)
        .where(research_summary_papers.c.summary_id == summary_id)
        .order_by(research_summary_papers.c.position)
    ).scalars().all()
    assert saved_ids == [UUID(paper_id) for paper_id in selected]
    listing = client.get(f"/research-jobs/{job_id}/summaries")
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == str(summary_id)
    assert listing.json()[0]["summary"] == "Reviewed summary"
    assert listing.json()[0]["paper_ids"] == selected

    other_listing = client.get(f"/research-jobs/{other_job.json()['id']}/summaries")
    assert other_listing.status_code == 200, other_listing.text
    assert other_listing.json() == []

    rejected = client.post(
        f"/research-jobs/{job_id}/papers:generate-summary",
        json={"paper_ids": [str(papers[3].id)]},
    )
    assert rejected.status_code == 400, rejected.text
    assert len(prompts) == 1