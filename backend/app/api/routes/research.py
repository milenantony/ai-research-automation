from app.services.research_workflow import ResearchWorkflow
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status ,Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.research_job import ResearchJob
from app.schemas.research import (
    ResearchJobCreate,
    ResearchJobResponse,
    ResearchJobStatus,
    ResearchJobUpdate,
    ResearchSummaryRequest,
    ResearchSummaryResponse,
    ResearchPaperResponse,
    PaperSearchRequest,
    LinkedPaperSummaryRequest,
)
from app.services.llm_exceptions import (
    LLMConfigurationError,
    LLMProviderError,
)
from app.models.research_job_papers import research_job_papers
from app.models.research_paper import ResearchPaper
from app.services.paper_retrieval_service import (
    PaperRetrievalError,
    PaperRetrievalService,
)
from app.services.paper_service import PaperService
from app.services.summary_service import save_linked_paper_summary
from app.services.paper_discovery_agent import PaperDiscoveryAgent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/research-jobs",
    tags=["Research Jobs"],
)


@router.post(
    "",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_job(
    request: ResearchJobCreate,
    db: Session = Depends(get_db),
) -> ResearchJob:

    job = ResearchJob(
        topic=request.topic,
        status=ResearchJobStatus.PENDING.value,
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(
            "Research job created successfully: %s",
            job.id,
        )

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Failed to create research job")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create research job",
        )

    return job


@router.get(
    "",
    response_model=list[ResearchJobResponse],
)
def get_research_jobs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    job_status: ResearchJobStatus | None = Query(
        default=None,
        alias="status",
    ),
    db: Session = Depends(get_db),
) -> list[ResearchJob]:

    try:
        query = db.query(ResearchJob)

        if job_status is not None:
            query = query.filter(
                ResearchJob.status == job_status.value
            )

        jobs = (
            query
            .order_by(ResearchJob.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Failed to retrieve research jobs")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve research jobs",
        )

    logger.info(
        "Retrieved %s research jobs (skip=%s, limit=%s, status=%s)",
        len(jobs),
        skip,
        limit,
        job_status.value if job_status else "ALL",
    )

    return jobs

@router.get(
    "/{job_id}",
    response_model=ResearchJobResponse,
)
def get_research_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> ResearchJob:

    try:
        job = db.get(ResearchJob, job_id)

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Failed to retrieve research job")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve research job",
        )

    if job is None:
        logger.warning(
            "Research job not found: %s",
            job_id,
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research job not found",
        )

    logger.info(
        "Research job retrieved successfully: %s",
        job.id,
    )

    return job

@router.put(
    "/{job_id}",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_200_OK,
)
def update_research_job(
    job_id: UUID,
    request: ResearchJobUpdate,
    db: Session = Depends(get_db),
) -> ResearchJob:

    try:
        job = db.get(ResearchJob, job_id)

        if job is None:
            logger.warning(
                "Research job not found for update: %s",
                job_id,
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research job not found",
            )

        job.topic = request.topic

        db.commit()
        db.refresh(job)

        logger.info(
            "Research job updated successfully: %s",
            job.id,
        )

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Failed to update research job")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update research job",
        )

    return job

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_research_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> None:

    try:
        job = db.get(ResearchJob, job_id)

        if job is None:
            logger.warning(
                "Research job not found for deletion: %s",
                job_id,
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research job not found",
            )

        db.delete(job)
        db.commit()

        logger.info(
            "Research job deleted successfully: %s",
            job_id,
        )

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Failed to delete research job")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete research job",
        )

    return None

@router.post(
    "/{job_id}/generate-summary",
    response_model=ResearchSummaryResponse,
    status_code=status.HTTP_200_OK,
)

def generate_research_summary(
    job_id: UUID,
    request: ResearchSummaryRequest,
    db: Session = Depends(get_db),
) -> ResearchSummaryResponse:

    # Step 1: Find the research job
    try:
        job = db.get(ResearchJob, job_id)

    except SQLAlchemyError:
        db.rollback()

        logger.exception(
            "Failed to retrieve research job for summary generation"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve research job",
        )

    # Step 2: Check whether the job exists
    if job is None:
        logger.warning(
            "Research job not found for summary generation: %s",
            job_id,
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research job not found",
        )

    # Step 3: Generate the summary using ResearchWorkflow
    return _generate_summary(job, request.research_context)


