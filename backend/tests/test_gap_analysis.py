import json
from uuid import UUID
from sqlalchemy import select

from app.models.research_gap_analysis import ResearchGapAnalysis

from app.models.research_paper import ResearchPaper
from app.services.llm_service import LLMService
from app.services.paper_service import PaperService
import pytest
from uuid import uuid4

from app.services.gap_analysis_service import generate_insight_backed_gaps, parse_gap_analysis
from app.services.insight_extraction import CitedInsight
from app.services.llm_exceptions import LLMProviderError




@pytest.mark.parametrize(
    ("wrapper", "case", "error"),
    [
        ("{}", "empty", None),
        ("```json\n{}\n```", "empty", None),
        (" \n```json\r\n{}\r\n```\n ", "cited", None),
        ("```json\n{}\n```", "invalid_schema", "Invalid insight-backed gap response"),
        ("```json\n{}\n```", "corrected_evidence", None),
        ("```json\n{}\n```", "unknown_insight", "unknown insight"),
        ("```json\n{}\n```", "wrong_paper", "paper citations do not match"),
        ("Here is the result:\n```json\n{}\n```", "empty", "Invalid insight-backed gap response"),
        ("```json\n{}\n```\n```json\n{{}}\n```", "empty", "Invalid insight-backed gap response"),
    ],
)
def test_insight_backed_gap_response(monkeypatch, wrapper, case, error):
    job_id = uuid4()
    insight = CitedInsight(
        category="limitation",
        claim="The evaluation was limited to one site.",
        paper_id=uuid4(),
        evidence_quote="The evaluation was limited to one site.",
        title="Solar study",
        source="arxiv",
        external_id="solar-study",
        paper_url=None,
        doi=None,
    )
    gap = {
        "category": "author_reported_limitation",
        "description": insight.claim,
        "evidence": insight.evidence_quote,
        "supporting_paper_ids": [str(insight.paper_id)],
        "insight_numbers": [1],
    }
    if case == "invalid_schema":
        del gap["insight_numbers"]
    elif case == "unknown_insight":
        gap["insight_numbers"] = [2]
    elif case == "wrong_paper":
        gap["supporting_paper_ids"] = [str(uuid4())]

    payload = wrapper.format(json.dumps({"gaps": [] if case == "empty" else [gap]}))
    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    prompts = []

    def generate(self, prompt):
        prompts.append(prompt)
        if case == "corrected_evidence" and len(prompts) == 1:
            incomplete_gap = {key: value for key, value in gap.items() if key != "evidence"}
            return wrapper.format(json.dumps({"gaps": [incomplete_gap]}))
        return payload

    monkeypatch.setattr(LLMService, "generate", generate)
    if error:
        with pytest.raises(LLMProviderError, match=error):
            generate_insight_backed_gaps(job_id, "Solar forecasting", [insight])
        return

    result = generate_insight_backed_gaps(job_id, "Solar forecasting", [insight])
    assert result.job_id == job_id
    if case == "corrected_evidence":
        assert len(prompts) == 2
        assert 'especially "evidence"' in prompts[1]
        assert result.gaps[0].evidence == insight.evidence_quote
    else:
        assert len(prompts) == 1
    if case == "empty":
        assert result.gaps == []
    else:
        cited_gap, = result.gaps
        assert cited_gap.review_status == "pending"
        assert cited_gap.supporting_paper_ids == [insight.paper_id]
        assert cited_gap.cited_insights == [insight]


