from uuid import UUID

from sqlalchemy.orm import Session

from app.models.research_gap_analysis import ResearchGapAnalysis
from app.schemas.research import GapAnalysisResponse


def save_gap_analysis(
    db: Session,
    response: GapAnalysisResponse,
    selected_paper_ids: list[UUID],
) -> ResearchGapAnalysis:
    record = ResearchGapAnalysis(
        job_id=response.job_id,
        topic=response.topic,
        selected_paper_ids=[str(paper_id) for paper_id in selected_paper_ids],
        gaps=[gap.model_dump(mode="json") for gap in response.gaps],
    )
    db.add(record)
    db.flush()
    return record