def _generate_summary(
    job: ResearchJob,
    research_context: str,
) -> ResearchSummaryResponse:
    job_id = job.id

    try:
        workflow = ResearchWorkflow()
        summary = workflow.generate_summary(
            topic=job.topic,
            research_context=research_context,
        )
        

    except LLMConfigurationError:
        logger.exception(
            "LLM configuration error for research job: %s",
            job_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM configuration error",
        )

    except LLMProviderError:
        logger.exception(
            "LLM provider error for research job: %s",
            job_id,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM provider request failed",
        )

    except ValueError as exc:
        logger.warning(
            "Invalid summary generation request: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception:
        logger.exception(
            "Unexpected error generating research summary for job: %s",
            job_id,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate research summary",
        )

    # Step 4: Return the generated summary
    logger.info(
        "Research summary generated successfully for job: %s",
        job_id,
    )

    return ResearchSummaryResponse(
        job_id=job.id,
        topic=job.topic,
        summary=summary,
    )

@router.get(
    "/{job_id}/papers",
    response_model=list[ResearchPaperResponse],
)
def list_research_job_papers(
    job_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ResearchPaper]:
    try:
        if db.get(ResearchJob, job_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research job not found",
            )

        return (
            PaperService.papers_for_job(db, job_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to list papers for research job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve research papers",
        )
@router.post(
    "/{job_id}/papers:search",
    response_model=list[ResearchPaperResponse],
)
async def search_research_job_papers(
    job_id: UUID,
    request: PaperSearchRequest,
    db: Session = Depends(get_db),
) -> list[ResearchPaperResponse]:
    job = get_research_job(job_id=job_id, db=db)

    try:
        search_query = job.topic
        if request.refine_query:
            search_query = await PaperDiscoveryAgent().build_search_query(job.topic)

        papers = await PaperRetrievalService().search_and_save(
            db=db,
            topic=search_query,
            max_results=request.max_results,
        )
        unique_papers = {paper.id: paper for paper in papers}
        PaperService.link_papers_to_job(db, job_id, unique_papers.values())
        response = [
            ResearchPaperResponse.model_validate(paper)
            for paper in unique_papers.values()
        ]
        db.commit()
        return response
    except LLMConfigurationError as exc:
        db.rollback()
        logger.exception("Paper discovery configuration failed for job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Paper discovery agent configuration failed",
        ) from exc

    except LLMProviderError as exc:
        db.rollback()
        logger.exception("Paper discovery query generation failed for job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate a paper search query",
        ) from exc

    except PaperRetrievalError as exc:
        db.rollback()
        logger.warning("Paper retrieval failed for job %s: %s", job_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="All paper retrieval providers failed",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to save papers for research job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save research job papers",
        ) from exc
@router.post(
    "/{job_id}/papers:generate-summary",
    response_model=ResearchSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def generate_linked_paper_summary(
    job_id: UUID,
    request: LinkedPaperSummaryRequest | None = None,
    db: Session = Depends(get_db),
) -> ResearchSummaryResponse:
    job = get_research_job(job_id=job_id, db=db)
    try:
        papers = PaperService.papers_for_job(db, job_id).all()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to load papers for research job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve research papers",
        )
    if request is not None:
        selected_ids = request.paper_ids

        if len(selected_ids) != len(set(selected_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected paper IDs must be unique",
            )

        papers_by_id = {paper.id: paper for paper in papers}
        if any(paper_id not in papers_by_id for paper_id in selected_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Every selected paper must be linked to this research job",
            )
        papers = [papers_by_id[paper_id] for paper_id in selected_ids]
    try:
        context = ResearchWorkflow.build_paper_context(papers)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    paper_ids = [paper.id for paper in papers]
    response = _generate_summary(job, context)

    try:
        save_linked_paper_summary(
            db=db,
            job_id=job_id,
            summary=response.summary,
            paper_ids=paper_ids,
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to save linked-paper summary for job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save linked-paper summary",
        ) from exc

    return response