def test_gap_analysis_uses_selected_papers_in_order(
    client, db_session, monkeypatch
):
    job = client.post(
        "/research-jobs",
        json={"topic": "Solar forecasting"},
    )
    assert job.status_code == 201
    job_id = UUID(job.json()["id"])

    papers = [
        ResearchPaper(
            source="arxiv",
            external_id=f"gap-test-{number}",
            title=title,
            abstract=f"Abstract for {title}.",
            authors=[],
        )
        for number, title in enumerate(("First", "Second", "Excluded"))
    ]
    db_session.add_all(papers)
    db_session.flush()
    PaperService.link_papers_to_job(db_session, job_id, papers)
    db_session.commit()

    prompts = []

    def fake_generate(self, prompt):
        prompts.append(prompt)
        return json.dumps({
            "gaps": [{
                "category": "inferred_gap",
                "description": "A cautious comparison of the two studies.",
                "supporting_paper_ids": [
                    str(papers[1].id),
                    str(papers[0].id),
                ],
                "evidence": "The selected abstracts describe different approaches.",
            }]
        })

    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    monkeypatch.setattr(LLMService, "generate", fake_generate)

    response = client.post(
        f"/research-jobs/{job_id}/papers:analyze-gaps",
        json={"paper_ids": [str(papers[1].id), str(papers[0].id)]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["gaps"][0]["supporting_paper_ids"] == [
        str(papers[1].id),
        str(papers[0].id),
    ]
    assert prompts[0].index("Title: Second") < prompts[0].index("Title: First")
    assert "Title: Excluded" not in prompts[0]
    db_session.expire_all()
    saved = db_session.scalars(
        select(ResearchGapAnalysis).where(
            ResearchGapAnalysis.job_id == job_id
        )
    ).one()

    assert saved.topic == "Solar forecasting"
    assert saved.selected_paper_ids == [
        str(papers[1].id),
        str(papers[0].id),
    ]
    assert saved.gaps == response.json()["gaps"]
    listed = client.get(f"/research-jobs/{job_id}/gap-analyses")

    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == str(saved.id)
    assert listed.json()[0]["selected_paper_ids"] == [
        str(papers[1].id),
        str(papers[0].id),
    ]
    assert listed.json()[0]["gaps"] == response.json()["gaps"]
    review = client.patch(
    f"/research-jobs/{job_id}/gap-analyses/{saved.id}/review",
    json={"gap_index": 0, "review_status": "approved"},
    )

    assert review.status_code == 200, review.text
    assert review.json()["gaps"][0]["review_status"] == "approved"

    db_session.expire_all()
    reloaded = db_session.get(ResearchGapAnalysis, saved.id)
    assert reloaded.gaps[0]["review_status"] == "approved"
def test_gap_analysis_rejects_unselected_citation():
    selected_id = uuid4()
    other_id = uuid4()

    response = json.dumps({
        "gaps": [{
            "category": "inferred_gap",
            "description": "A proposed gap.",
            "supporting_paper_ids": [str(other_id)],
            "evidence": "A claimed observation.",
        }]
    })

    with pytest.raises(LLMProviderError, match="unselected paper"):
        parse_gap_analysis(
            raw_response=response,
            job_id=uuid4(),
            topic="Solar forecasting",
            selected_paper_ids=[selected_id],
        )


def test_gap_analysis_rejects_invalid_json():
    with pytest.raises(LLMProviderError, match="invalid JSON"):
        parse_gap_analysis(
            raw_response="This is not JSON",
            job_id=uuid4(),
            topic="Solar forecasting",
            selected_paper_ids=[uuid4()],
        )
def test_gap_analysis_rejects_paper_from_another_job(
    client, db_session, monkeypatch
):
    first = client.post(
        "/research-jobs", json={"topic": "Solar forecasting"}
    )
    second = client.post(
        "/research-jobs", json={"topic": "Wind forecasting"}
    )
    assert first.status_code == second.status_code == 201

    paper = ResearchPaper(
        source="arxiv",
        external_id="gap-other-job",
        title="Wind study",
        abstract="Wind forecasting methods.",
        authors=[],
    )
    db_session.add(paper)
    db_session.flush()
    PaperService.link_papers_to_job(
        db_session, UUID(second.json()["id"]), [paper]
    )
    db_session.commit()

    def fail_if_called(self):
        pytest.fail("LLM must not run for a paper from another job")

    monkeypatch.setattr(LLMService, "__init__", fail_if_called)

    response = client.post(
        f"/research-jobs/{first.json()['id']}/papers:analyze-gaps",
        json={"paper_ids": [str(paper.id)]},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == (
        "Every selected paper must be linked to this research job"
    )
def test_gap_analysis_cannot_cite_paper_without_abstract(
    client, db_session, monkeypatch
):
    job = client.post(
        "/research-jobs", json={"topic": "Solar forecasting"}
    )
    assert job.status_code == 201
    job_id = UUID(job.json()["id"])

    with_abstract = ResearchPaper(
        source="arxiv",
        external_id="gap-with-abstract",
        title="Study with evidence",
        abstract="The study reports a limited evaluation period.",
        authors=[],
    )
    without_abstract = ResearchPaper(
        source="arxiv",
        external_id="gap-no-abstract",
        title="Study without evidence",
        abstract=None,
        authors=[],
    )
    db_session.add_all([with_abstract, without_abstract])
    db_session.flush()
    PaperService.link_papers_to_job(
        db_session, job_id, [with_abstract, without_abstract]
    )
    db_session.commit()

    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    monkeypatch.setattr(
        LLMService,
        "generate",
        lambda self, prompt: json.dumps({
            "gaps": [{
                "category": "author_reported_limitation",
                "description": "Limited evaluation period.",
                "supporting_paper_ids": [str(without_abstract.id)],
                "evidence": "A fabricated claim.",
            }]
        }),
    )

    response = client.post(
        f"/research-jobs/{job_id}/papers:analyze-gaps",
        json={"paper_ids": [
            str(with_abstract.id), str(without_abstract.id)
        ]},
    )

    assert response.status_code == 502, response.text
def test_generated_gap_cannot_approve_itself():
    paper_id = uuid4()
    result = parse_gap_analysis(
        raw_response=json.dumps({
            "gaps": [{
                "category": "inferred_gap",
                "description": "A cautious proposed gap.",
                "supporting_paper_ids": [str(paper_id)],
                "evidence": "The supplied abstract supports this inference.",
                "review_status": "approved",
            }]
        }),
        job_id=uuid4(),
        topic="Solar forecasting",
        selected_paper_ids=[paper_id],
    )

    assert result.gaps[0].review_status == "pending"