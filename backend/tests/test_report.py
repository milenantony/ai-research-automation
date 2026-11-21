from uuid import UUID

from sqlalchemy import select

from app.models.research_gap_analysis import ResearchGapAnalysis
from app.models.research_paper import ResearchPaper
from app.models.research_summary import ResearchSummary
from app.services.paper_service import PaperService
from app.services.summary_service import save_linked_paper_summary


def test_report_uses_only_approved_gaps_and_cites_sources(client, db_session):
    job = client.post(
        "/research-jobs", json={"topic": "Solar forecasting"}
    ).json()
    job_id = UUID(job["id"])

    paper = ResearchPaper(
        source="arxiv",
        external_id="report-paper-1",
        title="Solar forecasting study",
        abstract="The evaluation period was short.",
        authors=[],
        doi="10.1234/example",
    )
    db_session.add(paper)
    db_session.flush()
    PaperService.link_papers_to_job(db_session, job_id, [paper])
    save_linked_paper_summary(
        db_session, job_id, "Summary of the study.", [paper.id]
    )
    analysis = ResearchGapAnalysis(
        job_id=job_id,
        topic=job["topic"],
        selected_paper_ids=[str(paper.id)],
        gaps=[
            {
                "category": "author_reported_limitation",
                "description": "Short evaluation period.",
                "supporting_paper_ids": [str(paper.id)],
                "evidence": "The abstract reports a short evaluation period.",
                "review_status": "approved",
            },
            {
                "category": "inferred_gap",
                "description": "Unreviewed proposal.",
                "supporting_paper_ids": [str(paper.id)],
                "evidence": "A tentative inference.",
                "review_status": "rejected",
            },
        ],
    )
    db_session.add(analysis)
    db_session.commit()

    summary_id = db_session.scalars(
        select(ResearchSummary.id).where(ResearchSummary.job_id == job_id)
    ).one()
    request = {
        "summary_id": str(summary_id),
        "gap_analysis_id": str(analysis.id),
    }
    response = client.post(
        f"/research-jobs/{job_id}/reports:generate", json=request
    )

    assert response.status_code == 200, response.text
    report = response.json()["report"]
    assert "Summary of the study." in report
    assert "Short evaluation period." in report
    assert "Unreviewed proposal." not in report
    assert "Solar forecasting study" in report
    assert "DOI: 10.1234/example" in report
    assert "[1]" in report

    analysis.gaps = [
        {**gap, "review_status": "pending"} for gap in analysis.gaps
    ]
    db_session.commit()
    no_approval = client.post(
        f"/research-jobs/{job_id}/reports:generate", json=request
    )
    assert no_approval.status_code == 400
    other_job = client.post(
        "/research-jobs", json={"topic": "Wind forecasting"}
    ).json()
    wrong_job = client.post(
        f"/research-jobs/{other_job['id']}/reports:generate",
        json=request,
    )
    assert wrong_job.status_code == 404