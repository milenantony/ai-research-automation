import json
import os
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import insert, text

from app.models.research_job import ResearchJob
from app.models.research_job_papers import research_job_papers
from app.models.research_paper import ResearchPaper
from app.services.passage_retrieval import EMBEDDING_DIMENSIONS, PassageRetrieval


pytestmark = pytest.mark.skipif(
    os.getenv("PAPERX_TEST_PGVECTOR") != "1",
    reason="Requires the optional pgvector test database",
)


class DeterministicEmbedder:
    model = "test-embedding"

    def __init__(self):
        self.documents = []

    def embed(self, content, *, is_query):
        if not is_query:
            self.documents.append(content)
        first = (1.0, 0.0) if "solar" in content else (0.0, 1.0)
        return [*first, *([0.0] * (EMBEDDING_DIMENSIONS - 2))]


def test_selected_abstracts_are_embedded_once_and_retrieved_in_scope(
    db_session, client, monkeypatch
):
    first_job = ResearchJob(topic="Solar forecasts")
    second_job = ResearchJob(topic="Storage")
    solar = ResearchPaper(
        source="arxiv",
        external_id=str(uuid4()),
        title="Solar study",
        abstract="  solar forecasts from satellite imagery  ",
        paper_url="https://example.com/solar",
        doi="10.1234/solar",
    )
    battery = ResearchPaper(
        source="arxiv", external_id=str(uuid4()), title="Storage", abstract="battery storage"
    )
    other = ResearchPaper(
        source="arxiv", external_id=str(uuid4()), title="Other", abstract="solar report"
    )
    blank = ResearchPaper(
        source="arxiv", external_id=str(uuid4()), title="Blank", abstract="   "
    )
    db_session.add_all([first_job, second_job, solar, battery, other, blank])
    db_session.flush()
    db_session.execute(insert(research_job_papers), [
        {"job_id": first_job.id, "paper_id": paper.id} for paper in (solar, battery, blank)
    ] + [
        {"job_id": second_job.id, "paper_id": paper.id} for paper in (solar, other)
    ])

    embedder = DeterministicEmbedder()
    service = PassageRetrieval(db_session, embedder)
    selected = [solar.id, battery.id, blank.id, solar.id]

    assert service.ingest(first_job.id, selected) == 2
    db_session.commit()
    assert service.ingest(first_job.id, selected) == 0
    assert sorted(embedder.documents) == ["battery storage", "solar forecasts from satellite imagery"]

    assert service.ingest(second_job.id, [other.id]) == 1
    assert service.retrieve(second_job.id, [solar.id], "solar") == []
    with pytest.raises(ValueError, match="must be linked"):
        service.ingest(first_job.id, [solar.id, other.id])
    with pytest.raises(ValueError, match="must be linked"):
        service.retrieve(first_job.id, [solar.id, other.id], "solar")

    hits = service.retrieve(first_job.id, selected, "solar")
    assert [hit.paper_id for hit in hits] == [solar.id, battery.id]
    assert service.retrieve(first_job.id, selected, "solar", limit=1) == hits[:1]
    hit = hits[0]
    assert hit.job_id == first_job.id
    assert hit.passage_text == "solar forecasts from satellite imagery"
    assert hit.title == solar.title
    assert hit.source == solar.source
    assert hit.external_id == solar.external_id
    assert hit.paper_url == solar.paper_url
    assert hit.doi == solar.doi
    assert hit.cosine_distance == pytest.approx(0.0)
    assert [hit.paper_id for hit in service.retrieve(
        first_job.id, [battery.id], "solar"
    )] == [battery.id]
    assert db_session.scalar(text("""
        SELECT count(*) FROM research_abstract_passages WHERE job_id = :job_id
    """), {"job_id": first_job.id}) == 2

    from app.services import gap_analysis_service, insight_extraction, research_workflow

    monkeypatch.setattr(insight_extraction, "GeminiEmbeddingProvider", lambda: embedder)
    llm = Mock()
    llm.generate.return_value = json.dumps({"insights": [{
        "category": "finding",
        "claim": "The study forecasts solar generation from satellite imagery.",
        "paper_id": str(solar.id),
        "evidence_quote": "solar forecasts from satellite imagery",
    }]})
    monkeypatch.setattr(insight_extraction, "LLMService", lambda: llm)

    response = client.post(
        f"/research-jobs/{first_job.id}/papers:extract-insights",
        json={"paper_ids": [str(solar.id)], "limit": 1},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["retrieved_paper_ids"] == [str(solar.id)]
    assert payload["insights"][0]["paper_id"] == str(solar.id)
    assert payload["insights"][0]["evidence_quote"] == "solar forecasts from satellite imagery"
    assert payload["insights"][0]["paper_url"] == solar.paper_url
    assert "battery storage" not in llm.generate.call_args.args[0]

    gap_llm = Mock()
    gap_llm.generate.return_value = json.dumps({"gaps": [{
        "category": "inferred_gap",
        "description": "Assess transfer to other imagery sources.",
        "evidence": "The supplied insight identifies satellite imagery.",
        "supporting_paper_ids": [str(solar.id)],
        "insight_numbers": [1],
        "review_status": "approved",
    }, {
        "category": "inferred_gap",
        "description": "Rejected control gap.",
        "evidence": "This proposal is excluded by the reviewer.",
        "supporting_paper_ids": [str(solar.id)],
        "insight_numbers": [1],
    }]})
    monkeypatch.setattr(gap_analysis_service, "LLMService", lambda: gap_llm)
    root = f"/research-jobs/{first_job.id}"
    generated = client.post(
        f"{root}/papers:analyze-gaps", json={"paper_ids": [str(solar.id)]}
    )
    assert generated.status_code == 200, generated.text
    gap, rejected_gap = generated.json()["gaps"]
    assert gap["review_status"] == "pending"
    assert gap["cited_insights"] == payload["insights"]
    assert "solar forecasts from satellite imagery" in gap_llm.generate.call_args.args[0]
    saved, = client.get(f"{root}/gap-analyses").json()
    reviewed = client.patch(
        f"{root}/gap-analyses/{saved['id']}/review",
        json={"gap_index": 0, "review_status": "approved"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["gaps"] == [{**gap, "review_status": "approved"}, rejected_gap]
    decision = client.patch(
        f"{root}/gap-analyses/{saved['id']}/review",
        json={"gap_index": 1, "review_status": "rejected"},
    )
    assert decision.status_code == 200, decision.text

    summary_llm = Mock()
    summary_llm.generate.return_value = "The study uses satellite imagery for solar forecasts."
    monkeypatch.setattr(research_workflow, "LLMService", lambda: summary_llm)
    summary = client.post(
        f"{root}/papers:generate-summary", json={"paper_ids": [str(solar.id)]}
    )
    assert summary.status_code == 200, summary.text
    summaries = client.get(f"{root}/summaries").json()
    report = client.post(
        f"{root}/reports:generate",
        json={"summary_id": summaries[0]["id"], "gap_analysis_id": saved["id"]},
    )
    assert report.status_code == 200, report.text
    latest = client.get(f"{root}/reports/latest")
    assert latest.status_code == 200, latest.text
    assert latest.json() == {"report": report.json()["report"]}
    assert client.get(root).json()["status"] == "COMPLETED"
    markdown = latest.json()["report"]
    assert "Assess transfer to other imagery sources." in markdown
    assert "> solar forecasts from satellite imagery" in markdown
    assert "DOI: 10.1234/solar" in markdown
    assert "Rejected control gap." not in markdown

    if fixture_path := os.getenv("PAPERX_REPORT_FIXTURE"):
        Path(fixture_path).write_text(json.dumps({
            "/research-jobs": [client.get(root).json()],
            f"{root}/papers": client.get(f"{root}/papers").json(),
            f"{root}/summaries": summaries,
            f"{root}/gap-analyses": client.get(f"{root}/gap-analyses").json(),
            f"{root}/reports/latest": latest.json(),
        }), encoding="utf-8")

    invalid_gap = json.loads(gap_llm.generate.return_value)
    invalid_gap["gaps"][0]["supporting_paper_ids"] = [str(battery.id)]
    gap_llm.generate.return_value = json.dumps(invalid_gap)
    rejected = client.post(
        f"{root}/papers:analyze-gaps", json={"paper_ids": [str(solar.id)]}
    )
    assert rejected.status_code == 502, rejected.text
    assert [item["id"] for item in client.get(f"{root}/gap-analyses").json()] == [saved["id"]]

    solar.abstract = "updated solar forecasts"
    db_session.flush()
    assert service.ingest(first_job.id, [solar.id]) == 1
    assert service.retrieve(first_job.id, [solar.id], "solar")[0].passage_text == solar.abstract

    solar.abstract = None
    db_session.flush()
    assert service.ingest(first_job.id, [solar.id]) == 1
    assert service.retrieve(first_job.id, [solar.id], "solar") == []
