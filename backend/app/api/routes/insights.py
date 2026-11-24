import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.research_job import ResearchJob
from app.services.insight_extraction import CitedInsight, extract_insights
from app.services.llm_exceptions import LLMConfigurationError, LLMProviderError
from app.services.llm_service import LLMService
from app.services.passage_retrieval import PassageRetrieval
from app.services.providers.gemini_embeddings import GeminiEmbeddingProvider


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research-jobs", tags=["Research Jobs"])


class InsightExtractionRequest(BaseModel):
    paper_ids: list[UUID] = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class InsightExtractionResponse(BaseModel):
    job_id: UUID
    topic: str
    retrieved_paper_ids: list[UUID]
    insights: list[CitedInsight]


@router.post("/{job_id}/papers:extract-insights", response_model=InsightExtractionResponse)
def extract_paper_insights(
    job_id: UUID, request: InsightExtractionRequest, db: Session = Depends(get_db)
) -> InsightExtractionResponse:
    job = db.get(ResearchJob, job_id)
    if job is None:
        raise HTTPException(404, "Research job not found")
    if len(request.paper_ids) != len(set(request.paper_ids)):
        raise HTTPException(400, "Selected paper IDs must be unique")

    try:
        if not db.scalar(text("SELECT to_regclass('research_abstract_passages')")):
            raise HTTPException(503, "Passage retrieval is unavailable on this database")

        topic = job.topic
        retrieval = PassageRetrieval(db, GeminiEmbeddingProvider())
        retrieval.ingest(job_id, request.paper_ids)
        passages = retrieval.retrieve(job_id, request.paper_ids, topic, limit=request.limit)
        db.commit()

        return InsightExtractionResponse(
            job_id=job_id,
            topic=topic,
            retrieved_paper_ids=[passage.paper_id for passage in passages],
            insights=extract_insights(topic, passages, LLMService()) if passages else [],
        )
    except LLMConfigurationError as exc:
        db.rollback()
        raise HTTPException(503, "Insight extraction provider is not configured") from exc
    except LLMProviderError as exc:
        db.rollback()
        logger.warning("Insight extraction provider failed for job %s: %s", job_id, exc)
        raise HTTPException(502, "Insight extraction provider returned an error") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Passage storage failed for job %s", job_id)
        raise HTTPException(500, "Passage storage failed") from exc
