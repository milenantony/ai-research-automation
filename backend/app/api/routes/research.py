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
)
from app.services.llm_exceptions import (
    LLMConfigurationError,
    LLMProviderError,
)

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
    try:
        workflow = ResearchWorkflow()

        summary = workflow.generate_summary(
            topic=job.topic,
            research_context=request.research_context,
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

