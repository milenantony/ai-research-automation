
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


